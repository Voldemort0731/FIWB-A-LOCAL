import asyncio
import sys
from typing import Optional

class NoOpLock:
    async def __aenter__(self): return self
    async def __aexit__(self, exc_type, exc_val, exc_tb): pass

class GoogleApiLock:
    """
    Global lock to prevent SSL WRONG_VERSION_NUMBER errors on macOS 
    when multiple Google API requests are made concurrently.
    On Windows/Linux, we use a NoOpLock to allow full concurrency.
    """
    _lock: Optional[asyncio.Lock] = None

    @classmethod
    def get_lock(cls):
        if sys.platform != "darwin":
            return NoOpLock()
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock
