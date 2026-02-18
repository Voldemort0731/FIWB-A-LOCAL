import asyncio
import logging

logger = logging.getLogger("uvicorn.error")

class GlobalSyncManager:
    """
    Orchestrates concurrency across the entire application.
    Prevents 70 users from killing the DB pool or Google API.
    """
    # Max independent users syncing deeply at once
    _user_semaphore = asyncio.Semaphore(5)
    
    # Max concurrent API calls to Google/OpenAI across the whole app
    _api_semaphore = asyncio.Semaphore(10)

    @classmethod
    async def run_deep_task(cls, task_coro):
        """Wraps a task to ensure it respects global server limits."""
        async with cls._user_semaphore:
            return await task_coro

    @classmethod
    def get_api_lock(cls):
        return cls._api_semaphore
