import asyncio

# Global lock to prevent httplib2/ssl segmentation faults across the entire application process.
# Any service using google-api-python-client (which uses httplib2) MUST acquire this lock 
# before calling .execute() in a thread.
GLOBAL_API_LOCK = asyncio.Lock()
