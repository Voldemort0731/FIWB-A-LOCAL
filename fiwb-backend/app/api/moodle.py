from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.lms.moodle_sync import MoodleSyncService
from pydantic import BaseModel

router = APIRouter()

class MoodleConnectRequest(BaseModel):
    user_email: str
    moodle_url: str
    moodle_token: str

async def moodle_sync_task(user_email: str, url: str, token: str):
    service = MoodleSyncService(url, token, user_email)
    await service.sync_all()

@router.post("/connect")
async def connect_moodle(request: MoodleConnectRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Standardize URL
    url = request.moodle_url.rstrip('/')
    
    user.moodle_url = url
    user.moodle_token = request.moodle_token
    db.commit()
    
    background_tasks.add_task(moodle_sync_task, user.email, url, request.moodle_token)
    
    return {"status": "success", "message": "Moodle connected and sync started"}

@router.post("/sync")
async def sync_moodle(user_email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_email).first()
    if not user or not user.moodle_url or not user.moodle_token:
        raise HTTPException(status_code=400, detail="Moodle not connected for this user")
        
    background_tasks.add_task(moodle_sync_task, user.email, user.moodle_url, user.moodle_token)
    return {"status": "sync_started"}
