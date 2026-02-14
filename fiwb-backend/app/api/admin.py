from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import User, Course, user_courses
from app.lms.sync_service import LMSSyncService
from sqlalchemy import delete
import asyncio

from app.config import settings

router = APIRouter()

def verify_admin(admin_email: str):
    if admin_email != settings.OWNER_EMAIL:
        raise HTTPException(status_code=403, detail="Unauthorized access to analytics")
    return admin_email

@router.get("/users")
def get_users(admin_email: str, db: Session = Depends(get_db)):
    """List all users."""
    verify_admin(admin_email)
    return db.query(User).all()

@router.get("/courses")
def get_all_courses(admin_email: str, db: Session = Depends(get_db)):
    """List all courses."""
    verify_admin(admin_email)
    return db.query(Course).all()

async def sync_task(user_email: str):
    from app.intelligence.scheduler import sync_all_for_user
    await sync_all_for_user(user_email)

@router.post("/sync/{user_email}")
def trigger_sync(user_email: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually trigger sync for a user using stored token."""
    from app.utils.email import standardize_email
    email = standardize_email(user_email)
    
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.access_token:
        raise HTTPException(status_code=404, detail="User or token not found")
    
    background_tasks.add_task(sync_task, user.email)
    return {"status": "Sync started in background"}

@router.post("/cleanup/{user_email}")
async def cleanup_user_data(user_email: str, db: Session = Depends(get_db)):
    """Remove all mock data and optionally clear specific user links."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Identify mock courses linked to this user
    mock_courses_list = [c for c in user.courses if c.id.startswith("mock")]
    
    for course in mock_courses_list:
        # Remove link
        user.courses.remove(course)
        
        # If no other users are linked to this mock course, delete it
        if len(course.users) == 0:
            db.delete(course)
    
    db.commit()
    return {"status": f"Cleaned up {len(mock_courses_list)} mock courses for {user_email}"}

@router.post("/mock-sync/{user_email}")
async def trigger_mock_sync(user_email: str, db: Session = Depends(get_db)):
    """Generate mock courses and materials for testing."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email, google_id=f"mock_{user_email}")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    from app.supermemory.client import SupermemoryClient
    sm_client = SupermemoryClient()
    
    mock_courses = [
        {"id": "mock1", "name": "Artificial Intelligence", "professor": "Dr. Alan Turing", "platform": "Google Classroom"},
        {"id": "mock2", "name": "Computer Networks", "professor": "Dr. Vint Cerf", "platform": "Google Classroom"},
        {"id": "mock3", "name": "Operating Systems", "professor": "Dr. Linus Torvalds", "platform": "Google Classroom"},
    ]
    
    for c in mock_courses:
        db_course = db.query(Course).filter(Course.id == c['id']).first()
        if not db_course:
            db_course = Course(**c)
            db.add(db_course)
        else:
            db_course.name = c['name']
            db_course.professor = c['professor']
        
        if db_course not in user.courses:
            user.courses.append(db_course)
            
        materials = [
            {"title": f"Syllabus - {c['name']}", "type": "material", "content": f"Introduction to {c['name']}."},
            {"title": f"Assignment 1", "type": "assignment", "content": "Basic problems."},
            {"title": "Lecture Notes", "type": "material", "content": "Week 1 notes."}
        ]
        
        for m in materials:
            meta = {
                "user_id": user_email,
                "course_id": c['id'],
                "course_name": c['name'],
                "type": m['type'],
                "source": "Mock Sync"
            }
            await sm_client.add_document(m['content'], meta, title=m['title'])
    
    db.commit()
    return {"status": "Mock environment initialized"}
