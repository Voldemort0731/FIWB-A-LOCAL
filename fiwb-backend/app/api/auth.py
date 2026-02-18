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

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

class LoginRequest(BaseModel):
    code: str

@router.post("/login")
async def login(request: LoginRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Highly optimized Login endpoint for Institutional Scale.
    Uses shared connection pooling and non-blocking background tasks.
    """
    try:
        from app.utils.clients import SharedClients
        client = SharedClients.get_http_client()
        
        # 1. Exchange Authorization Code for Tokens
        logger.info(f"Attempting token exchange for code: {request.code[:10]}...")
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": request.code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": "postmessage",
                "grant_type": "authorization_code",
            },
            timeout=15.0
        )
        
        if not token_resp.is_success:
            logger.error(f"Token exchange failed: {token_resp.text}")
            raise HTTPException(status_code=400, detail="Google authentication failed")
        
        tokens = token_resp.json()
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')
        
        # 2. Get User Profile via direct UserInfo API
        ui_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0
        )
        
        if not ui_resp.is_success:
            logger.error(f"UserInfo fetch failed: {ui_resp.text}")
            raise HTTPException(status_code=400, detail="Failed to retrieve profile info")
        
        user_info = ui_resp.json()
        email = standardize_email(user_info.get('email'))
        google_id = str(user_info.get('id') or user_info.get('sub'))
        
        if not email:
            raise HTTPException(status_code=400, detail="No email found in Google response")

        # 3. Database Management (Non-blocking)
        def get_or_create_user(db_session: Session, g_id: str, u_email: str, a_token: str, r_token: str):
            user = db_session.query(User).filter(User.google_id == g_id).first()
            if not user:
                user = db_session.query(User).filter(User.email == u_email).first()

        # 3. Database Management (Synchronous for Safety)
        # We run this directly to avoid threading issues with the dependency-injected session
        def get_or_create_user_sync(db_session: Session, g_id: str, u_email: str, a_token: str, r_token: str):
            user = db_session.query(User).filter(User.google_id == g_id).first()
            if not user:
                user = db_session.query(User).filter(User.email == u_email).first()

            if not user:
                user = User(email=u_email, google_id=g_id, access_token=a_token, refresh_token=r_token)
                db_session.add(user)
            else:
                user.email = u_email 
                user.google_id = g_id
                user.access_token = a_token
                user.refresh_token = r_token if r_token else user.refresh_token
            
            user.last_synced = datetime.utcnow()
            try:
                db_session.commit()
                db_session.refresh(user)
                return user.id
            except Exception as e:
                db_session.rollback()
                raise e

        user_id = get_or_create_user_sync(db, google_id, email, access_token, refresh_token)
        logger.info(f"User {email} authenticated. Starting background sync.")
        
        # 4. Defer Background Tasks (Leveled Sync)
        async def run_initial_sync():
            try:
                # Level 0/1: Classroom meta
                from app.lms.sync_service import LMSSyncService
                service = LMSSyncService(access_token, email, refresh_token)
                await service.sync_all_courses()
                
                # Level 2: Deep Sync (Gmail, Drive) - delayed for UI smoothness
                await asyncio.sleep(3) 
                from app.intelligence.scheduler import sync_all_for_user
                await sync_all_for_user(email)
            except Exception as e:
                logger.error(f"Background sync failed for {email}: {e}")

        background_tasks.add_task(run_initial_sync)
        
        return {
            "status": "success", 
            "user_id": user_id,
            "email": email,
            "name": user_info.get('name'),
            "picture": user_info.get('picture')
        }
    
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Login failure: {e}")
        raise HTTPException(status_code=500, detail="Institutional link failure during login.")
