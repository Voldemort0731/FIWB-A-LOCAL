from app.lms.moodle import MoodleClient
from app.supermemory.client import SupermemoryClient
from app.database import SessionLocal
from app.models import User, Course, Material
from datetime import datetime
import asyncio
import json
import logging

logger = logging.getLogger("uvicorn.error")

class MoodleSyncService:
    def __init__(self, moodle_url: str, moodle_token: str, user_email: str):
        self.client = MoodleClient(moodle_url, moodle_token)
        self.user_email = user_email
        self.sm_client = SupermemoryClient()

    async def sync_all(self):
        """Sync everything from Moodle."""
        db = SessionLocal()
        try:
            logger.info(f"Starting Moodle sync for {self.user_email}...")
            user = db.query(User).filter(User.email == self.user_email).first()
            if not user:
                return

            courses = await self.client.get_courses()
            if not courses:
                logger.warning(f"No courses found for user {self.user_email} on Moodle.")
                return

            for course_data in courses:
                course_id = f"moodle_{course_data['id']}"
                course_name = course_data.get('fullname', course_data.get('shortname', 'Unknown Course'))
                
                # 1. Upsert Course
                db_course = db.query(Course).filter(Course.id == course_id).first()
                if not db_course:
                    db_course = Course(
                        id=course_id,
                        name=course_name,
                        professor="Moodle Instructor",
                        platform="Moodle"
                    )
                    db.add(db_course)
                else:
                    db_course.name = course_name
                
                if db_course not in user.courses:
                    user.courses.append(db_course)
                db.commit()

                # 2. Sync Course Content
                await self._sync_course_content(db, course_data['id'], course_id, course_name)
                
        finally:
            db.close()

    async def _sync_course_content(self, db, moodle_id: int, db_id: str, course_name: str):
        """Sync course contents (resources, modules)."""
        contents = await self.client.get_course_contents(moodle_id)
        if not contents:
            return

        for section in contents:
            modules = section.get('modules', [])
            for mod in modules:
                mod_id = f"moodle_mod_{mod['id']}"
                title = mod.get('name', 'Moodle Resource')
                mod_type = mod.get('modname') # resource, url, forum, assign, etc.
                
                # Check duplication in DB
                existing = db.query(Material).filter(Material.id == mod_id).first()
                if existing: continue

                content_parts = [f"Moodle Resource in {course_name}", f"Section: {section.get('name', 'General')}"]
                description = mod.get('description', '')
                if description:
                    content_parts.append(f"Description: {description}")

                attachments = []
                if mod_type == 'resource' and mod.get('contents'):
                    for file in mod['contents']:
                        attachments.append({
                            "id": f"file_{file.get('fileurl', '').split('?')[0]}",
                            "title": file.get('filename', 'Attached File'),
                            "url": file.get('fileurl', '') + ("&token=" + self.client.token if '?' in file.get('fileurl', '') else "?token=" + self.client.token),
                            "type": "file"
                        })
                elif mod_type == 'url' and mod.get('contents'):
                    for link in mod['contents']:
                        attachments.append({
                            "type": "link",
                            "title": title,
                            "url": link.get('fileurl')
                        })

                full_content = "\n".join(content_parts)
                
                # 1. Add to Local DB
                db_mat = Material(
                    id=mod_id,
                    course_id=db_id,
                    title=title,
                    content=description or title,
                    type=mod_type,
                    attachments=json.dumps(attachments),
                    source_link=mod.get('url')
                )
                db.add(db_mat)
                db.commit()

                # 2. Add to Supermemory
                metadata = {
                    "user_id": self.user_email,
                    "course_id": db_id,
                    "course_name": course_name,
                    "type": mod_type,
                    "source": "moodle",
                    "source_id": mod_id,
                    "source_link": mod.get('url')
                }
                
                await self.sm_client.add_document(
                    content=full_content,
                    metadata=metadata,
                    title=f"Moodle: {title}",
                    description=description[:200] if description else f"Resource from {course_name}"
                )
                from app.intelligence.usage import UsageTracker
                UsageTracker.log_index_event(self.user_email, content=full_content)
