import asyncio
from app.lms.sync_service import LMSSyncService
from app.database import SessionLocal
from app.models import User

async def check_course_content():
    """Check what content exists in the Google Classroom course"""
    db = SessionLocal()
    user = db.query(User).filter(User.email == "siddhantwagh724@gmail.com").first()
    
    if not user:
        print("❌ User not found")
        return
    
    if not user.access_token:
        print("❌ No access token")
        return
    
    print(f"✅ Found user: {user.email}")
    print(f"📧 Google ID: {user.google_id}")
    print(f"🔑 Has access token: {bool(user.access_token)}")
    print(f"🔄 Has refresh token: {bool(user.refresh_token)}")
    print()
    
    # Create sync service
    service = LMSSyncService(user.access_token, user.email, user.refresh_token)
    
    # Get courses
    print("📚 Fetching courses...")
    courses = await service.gc_client.get_courses()
    print(f"Found {len(courses)} courses:")
    for c in courses:
        print(f"  - {c.get('name')} (ID: {c.get('id')})")
    print()
    
    # For each course, check content
    for course in courses:
        course_id = course.get('id')
        course_name = course.get('name')
        print(f"\n📖 Checking content for: {course_name}")
        print("=" * 60)
        
        # Coursework
        try:
            coursework = await service.gc_client.get_coursework(course_id)
            print(f"  📝 Assignments: {len(coursework)}")
            for work in coursework[:3]:  # Show first 3
                print(f"    - {work.get('title', 'Untitled')}")
        except Exception as e:
            print(f"  ❌ Error fetching coursework: {e}")
        
        # Materials
        try:
            materials = await service.gc_client.get_materials(course_id)
            print(f"  📄 Materials: {len(materials)}")
            for mat in materials[:3]:  # Show first 3
                print(f"    - {mat.get('title', 'Untitled')}")
        except Exception as e:
            print(f"  ❌ Error fetching materials: {e}")
        
        # Announcements
        try:
            announcements = await service.gc_client.get_announcements(course_id)
            print(f"  📢 Announcements: {len(announcements)}")
            for ann in announcements[:3]:  # Show first 3
                text = ann.get('text', '')[:50]
                print(f"    - {text}...")
        except Exception as e:
            print(f"  ❌ Error fetching announcements: {e}")
    
    db.close()

if __name__ == "__main__":
    asyncio.run(check_course_content())
