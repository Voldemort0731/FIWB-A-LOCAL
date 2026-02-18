from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from app.config import settings
import asyncio
import threading
import logging

logger = logging.getLogger("uvicorn.error")

from app.utils.locks import GLOBAL_API_LOCK

class GoogleClassroomClient:
    def __init__(self, token: str, refresh_token: str = None):
        self.creds = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )
        self._service = None
        # Use the global lock, not per-instance

    async def _get_service(self):
        """Build the Classroom service (lazy, once per instance)."""
        if self._service is not None:
            return self._service

        async with GLOBAL_API_LOCK:
            # Double-check after acquiring lock
            if self._service is not None:
                return self._service

            # Refresh token if needed (synchronous, safe in thread)
            if self.creds.refresh_token and (self.creds.expired or not self.creds.valid):
                try:
                    await asyncio.to_thread(self.creds.refresh, Request())
                    logger.info("Token refreshed successfully")
                except Exception as e:
                    logger.warning(f"Token refresh failed (will try with existing): {e}")

            try:
                self._service = await asyncio.to_thread(
                    lambda: build('classroom', 'v1', credentials=self.creds, static_discovery=True)
                )
            except Exception as e:
                logger.error(f"Failed to build Classroom service: {e}")
                raise
        return self._service

    async def _execute(self, request_fn):
        """
        Execute a Google API request safely using the GLOBAL process lock.
        Prevents ANY concurrent Google API calls process-wide.
        """
        async with GLOBAL_API_LOCK:
            return await asyncio.to_thread(request_fn)

    async def get_courses(self):
        """Fetch all active courses. Sequential (not parallel) to avoid httplib2 segfault."""
        service = await self._get_service()

        # IMPORTANT: Do NOT use asyncio.gather here.
        # Running two asyncio.to_thread calls on the same httplib2-backed service
        # object simultaneously causes a segmentation fault in Python 3.12.
        student_courses = []
        teacher_courses = []

        try:
            result = await self._execute(
                lambda: service.courses().list(studentId='me', courseStates=['ACTIVE']).execute()
            )
            student_courses = result.get('courses', [])
        except Exception as e:
            logger.warning(f"Student courses fetch failed: {e}")

        try:
            result = await self._execute(
                lambda: service.courses().list(teacherId='me', courseStates=['ACTIVE']).execute()
            )
            teacher_courses = result.get('courses', [])
        except Exception as e:
            logger.warning(f"Teacher courses fetch failed: {e}")

        all_courses = student_courses + teacher_courses
        unique = {c['id']: c for c in all_courses}
        return list(unique.values())

    async def get_coursework(self, course_id: str):
        """Fetch assignments for a course."""
        service = await self._get_service()
        try:
            r = await self._execute(
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
            r = await self._execute(
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
            r = await self._execute(
                lambda: service.courses().courseWorkMaterials().list(courseId=course_id).execute()
            )
            return r.get('courseWorkMaterial', [])
        except Exception as e:
            logger.warning(f"Materials fetch failed for {course_id}: {e}")
            return []

    async def get_teachers(self, course_id: str):
        """Fetch teachers for a course. Returns empty list on 403 (no permission)."""
        service = await self._get_service()
        try:
            r = await self._execute(
                lambda: service.courses().teachers().list(courseId=course_id).execute()
            )
            return r.get('teachers', [])
        except Exception as e:
            # 403 is common — students can't list teachers in all courses
            logger.debug(f"Teachers fetch skipped for {course_id}: {e}")
            return []
