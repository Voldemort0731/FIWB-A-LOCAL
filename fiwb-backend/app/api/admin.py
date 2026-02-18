from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import User, Course, Material
from sqlalchemy import delete
import asyncio
import logging

from app.config import settings
from app.utils.email import standardize_email

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

def verify_admin(admin_email: str):
    if admin_email != settings.OWNER_EMAIL:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return admin_email

@router.get("/users")
def get_users(admin_email: str, db: Session = Depends(get_db)):
    verify_admin(admin_email)
    users = db.query(User).all()
    return [{"id": u.id, "email": u.email, "last_synced": u.last_synced} for u in users]

@router.get("/courses")
def get_all_courses(admin_email: str, db: Session = Depends(get_db)):
    verify_admin(admin_email)
    return db.query(Course).all()

async def _run_full_sync(user_email: str):
    """Background sync task that uses the stored token from DB."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user or not user.access_token:
            logger.error(f"[Admin Sync] No token for {user_email}")
            return
        access_token = user.access_token
        refresh_token = user.refresh_token
    finally:
        db.close()

    # 1. Classroom sync
    try:
        from app.lms.sync_service import LMSSyncService
        svc = LMSSyncService(access_token, user_email, refresh_token)
        await svc.sync_all_courses()
        logger.info(f"[Admin Sync] Classroom sync triggered for {user_email}")
    except Exception as e:
        logger.error(f"[Admin Sync] Classroom failed for {user_email}: {e}")

    # 2. Gmail sync (after short delay)
    await asyncio.sleep(2)
    try:
        from app.lms.gmail_service import GmailSyncService
        gmail = GmailSyncService(access_token, user_email, refresh_token)
        await gmail.sync_recent_emails()
        logger.info(f"[Admin Sync] Gmail sync done for {user_email}")
    except Exception as e:
        logger.error(f"[Admin Sync] Gmail failed for {user_email}: {e}")

@router.post("/sync/{user_email}")
async def trigger_sync(user_email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually trigger a full sync for a user using their stored token."""
    email = standardize_email(user_email)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.access_token:
        raise HTTPException(status_code=400, detail="No access token stored for user. Please log in again.")

    background_tasks.add_task(_run_full_sync, email)
    return {"status": "sync_started", "user": email}

@router.post("/cleanup/{user_email}")
async def cleanup_user_data(user_email: str, db: Session = Depends(get_db)):
    """Remove all mock data for a user."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    mock_courses = [c for c in user.courses if c.id.startswith("mock")]
    for course in mock_courses:
        user.courses.remove(course)
        if len(course.users) == 0:
            db.delete(course)

    db.commit()
    return {"status": f"Cleaned up {len(mock_courses)} mock courses for {user_email}"}

@router.get("/status/{user_email}")
def get_sync_status(user_email: str, db: Session = Depends(get_db)):
    """Get sync status and material counts for a user."""
    email = standardize_email(user_email)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    material_count = db.query(Material).filter(Material.user_id == user.id).count()
    course_count = len(user.courses)

    return {
        "email": user.email,
        "last_synced": user.last_synced,
        "courses": course_count,
        "materials": material_count,
        "has_token": bool(user.access_token),
        "has_refresh_token": bool(user.refresh_token)
    }
