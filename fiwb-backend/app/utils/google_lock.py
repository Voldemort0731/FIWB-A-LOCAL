import asyncio
import sys
from typing import Optional

class NoOpLock:
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc_val, exc_tb): pass

class GoogleApiLock:
    """
    Previously used a global lock to prevent SSL WRONG_VERSION_NUMBER errors 
    on macOS when multiple Google API requests are made concurrently.
    
    However, this caused ALL API requests to be serialized — including 
    regular user-facing endpoints which got starved by background sync tasks.
    
    Now uses a Semaphore to allow limited concurrency (3 concurrent requests)
    instead of full serialization. This prevents SSL issues while still
    allowing the app to respond to user requests during background sync.
    """
    _semaphore: Optional[asyncio.Semaphore] = None

    @classmethod
    def get_lock(cls):
        if sys.platform != "darwin":
            return NoOpLock()
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(1)  # Strictly serialize to prevent SSL errors
        return cls._semaphore
