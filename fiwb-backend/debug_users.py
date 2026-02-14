from app.database import SessionLocal
from app.models import User, Course

def list_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Total Users: {len(users)}")
        for user in users:
            token_status = "✅ Token Present" if user.access_token else "❌ Token Missing"
            refresh_status = "✅ Refresh Token" if user.refresh_token else "❌ No Refresh Token"
            print(f"- {user.email} | {token_status} | {refresh_status}")
            
            # List courses for this user
            print(f"  Courses ({len(user.courses)}):")
            for c in user.courses:
                print(f"    - {c.name} ({c.id})")
        
        courses = db.query(Course).all()
        print(f"\nTotal Synced Courses in DB: {len(courses)}")
    finally:
        db.close()

if __name__ == "__main__":
    list_users()
