from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import pypdf
from app.models import Material, Course, User
from app.database import SessionLocal
from app.supermemory.client import SupermemoryClient
import datetime
import json
import asyncio

class DriveSyncService:
    def __init__(self, access_token: str, user_email: str, refresh_token: str = None):
        from app.config import settings
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        self.service = None
        self.user_email = user_email
        self.sm_client = SupermemoryClient()

    async def _get_service(self):
        """Thread-safe and async-safe service builder."""
        if self.service is None:
            from app.utils.google_lock import GoogleApiLock
            async with GoogleApiLock.get_lock():
                if self.service is None:
                    try:
                        self.service = await asyncio.to_thread(
                            lambda: build('drive', 'v3', credentials=self.creds, static_discovery=True)
                        )
                    except Exception as e:
                        print(f"Failed to initialize Drive service: {e}")
                        raise e
        return self.service

    async def list_root_folders(self):
        """List folders in the root of Google Drive."""
        service = await self._get_service()
        from app.utils.google_lock import GoogleApiLock
        async with GoogleApiLock.get_lock():
            results = await asyncio.to_thread(
                lambda: service.files().list(
                    q="mimeType = 'application/vnd.google-apps.folder' and 'root' in parents and trashed = false",
                    fields="files(id, name, webViewLink)",
                    pageSize=50
                ).execute()
            )
        return results.get('files', [])

    async def sync_folder(self, folder_id: str):
        """Sync all PDF and Text files from a specific folder."""
        # Ensure a virtual "Google Drive" course exists in DB for grouping
        db = SessionLocal()
        drive_course = db.query(Course).filter(Course.id == "GOOGLE_DRIVE").first()
        if not drive_course:
            drive_course = Course(
                id="GOOGLE_DRIVE",
                name="Personal Google Drive",
                professor="Self",
                platform="Google Drive"
            )
            db.add(drive_course)
            db.commit()

        # Link user to this virtual course
        user = db.query(User).filter(User.email == self.user_email).first()
        if user and drive_course not in user.courses:
            user.courses.append(drive_course)
            db.commit()

        # Fetch files in folder
        query = f"'{folder_id}' in parents and (mimeType = 'application/pdf' or mimeType = 'text/plain' or mimeType = 'application/vnd.google-apps.document') and trashed = false"
        service = await self._get_service()
        from app.utils.google_lock import GoogleApiLock
        async with GoogleApiLock.get_lock():
            results = await asyncio.to_thread(
                lambda: service.files().list(
                    q=query,
                    fields="files(id, name, mimeType, webViewLink, createdTime, modifiedTime)",
                    pageSize=100
                ).execute()
            )
        
        files = results.get('files', [])
        synced_count = 0

        for file in files:
            file_id = file['id']
            # Check if already synced in DB
            existing = db.query(Material).filter(Material.id == file_id).first()
            if existing:
                continue

            content = ""
            try:
                content = await self._get_file_content(file)
            except Exception as e:
                print(f"Failed to extract content for {file['name']}: {e}")
                continue

            # Save to Local DB
            new_material = Material(
                id=file_id,
                course_id="GOOGLE_DRIVE",
                title=file['name'],
                content=content[:5000], # Preview content
                type="drive_file",
                created_at=file.get('createdTime'),
                source_link=file.get('webViewLink'),
                attachments=json.dumps([{
                    "id": file_id,
                    "title": file['name'],
                    "url": file.get('webViewLink'),
                    "type": "drive_file"
                }])
            )
            db.add(new_material)
            db.commit()

            # Sync to Supermemory
            await self.sm_client.add_document(
                content=content,
                title=file['name'],
                description=f"File from Google Drive synced on {datetime.datetime.utcnow().isoformat()}",
                metadata={
                    "user_id": self.user_email,
                    "source": "google_drive",
                    "course_id": "GOOGLE_DRIVE",
                    "file_id": file_id,
                    "type": "drive_file",
                    "source_link": file.get('webViewLink')
                }
            )
            from app.intelligence.usage import UsageTracker
            UsageTracker.log_index_event(self.user_email, content=content)
            synced_count += 1

        db.close()
        return synced_count

    async def _get_file_content(self, file_meta):
        file_id = file_meta['id']
        mime_type = file_meta['mimeType']
        
        if mime_type == 'application/vnd.google-apps.document':
            # Export Google Doc as text
            service = await self._get_service()
            from app.utils.google_lock import GoogleApiLock
            async with GoogleApiLock.get_lock():
                request = service.files().export_media(fileId=file_id, mimeType='text/plain')
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = await asyncio.to_thread(downloader.next_chunk)
            return fh.getvalue().decode('utf-8')
            
        elif mime_type == 'text/plain':
            service = await self._get_service()
            from app.utils.google_lock import GoogleApiLock
            async with GoogleApiLock.get_lock():
                request = service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = await asyncio.to_thread(downloader.next_chunk)
            return fh.getvalue().decode('utf-8')

        elif mime_type == 'application/pdf':
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # Extract PDF Text
            pdf_reader = pypdf.PdfReader(io.BytesIO(fh.getvalue()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
            
        return ""
