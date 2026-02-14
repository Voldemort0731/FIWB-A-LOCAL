from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.lms.drive_service import DriveSyncService
from pydantic import BaseModel
from typing import List
import asyncio
import json

router = APIRouter()

class DriveSyncRequest(BaseModel):
    user_email: str
    folder_ids: List[str]

async def drive_sync_task(user_email: str, access_token: str, refresh_token: str, folder_ids: List[str]):
    service = DriveSyncService(access_token, user_email, refresh_token)
    for folder_id in folder_ids:
        try:
            await service.sync_folder(folder_id)
        except Exception as e:
            print(f"Error syncing folder {folder_id} for {user_email}: {e}")

@router.get("/folders")
async def get_folders(user_email: str, db: Session = Depends(get_db)):
    from app.utils.email import standardize_email
    email = standardize_email(user_email)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    service = DriveSyncService(user.access_token, user.email, user.refresh_token)
    try:
        folders = await service.list_root_folders()
        return folders
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list Drive folders: {str(e)}")

@router.post("/sync")
async def sync_drive(request: DriveSyncRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from app.utils.email import standardize_email
    email = standardize_email(request.user_email)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.watched_drive_folders = json.dumps(request.folder_ids)
    db.commit()
    
    background_tasks.add_task(
        drive_sync_task, 
        user.email, 
        user.access_token, 
        user.refresh_token, 
        request.folder_ids
    )
    
    return {"status": "sync_started", "folders_queued": len(request.folder_ids)}
