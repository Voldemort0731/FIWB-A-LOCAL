from fastapi import APIRouter
from app.lms.google_classroom import GoogleClassroomClient
import traceback

router = APIRouter()

@router.get("/debug/courses")
async def debug_courses(token: str):
    try:
        gc = GoogleClassroomClient(token)
        service = await gc._get_service()
        res = service.courses().list(studentId='me', courseStates=['ACTIVE']).execute()
        return {"status": "ok", "courses": res.get('courses', [])}
    except Exception as e:
        return {"status": "error", "error": str(e), "trace": traceback.format_exc()}
