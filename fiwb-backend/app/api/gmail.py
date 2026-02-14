from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.lms.gmail_service import GmailSyncService
import logging

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

@router.post("/trigger/{user_id}")
async def trigger_gmail_sync(user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger a manual Gmail sync for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.access_token:
        # Check if we have credentials generally
        raise HTTPException(status_code=400, detail="User not authenticated with Google")
        
    try:
        service = GmailSyncService(user.access_token, user.email, user.refresh_token)
        # Run sync in background
        background_tasks.add_task(service.sync_recent_emails)
    except Exception as e:
        logger.error(f"Failed to start Gmail sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"status": "Gmail sync started in background"}
