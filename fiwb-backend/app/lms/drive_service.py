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

        # Fetch files in folder - support many file types with pagination
        # Include: PDFs, text files, Google Docs/Sheets/Slides, Word/Excel/PowerPoint, images, and more
        mime_types = [
            'application/pdf',
            'text/plain',
            'application/vnd.google-apps.document',  # Google Docs
            'application/vnd.google-apps.spreadsheet',  # Google Sheets
            'application/vnd.google-apps.presentation',  # Google Slides
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
            'application/msword',  # .doc
            'application/vnd.ms-excel',  # .xls
            'application/vnd.ms-powerpoint',  # .ppt
            'application/vnd.oasis.opendocument.text',
            'application/vnd.oasis.opendocument.spreadsheet',
            'application/vnd.oasis.opendocument.presentation',
            'image/jpeg',
            'image/png',
            'image/gif',
            'video/mp4',
            'video/quicktime',
            'video/webm',
            'application/zip',
            'application/x-zip-compressed',
            'image/webp',
            'text/html',
            'text/csv',
            'application/rtf',
            'text/markdown'
        ]
        mime_query = ' or '.join([f"mimeType = '{mt}'" for mt in mime_types])
        query = f"'{folder_id}' in parents and ({mime_query}) and trashed = false"
        service = await self._get_service()
        
        # Recursively fetch all files in folder and subfolders
        files = await self._get_all_files_recursive(folder_id, mime_types)
        
        print(f"[Drive Sync] Found {len(files)} files in folder {folder_id} (recursive)")
        synced_count = 0

        # Process files in small batches to avoid event loop starvation
        batch_size = 3  # Small batch size because file downloads are heavy
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            
            for file in batch:
                file_id = file['id']
                # Check if already synced in DB
                existing = db.query(Material).filter(Material.id == file_id).first()
                if existing:
                    if not existing.user_id:
                        existing.user_id = user.id
                        db.commit()
                    continue

                content = ""
                try:
                    content = await self._get_file_content(file)
                except Exception as e:
                    print(f"Failed to extract content for {file['name']}: {e}")
                    continue

                # Save to Local DB
                try:
                    new_material = Material(
                        id=file_id,
                        user_id=user.id,
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
                except Exception as db_err:
                    print(f"Error saving file {file['name']} to DB: {db_err}")
                    db.rollback()
            
            # Yield control to event loop after each batch
            await asyncio.sleep(0.2)

        db.close()
        return synced_count

    async def _get_file_content(self, file_meta):
        file_id = file_meta['id']
        mime_type = file_meta['mimeType']
        file_name = file_meta.get('name', 'Unknown')
        
        # Google Docs - export as plain text
        if mime_type == 'application/vnd.google-apps.document':
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
        
        # Google Sheets - export as CSV
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            service = await self._get_service()
            from app.utils.google_lock import GoogleApiLock
            async with GoogleApiLock.get_lock():
                request = service.files().export_media(fileId=file_id, mimeType='text/csv')
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = await asyncio.to_thread(downloader.next_chunk)
            return fh.getvalue().decode('utf-8')
        
        # Google Slides - export as plain text
        elif mime_type == 'application/vnd.google-apps.presentation':
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
            
        # Plain text files
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

        # PDF files
        elif mime_type == 'application/pdf':
            service = await self._get_service()
            from app.utils.google_lock import GoogleApiLock
            async with GoogleApiLock.get_lock():
                request = service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = await asyncio.to_thread(downloader.next_chunk)
            
            # Extract PDF Text
            pdf_reader = pypdf.PdfReader(io.BytesIO(fh.getvalue()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            
            if not text.strip():
                return f"PDF File: {file_name} (Scanned document or unreadable text). View original file to read content."
            return text
        
        # CSV files
        elif mime_type == 'text/csv':
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
        
        # HTML files
        elif mime_type == 'text/html':
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
        
        # Markdown files
        elif mime_type == 'text/markdown':
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
        
        # For images and binary files (Word, Excel, PowerPoint, etc.)
        # We can't extract text easily, so return metadata
        elif mime_type.startswith('image/') or mime_type.startswith('video/'):
            return f"Media file: {file_name} (Type: {mime_type})"
        
        elif mime_type == 'application/zip' or mime_type == 'application/x-zip-compressed':
            return f"Archive file: {file_name} (Type: {mime_type})"
        
        elif mime_type in [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/msword',
            'application/vnd.ms-excel',
            'application/vnd.ms-powerpoint',
            'application/rtf'
        ]:
            file_type_names = {
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word Document',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel Spreadsheet',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PowerPoint Presentation',
                'application/msword': 'Word Document (Legacy)',
                'application/vnd.ms-excel': 'Excel Spreadsheet (Legacy)',
                'application/vnd.ms-powerpoint': 'PowerPoint Presentation (Legacy)',
                'application/rtf': 'Rich Text Document'
            }
            type_name = file_type_names.get(mime_type, 'Office Document')
            return f"{type_name}: {file_name}"
            
        return ""
    
    async def _get_all_files_recursive(self, folder_id: str, mime_types: list) -> list:
        """Recursively fetch files from folder and subfolders."""
        all_files = []
        folders_to_process = [folder_id]
        processed_folders = set()
        
        service = await self._get_service()
        mime_query = ' or '.join([f"mimeType = '{mt}'" for mt in mime_types])
        
        while folders_to_process:
            current_folder_id = folders_to_process.pop(0)
            if current_folder_id in processed_folders:
                continue
            
            processed_folders.add(current_folder_id)
            print(f"[Drive Sync] Scanning folder {current_folder_id}...")
            
            # 1. Fetch files in this folder
            # Query: direct children AND (matching mime types OR is a folder)
            query = f"'{current_folder_id}' in parents and (mimeType = 'application/vnd.google-apps.folder' or {mime_query}) and trashed = false"
            
            page_token = None
            while True:
                from app.utils.google_lock import GoogleApiLock
                async with GoogleApiLock.get_lock():
                    request_kwargs = {
                        'q': query,
                        'fields': "nextPageToken, files(id, name, mimeType, webViewLink, createdTime, modifiedTime)",
                        'pageSize': 100
                    }
                    if page_token:
                        request_kwargs['pageToken'] = page_token
                    
                    try:
                        results = await asyncio.to_thread(
                            lambda kw=request_kwargs: service.files().list(**kw).execute()
                        )
                    except Exception as e:
                        print(f"Error listing files in folder {current_folder_id}: {e}")
                        break
                
                items = results.get('files', [])
                for item in items:
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        if item['id'] not in processed_folders:
                            folders_to_process.append(item['id'])
                    else:
                        all_files.append(item)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            # Yield to event loop
            await asyncio.sleep(0.1)
            
        return all_files

