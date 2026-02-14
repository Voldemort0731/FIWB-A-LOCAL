from app.database import SessionLocal
from app.models import Material, Course, User
import json

def test_api_logic(course_id, user_email):
    db = SessionLocal()
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        print("User not found")
        return
        
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        print("Course not found")
        return
        
    if course not in user.courses:
        print("Course not linked to user")
        return
        
    db_materials = db.query(Material).filter(Material.course_id == course_id).all()
    print(f"Found {len(db_materials)} materials in DB for {course_id}")
    for m in db_materials:
        print(f"- {m.title}")
    db.close()

if __name__ == "__main__":
    test_api_logic("843626074076", "siddhantwagh724@gmail.com")
