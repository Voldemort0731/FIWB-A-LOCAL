import asyncio
import logging
from app.database import SessionLocal
from app.models import User
from app.lms.sync_service import LMSSyncService
import requests

# Configure logging to show everything
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sync():
    db = SessionLocal()
    try:
        # Fetch the user explicitly
        user_email = "sidwagh724@gmail.com"
        user = db.query(User).filter(User.email == user_email).first()
        
        if not user:
            print(f"❌ User {user_email} not found in DB!")
            return

        print(f"✅ Found User: {user.email}")
        print(f"🔑 Access Token: {user.access_token[:10]}...")
        
        # DEBUG: Check Token Scopes
        print("🔍 Checking Token Scopes...")
        try:
            token_info = requests.get(f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={user.access_token}").json()
            if 'scope' in token_info:
                print(f"📜 Scopes: {token_info['scope']}")
            else:
                print(f"⚠️ Could not get scopes: {token_info}")
        except Exception as e:
            print(f"⚠️ Token debug failed: {e}")

        # Initialize Service
        service = LMSSyncService(user.access_token, user.email)
        
        # Run Sync
        print("🔄 Starting Sync...")
        await service.sync_all_courses()
        print("✅ Sync Finished!")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_sync())
