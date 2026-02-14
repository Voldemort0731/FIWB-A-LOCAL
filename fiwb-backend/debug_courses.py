from app.database import SessionLocal
from app.models import User, Course
import json

db = SessionLocal()
email = "owaissayyed2007@gmail.com"
user = db.query(User).filter(User.email == email).first()

if not user:
    print(f"User {email} not found")
else:
    courses = [
        {
            "id": c.id,
            "name": c.name,
            "professor": c.professor or "Unknown",
            "platform": c.platform
        }
        for c in user.courses
    ]
    print(json.dumps(courses, indent=2))

db.close()
