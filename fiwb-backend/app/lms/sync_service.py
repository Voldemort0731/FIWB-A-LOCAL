from app.lms.google_classroom import GoogleClassroomClient
from app.database import SessionLocal
from app.models import User, Course, Material
from datetime import datetime
import asyncio
import json
import logging
import traceback

from app.intelligence.usage import UsageTracker
from app.utils.email import standardize_email
from app.utils.clients import SharedClients

logger = logging.getLogger("uvicorn.error")

class LMSSyncService:
    def __init__(self, access_token: str, user_email: str, refresh_token: str = None):
        self.gc_client = GoogleClassroomClient(access_token, refresh_token)
        self.user_email = standardize_email(user_email)
        self.sm_client = SharedClients.get_supermemory()

    async def sync_all_courses(self):
        """
        PHASE 1 (Fast): Fetch course list, update DB, return immediately.
        PHASE 2 (Background): Deep content sync, throttled by GlobalSyncManager.
        """
        db = SessionLocal()
        try:
            logger.info(f"[Sync] Starting Phase 1 for {self.user_email}")
            user = db.query(User).filter(User.email == self.user_email).first()
            if not user:
                logger.error(f"[Sync] User {self.user_email} not found.")
                return

            # Fetch courses with a timeout to prevent hanging
            try:
                courses_data = await asyncio.wait_for(
                    self.gc_client.get_courses(),
                    timeout=20.0
                )
                logger.info(f"[Sync] Phase 1: Found {len(courses_data)} courses for {self.user_email}")
            except asyncio.TimeoutError:
                logger.error(f"[Sync] Course fetch timed out for {self.user_email}")
                return
            except Exception as e:
                logger.error(f"[Sync] Course fetch failed for {self.user_email}: {e}")
                return

            # Update course metadata in DB
            active_ids = set()
            for c in courses_data:
                cid = c['id']
                active_ids.add(cid)
                db_course = db.query(Course).filter(Course.id == cid).first()
                if not db_course:
                    db_course = Course(id=cid, name=c['name'], professor="Loading...", platform="Google Classroom")
                    db.add(db_course)
                else:
                    db_course.name = c['name']
                if db_course not in user.courses:
                    user.courses.append(db_course)
                db_course.last_synced = datetime.utcnow()

            # Safety: only prune if we got a real list back
            existing_gc = [c for c in user.courses if c.platform == "Google Classroom"]
            if len(courses_data) == 0 and len(existing_gc) > 0:
                logger.warning(f"[Sync] API returned 0 courses but user had {len(existing_gc)}. Skipping cleanup.")
            else:
                for uc in list(user.courses):
                    if uc.platform == "Google Classroom" and uc.id not in active_ids:
                        user.courses.remove(uc)

            db.commit()
            user_id = user.id
            logger.info(f"[Sync] Phase 1 COMPLETE for {self.user_email} — {len(courses_data)} courses visible")

        except Exception as e:
            logger.error(f"[Sync] Phase 1 failed for {self.user_email}: {e}")
            traceback.print_exc()
            try: db.rollback()
            except: pass
            return
        finally:
            # CRITICAL: Always release the DB connection before Phase 2
            try: db.close()
            except: pass

        # PHASE 2: Fire and forget deep sync (throttled globally)
        from app.utils.concurrency import GlobalSyncManager

        async def deep_sync():
            async with GlobalSyncManager._user_semaphore:
                logger.info(f"[Sync] Phase 2 starting for {self.user_email}")
                for course_data in courses_data:
                    task_db = SessionLocal()
                    try:
                        cid = course_data['id']
                        cname = course_data['name']

                        # Get professor name
                        professor = "Unknown Professor"
                        try:
                            service = await self.gc_client._get_service()
                            tr = await asyncio.wait_for(
                                asyncio.to_thread(lambda: service.courses().teachers().list(courseId=cid).execute()),
                                timeout=5.0
                            )
                            teachers = tr.get('teachers', [])
                            if teachers:
                                professor = teachers[0].get('profile', {}).get('name', {}).get('fullName', 'Unknown')
                            db_c = task_db.query(Course).filter(Course.id == cid).first()
                            if db_c:
                                db_c.professor = professor
                                task_db.commit()
                        except Exception:
                            pass

                        await self._sync_course_content(task_db, cid, cname, professor, user_id)
                    except Exception as e:
                        logger.error(f"[Sync] Phase 2 error for {course_data.get('name')}: {e}")
                    finally:
                        try: task_db.close()
                        except: pass
                        await asyncio.sleep(0.3)

                logger.info(f"[Sync] Phase 2 COMPLETE for {self.user_email}")

        asyncio.create_task(deep_sync())

    async def _sync_course_content(self, db, course_id: str, course_name: str, professor: str, user_id: int):
        """Sync a single course's content. Uses local DB as source of truth for dedup."""
        try:
            # Build local dedup set (fast DB query, no Supermemory round-trip)
            existing_local_ids = set(
                row[0] for row in db.query(Material.id).filter(Material.course_id == course_id).all()
            )

            # Fetch all content types in parallel
            coursework, materials_list, announcements = await asyncio.gather(
                self.gc_client.get_coursework(course_id),
                self.gc_client.get_materials(course_id),
                self.gc_client.get_announcements(course_id),
                return_exceptions=True
            )
            if isinstance(coursework, Exception): coursework = []
            if isinstance(materials_list, Exception): materials_list = []
            if isinstance(announcements, Exception): announcements = []

            new_items = []

            # Process Assignments
            for work in coursework:
                item_id = work.get('id')
                if not item_id or item_id in existing_local_ids:
                    continue
                title = work.get('title', 'Assignment')
                desc = work.get('description', '')[:500]
                due = self._format_date(work.get('dueDate'))
                content, attachments = self._format_rich_item(work, due, "Assignment")
                new_items.append(Material(
                    id=item_id, user_id=user_id, course_id=course_id,
                    title=title, content=desc, type="assignment",
                    due_date=due, created_at=work.get('creationTime'),
                    attachments=json.dumps(attachments),
                    source_link=work.get('alternateLink')
                ))
                existing_local_ids.add(item_id)
                # Index to Supermemory in background
                asyncio.create_task(self._index_to_supermemory(content, title, desc, item_id, course_id, course_name, professor, "assignment", work.get('alternateLink')))

            # Process Materials
            for mat in materials_list:
                item_id = mat.get('id')
                if not item_id or item_id in existing_local_ids:
                    continue
                title = mat.get('title', 'Material')
                desc = mat.get('description', '')[:500]
                content, attachments = self._format_rich_item(mat, None, "Course Material")
                new_items.append(Material(
                    id=item_id, user_id=user_id, course_id=course_id,
                    title=title, content=desc, type="material",
                    due_date=None, created_at=mat.get('creationTime'),
                    attachments=json.dumps(attachments),
                    source_link=mat.get('alternateLink')
                ))
                existing_local_ids.add(item_id)
                asyncio.create_task(self._index_to_supermemory(content, title, desc, item_id, course_id, course_name, professor, "material", mat.get('alternateLink')))

            # Process Announcements
            for ann in announcements:
                item_id = ann.get('id')
                if not item_id or item_id in existing_local_ids:
                    continue
                text = ann.get('text', '')
                if not text:
                    continue
                title = f"Announcement: {course_name}"
                desc = text[:500]
                content = f"Announcement from {professor} in {course_name}:\n{text}"
                new_items.append(Material(
                    id=item_id, user_id=user_id, course_id=course_id,
                    title=title, content=desc, type="announcement",
                    due_date=None, created_at=ann.get('creationTime'),
                    attachments=json.dumps([]),
                    source_link=ann.get('alternateLink')
                ))
                existing_local_ids.add(item_id)
                asyncio.create_task(self._index_to_supermemory(content, title, desc, item_id, course_id, course_name, professor, "announcement", ann.get('alternateLink')))

            # Bulk insert all new items
            if new_items:
                db.bulk_save_objects(new_items)
                db.commit()
                logger.info(f"[Sync] Saved {len(new_items)} new items for course {course_name}")

        except Exception as e:
            logger.error(f"[Sync] Content sync error for {course_id}: {e}")
            try: db.rollback()
            except: pass

    async def _index_to_supermemory(self, content, title, desc, item_id, course_id, course_name, professor, item_type, source_link):
        """Fire-and-forget Supermemory indexing. Never blocks the main sync."""
        try:
            metadata = {
                "user_id": self.user_email,
                "course_id": course_id,
                "course_name": course_name,
                "professor": professor,
                "type": item_type,
                "source_id": item_id,
                "source": "google_classroom",
                "source_link": source_link
            }
            await self.sm_client.add_document(content, metadata, title=title, description=desc[:200])
        except Exception as e:
            logger.warning(f"[Sync] Supermemory index failed for {item_id}: {e}")

    def _format_date(self, date_dict: dict) -> str:
        if not date_dict: return None
        try:
            return f"{date_dict.get('year')}-{date_dict.get('month'):02d}-{date_dict.get('day'):02d}"
        except:
            return None

    def _format_rich_item(self, item: dict, due_date_str: str, label: str) -> tuple:
        title = item.get('title', 'Untitled')
        description = item.get('description', 'No description')
        content = f"{label}: {title}\nDescription: {description}\n"
        if due_date_str:
            content += f"Due: {due_date_str}\n"
        materials = item.get('materials', [])
        attachments = []
        if materials:
            mat_text, attachments = self._format_materials(materials)
            content += f"Attachments:\n{mat_text}"
        return content, attachments

    def _format_materials(self, materials: list) -> tuple:
        lines = []
        attachments = []
        for m in materials:
            if 'driveFile' in m:
                df = m['driveFile'].get('driveFile', {})
                title = df.get('title', 'Drive File')
                link = df.get('alternateLink', '')
                mime = df.get('mimeType', '')
                ftype = 'pdf' if 'pdf' in mime else 'document' if 'document' in mime else 'file'
                lines.append(f"- [Drive] {title}: {link}")
                attachments.append({"type": "drive", "file_type": ftype, "title": title, "url": link, "file_id": df.get('id', ''), "mime_type": mime})
            elif 'youtubeVideo' in m:
                yt = m['youtubeVideo']
                title = yt.get('title', 'Video')
                link = yt.get('alternateLink', '')
                vid = yt.get('id', '')
                lines.append(f"- [Video] {title}: {link}")
                attachments.append({"type": "video", "file_type": "youtube", "title": title, "url": link, "video_id": vid, "thumbnail": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg"})
            elif 'link' in m:
                l = m['link']
                title = l.get('title', 'Link')
                url = l.get('url', '')
                lines.append(f"- [Web] {title}: {url}")
                attachments.append({"type": "link", "file_type": "web", "title": title, "url": url})
            elif 'form' in m:
                f = m['form']
                title = f.get('title', 'Form')
                url = f.get('formUrl', '')
                lines.append(f"- [Form] {title}: {url}")
                attachments.append({"type": "form", "file_type": "google_form", "title": title, "url": url})
        return "\n".join(lines) or "None", attachments
