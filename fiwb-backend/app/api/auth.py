import os
import asyncio
import httpx
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.lms.sync_service import LMSSyncService
from app.database import get_db, engine, Base
from app.models import User
from app.config import settings
from app.utils.email import standardize_email

# Allow scope mismatch (Google sometimes reorders or drops scopes)
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

async def sync_courses_task(access_token: str, user_email: str, refresh_token: str = None):
    """Background task to sync courses from Google Classroom."""
    service = LMSSyncService(access_token, user_email, refresh_token)
    await service.sync_all_courses()

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]

class LoginRequest(BaseModel):
    code: str

@router.post("/login")
async def login(request: LoginRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Highly optimized Login endpoint using direct HTTP/Rest exchange.
    Bypasses slow library discovery docs and synchronous network calls.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Exchange Authorization Code for Tokens
            # This is the standard OAuth2 token swap
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": request.code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": "postmessage",
                    "grant_type": "authorization_code",
                }
            )
            
            if not token_resp.is_success:
                logger.error(f"Token exchange failed: {token_resp.text}")
                raise HTTPException(status_code=400, detail="Google authentication failed")
            
            tokens = token_resp.json()
            access_token = tokens.get('access_token')
            refresh_token = tokens.get('refresh_token')
            
            # 2. Get User Profile via direct UserInfo API
            # This replaces the slow build('oauth2', 'v2') call
            ui_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if not ui_resp.is_success:
                raise HTTPException(status_code=400, detail="Failed to retrieve profile info")
            
            user_info = ui_resp.json()
            email = standardize_email(user_info.get('email'))
            google_id = str(user_info.get('id') or user_info.get('sub'))
            
            if not email:
                raise HTTPException(status_code=400, detail="No email found in Google response")

            # 3. Database Management (Fast Lookup)
            user = db.query(User).filter(User.google_id == google_id).first()
            if not user:
                user = db.query(User).filter(User.email == email).first()

            if not user:
                user = User(
                    email=email,
                    google_id=google_id,
                    access_token=access_token,
                    refresh_token=refresh_token
                )
                db.add(user)
            else:
                user.email = email 
                user.google_id = google_id
                user.access_token = access_token
                if refresh_token:
                    user.refresh_token = refresh_token
            
            db.commit()
            db.refresh(user)
            
            # 4. Defer Background Tasks — FAST FIRST, DEEP LATER
            async def run_initial_sync():
                try:
                    # Phase 1: Quick classroom metadata (courses list only)
                    # This makes the dashboard show courses as fast as possible
                    service = LMSSyncService(access_token, email, refresh_token)
                    await service.sync_all_courses()
                    logger.info(f"Phase 1 (classroom meta) done for {email}")
                except Exception as e:
                    logger.error(f"Phase 1 sync fail for {email}: {e}")
                
                try:
                    # Phase 2: Drive + Gmail (deferred, non-blocking)
                    await asyncio.sleep(5)  # Delay to let UI settle and user interact
                    from app.intelligence.scheduler import sync_all_for_user
                    await sync_all_for_user(email)
                    logger.info(f"Phase 2 (full sync) done for {email}")
                except Exception as e:
                    logger.error(f"Phase 2 sync fail for {email}: {e}")

            background_tasks.add_task(run_initial_sync)
            
            return {
                "status": "success", 
                "user_id": user.id,
                "email": email,
                "name": user_info.get('name'),
                "picture": user_info.get('picture')
            }
    
    except Exception as e:
        logger.error(f"Login process failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Terminal initialization failure")

