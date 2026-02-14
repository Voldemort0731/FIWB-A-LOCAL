from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Course, User, Material
from datetime import datetime
import json

router = APIRouter()

@router.get("/")
def get_courses(user_email: str, db: Session = Depends(get_db)):
    """Fetch courses for a specific user from the database (Optimized)."""
    from sqlalchemy.orm import selectinload
    from app.utils.email import standardize_email
    email = standardize_email(user_email)
    
    user = db.query(User).filter(User.email == email).options(
        selectinload(User.courses)
    ).first()
    
    if not user:
        return []
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "professor": c.professor or "Unknown",
            "platform": c.platform,
            "last_synced": c.last_synced.isoformat() if c.last_synced else None
        }
        for c in user.courses
    ]

@router.get("/{course_id}")
def get_course(course_id: str, user_email: str, db: Session = Depends(get_db)):
    """Fetch details for a specific course."""
    from app.utils.email import standardize_email
    email = standardize_email(user_email)
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"error": "User not found"}
        
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or course not in user.courses:
        return {"error": "Course not found or access denied"}
        
    return {
        "id": course.id,
        "name": course.name,
        "professor": course.professor or "Unknown",
        "platform": course.platform
    }

@router.get("/{course_id}/materials")
async def get_course_materials(course_id: str, user_email: str, db: Session = Depends(get_db)):
    """Fetch all materials (assignments, announcements, etc.) for a course from Supermemory."""
    from app.supermemory.client import SupermemoryClient
    from app.utils.email import standardize_email
    email = standardize_email(user_email)
    
    # Verify user owns/is in this course
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"error": "User not found"}
        
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course or course not in user.courses:
        return {"error": "Access denied"}

    # --- Strategy: Try Local DB First for browsing ---
    # This ensures immediate availability even if vector indexing is slow
    db_materials = db.query(Material).filter(
        Material.course_id == course_id,
        Material.user_id == user.id
    ).order_by(Material.created_at.desc()).all()
    
    if db_materials:
        print(f"DEBUG: Found {len(db_materials)} materials in local DB for {course_id}")
        materials = []
        for m in db_materials:
            # Attachments stored as JSON string in DB
            try:
                atts = json.loads(m.attachments) if m.attachments else []
            except:
                atts = []
                
            materials.append({
                "id": m.id,
                "title": m.title,
                "type": m.type,
                "created_at": m.created_at or datetime.utcnow().isoformat(),
                "due_date": m.due_date,
                "content": m.content or "",
                "source": "Google Classroom",
                "attachments": atts,
                "category": m.type,
                "source_link": m.source_link
            })
        return materials

    # --- Fallback: Supermemory Search (if local DB empty) ---
    sm_client = SupermemoryClient()
    
    # Filter for this specific course and user
    filters = {
        "AND": [
            {"key": "course_id", "value": course_id},
            {"key": "user_id", "value": user_email}
        ]
    }
    
    # Use a space to allow more inclusive matching if results are empty with ""
    results = await sm_client.search(query=" ", filters=filters, limit=50)
    
    # Transform Supermemory chunks into browseable items
    # We want unique documents, not just chunks. 
    # But search returns chunks. We'll group by title to show unique materials.
    materials = []
    seen_titles = set()
    
    for doc in results.get("results", []):
        meta = doc.get("metadata", {})
        title = doc.get("title") or meta.get("title") or "Untitled Material"
        
        if title in seen_titles:
            continue
            
        seen_titles.add(title)
        
        # Attachments come as a JSON string from metadata if we serialized them
        raw_attachments = meta.get("attachments", [])
        if isinstance(raw_attachments, str):
            try:
                attachments_list = json.loads(raw_attachments)
            except:
                attachments_list = []
        else:
            attachments_list = raw_attachments

        # Get first chunk content as preview
        content = ""
        if doc.get("chunks"):
            content = doc["chunks"][0].get("content", "")

        materials.append({
            "id": doc.get("documentId"),
            "title": title,
            "type": meta.get("type", "material"),
            "date": meta.get("created_at", "Recently Sync'd"),
            "due_date": meta.get("due_date"),
            "description": content[:300],  # First 300 chars as preview
            "source": meta.get("source", "Google Classroom"),
            "attachments": attachments_list,
            "category": meta.get("type", "material"),
            "source_link": meta.get("source_link")
        })
        
    return materials
