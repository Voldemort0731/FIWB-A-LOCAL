from celery import Celery
from app.lms.sync_service import LMSSyncService
from app.config import settings
from app.database import SessionLocal
from app.models import User
import asyncio

celery_app = Celery('fiwb', broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.beat_schedule = {
    'sync-every-hour': {
        'task': 'app.worker.sync_all_users',
        'schedule': 3600.0,
    },
}
celery_app.conf.timezone = 'UTC'

@celery_app.task(name='app.worker.sync_all_users')
def sync_all_users():
    """Background task to sync all users."""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Syncing {len(users)} users...")
        for user in users:
            if user.access_token:
                sync_user_courses.delay(user.email, user.access_token)
    finally:
        db.close()

@celery_app.task
def sync_user_courses(user_email: str, token: str):
    """Sync a specific user's courses."""
    service = LMSSyncService(token, user_email)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(service.sync_all_courses())
