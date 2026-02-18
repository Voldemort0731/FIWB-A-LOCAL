from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from app.config import settings
import asyncio
import logging

logger = logging.getLogger("uvicorn.error")

class GoogleClassroomClient:
    def __init__(self, token: str, refresh_token: str = None):
        self.creds = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        self.user_email = "me"
        self._service = None

    async def _get_service(self):
        """Build the Classroom service. No global lock — each user gets their own instance."""
        if self._service is None:
            # Refresh token in a thread if needed
            if self.creds.refresh_token and (self.creds.expired or not self.creds.valid):
                try:
                    await asyncio.to_thread(self.creds.refresh, Request())
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")

            try:
                self._service = await asyncio.to_thread(
                    lambda: build('classroom', 'v1', credentials=self.creds, static_discovery=True)
                )
            except Exception as e:
                logger.error(f"Failed to build Classroom service: {e}")
                raise e
        return self._service

    async def get_courses(self):
        """Fetch all courses the user is enrolled in or teaching."""
        service = await self._get_service()

        async def fetch_student():
            try:
                r = await asyncio.to_thread(
                    lambda: service.courses().list(studentId='me', courseStates=['ACTIVE']).execute()
                )
                return r.get('courses', [])
            except Exception as e:
                logger.warning(f"Student courses fetch failed: {e}")
                return []

        async def fetch_teacher():
            try:
                r = await asyncio.to_thread(
                    lambda: service.courses().list(teacherId='me', courseStates=['ACTIVE']).execute()
                )
                return r.get('courses', [])
            except Exception as e:
                logger.warning(f"Teacher courses fetch failed: {e}")
                return []

        res_student, res_teacher = await asyncio.gather(fetch_student(), fetch_teacher())
        all_courses = res_student + res_teacher
        unique = {c['id']: c for c in all_courses}
        return list(unique.values())

    async def get_coursework(self, course_id: str):
        """Fetch assignments for a course."""
        service = await self._get_service()
        try:
            r = await asyncio.to_thread(
                lambda: service.courses().courseWork().list(courseId=course_id).execute()
            )
            return r.get('courseWork', [])
        except Exception as e:
            logger.warning(f"Coursework fetch failed for {course_id}: {e}")
            return []

    async def get_announcements(self, course_id: str):
        """Fetch announcements for a course."""
        service = await self._get_service()
        try:
            r = await asyncio.to_thread(
                lambda: service.courses().announcements().list(courseId=course_id).execute()
            )
            return r.get('announcements', [])
        except Exception as e:
            logger.warning(f"Announcements fetch failed for {course_id}: {e}")
            return []

    async def get_materials(self, course_id: str):
        """Fetch course materials."""
        service = await self._get_service()
        try:
            r = await asyncio.to_thread(
                lambda: service.courses().courseWorkMaterials().list(courseId=course_id).execute()
            )
            return r.get('courseWorkMaterial', [])
        except Exception as e:
            logger.warning(f"Materials fetch failed for {course_id}: {e}")
            return []
