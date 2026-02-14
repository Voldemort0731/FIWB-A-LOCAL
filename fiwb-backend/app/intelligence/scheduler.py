import asyncio
import logging
import json
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import User
from app.lms.sync_service import LMSSyncService
from app.lms.moodle_sync import MoodleSyncService
from app.lms.drive_service import DriveSyncService
from app.lms.gmail_service import GmailSyncService

logger = logging.getLogger("uvicorn.error")

async def sync_all_for_user(user_email: str):
    """Run all sync services for a single user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            return

        logger.info(f"🔄 [Auto-Sync] Starting background cycle for {user_email}")

        # 1. Google Classroom Sync
        try:
            classroom_service = LMSSyncService(user.access_token, user_email, user.refresh_token)
            await classroom_service.sync_all_courses()
            
            # Save refreshed token if changed
            if classroom_service.gc_client.creds.token != user.access_token:
                user.access_token = classroom_service.gc_client.creds.token
                db.commit()
                logger.info(f"🔄 [Auto-Sync] Access token refreshed and saved for {user_email}")
                
            logger.info(f"✅ [Auto-Sync] Classroom synced for {user_email}")
        except Exception as e:
            logger.error(f"❌ [Auto-Sync] Classroom failed for {user_email}: {e}")

        # 2. Moodle Sync
        if user.moodle_url and user.moodle_token:
            try:
                moodle_service = MoodleSyncService(user.moodle_url, user.moodle_token, user_email)
                await moodle_service.sync_all()
                logger.info(f"✅ [Auto-Sync] Moodle synced for {user_email}")
            except Exception as e:
                logger.error(f"❌ [Auto-Sync] Moodle failed for {user_email}: {e}")

        # 3. Google Drive Sync (Watched Folders)
        if user.watched_drive_folders:
            try:
                folder_ids = json.loads(user.watched_drive_folders)
                if folder_ids:
                    drive_service = DriveSyncService(user.access_token, user_email, user.refresh_token)
                    for fid in folder_ids:
                        await drive_service.sync_folder(fid)
                    logger.info(f"💾 [Auto-Sync] Drive ({len(folder_ids)} folders) synced for {user_email}")
            except Exception as e:
                logger.error(f"❌ [Auto-Sync] Drive failed for {user_email}: {e}")

        # 4. Gmail Sync (Tests & Announcements)
        try:
            gmail_service = GmailSyncService(user.access_token, user.email, user.refresh_token)
            await gmail_service.sync_recent_emails()
            logger.info(f"✅ [Auto-Sync] Gmail synced for {user_email}")
        except Exception as e:
            logger.error(f"❌ [Auto-Sync] Gmail failed for {user_email}: {e}")

        # Update last_synced
        user.last_synced = datetime.utcnow()
        db.commit()
        logger.info(f"💎 [Auto-Sync] Full Cycle Successful for {user_email}")

    finally:
        db.close()

async def global_sync_loop():
    """Infinite loop that syncs all users periodically."""
    # Wait for app to fully start
    await asyncio.sleep(60)
    
    interval_seconds = 60 * 60 * 6 // 1 # 6 hours backup
    
    while True:
        try:
            logger.info("🌍 [Auto-Sync] Starting global background safety-net cycle...")
            db = SessionLocal()
            users = db.query(User).all()
            user_emails = [u.email for u in users]
            db.close()

            for email in user_emails:
                await sync_all_for_user(email)
                # Small gap between users to prevent overwhelming APIs
                await asyncio.sleep(5)

            logger.info(f"😴 [Auto-Sync] Cycle complete. Sleeping for {interval_seconds//60} mins.")
        except Exception as e:
            logger.error(f"🚨 [Auto-Sync] Critical error in global loop: {e}")
        
        await asyncio.sleep(interval_seconds)

def start_scheduler():
    """Start the background sync loop."""
    asyncio.create_task(global_sync_loop())
