import asyncio
from app.lms.sync_service import LMSSyncService
from app.database import SessionLocal
from app.models import User

async def check_google_and_sync():
    print("Checking Google Classroom content...")
    db = SessionLocal()
    # Fetch the specific user we found
    user = db.query(User).filter(User.email == "siddhantwagh724@gmail.com").first()
    
    if not user:
        print("User not found!")
        return

    print(f"User: {user.email}")
    service = LMSSyncService(user.access_token, user.email, user.refresh_token)
    
    # 1. Get Courses from Google
    print("\n--- Google Classroom Data ---")
    courses = await asyncio.to_thread(service.gc_client.get_courses)
    print(f"Courses Found: {len(courses)}")
    for c in courses:
        print(f"- {c['name']} (ID: {c['id']})")
        
        # Check materials for the first course
        print(f"  Checking materials for {c['name']}...")
        materials = await asyncio.to_thread(service.gc_client.get_materials, c['id'])
        print(f"  > Materials: {len(materials)}")
        for m in materials:
             print(f"    - {m.get('title')} ({m.get('id')})")
             
        coursework = await asyncio.to_thread(service.gc_client.get_coursework, c['id'])
        print(f"  > Assignments: {len(coursework)}")
        for w in coursework:
             print(f"    - {w.get('title')} ({w.get('id')})")

    # 2. Check Supermemory Index (what's actually browsable in our app)
    print("\n--- Supermemory Index ---")
    from app.supermemory.client import SupermemoryClient
    sm = SupermemoryClient()
    
    # Check for *any* content for this user
    filters = {
        "AND": [
            {"key": "user_id", "value": user.email}
        ]
    }
    res = await sm.search(query="*", filters=filters, limit=50)
    chunks = res.get("chunks", [])
    print(f"Total Indexed Documents: {len(chunks)}")
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        print(f"- {meta.get('title')} [{meta.get('type')}] (Course: {meta.get('course_name')})")

    db.close()

if __name__ == "__main__":
    asyncio.run(check_google_and_sync())
