from fastapi import APIRouter
from app.lms.sync_service import LMSSyncService
import traceback
from app.database import SessionLocal
from app.models import User

router = APIRouter()

@router.get("/debug/sync")
async def debug_sync(email: str):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"error": "User not found"}
    token = user.access_token
    rtoken = user.refresh_token
    db.close()
    
    svc = LMSSyncService(token, email, rtoken)
    try:
        await svc.sync_all_courses(force_reindex=False)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "error": str(e), "trace": traceback.format_exc()}
