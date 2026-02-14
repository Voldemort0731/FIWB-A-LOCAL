import asyncio
import logging
from app.lms.sync_service import LMSSyncService
from app.database import SessionLocal
from app.models import User

logging.basicConfig(level=logging.INFO)
logging.getLogger("uvicorn.error").handlers = [] # prevent double logging if any
logging.getLogger("uvicorn.error").addHandler(logging.StreamHandler())
logging.getLogger("uvicorn.error").setLevel(logging.INFO)

async def test_sync():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "siddhantwagh724@gmail.com").first()
    if not user:
        print("User not found")
        return
    
    if not user.access_token:
        print("No access token for user")
        return
        
    print(f"Testing sync for {user.email}...")
    service = LMSSyncService(user.access_token, user.email, user.refresh_token)
    await service.sync_all_courses()
    
    courses = await asyncio.to_thread(service.gc_client.get_courses)
    print(f"Found {len(courses)} courses:")
    for c in courses:
        print(f" - {c.get('name')} (ID: {c.get('id')})")
        
        # Test coursework
        cw = await asyncio.to_thread(service.gc_client.get_coursework, c.get('id'))
        print(f"   -> Found {len(cw)} coursework items")
        
        # Test materials
        mat = await asyncio.to_thread(service.gc_client.get_materials, c.get('id'))
        print(f"   -> Found {len(mat)} material items")
        
        # Test announcements
        ann = await asyncio.to_thread(service.gc_client.get_announcements, c.get('id'))
        print(f"   -> Found {len(ann)} announcements")
    # Debug check
    print("\n--- Debugging Supermemory Storage ---")
    sm_client = service.sm_client
    # Basic functionality check
    import time
    ts = str(int(time.time()))
    test_title = f"Test Doc {ts}"
    print(f"\n--- Creating Test Document: {test_title} ---")
    await sm_client.add_document("This is a test content", {"type": "test", "user_id": user.email}, title=test_title)
    
    print("Waiting 15 seconds for indexing...")
    await asyncio.sleep(15)
    
    print(f"Searching for '{test_title}'")
    res = await sm_client.search(query=test_title, filters=None)
    chunks = res.get("chunks", [])
    print(f"Found {len(chunks)} chunks.")
    for chunk in chunks:
        print(f" - Chunk: {chunk.get('metadata')}")

if __name__ == "__main__":
    asyncio.run(test_sync())
