import asyncio
import logging
from app.lms.sync_service import LMSSyncService
from app.database import SessionLocal, engine
from app.models import User, Material, Base

# Set up logging to stdout
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

async def manual_sync():
    print("Initializing Database...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    user = db.query(User).filter(User.email == "siddhantwagh724@gmail.com").first()
    if not user:
        print("User not found!")
        return
    
    print(f"Starting Manual Sync for {user.email}...")
    service = LMSSyncService(user.access_token, user.email, user.refresh_token)
    await service.sync_all_courses()
    
    mats = db.query(Material).all()
    print(f"Sync finished. Materials in DB: {len(mats)}")
    for m in mats:
        print(f"- {m.title} ({m.type})")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(manual_sync())
