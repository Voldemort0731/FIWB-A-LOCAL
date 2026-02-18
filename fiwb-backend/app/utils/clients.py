import httpx
from app.config import settings

class SharedClients:
    """
    Singleton container for shared HTTP and API clients.
    Prevents connection churn under 70+ concurrent users.
    """
    _sm_client = None
    _openai_client = None
    _http_client = None  # General-purpose HTTP client (Google APIs, etc.)

    @classmethod
    def get_http_client(cls) -> httpx.AsyncClient:
        """General-purpose HTTPX client for Google OAuth, UserInfo, etc."""
        if cls._http_client is None:
            cls._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(45.0),
                limits=httpx.Limits(
                    max_connections=200,
                    max_keepalive_connections=50,
                    keepalive_expiry=30.0
                )
            )
        return cls._http_client

    @classmethod
    def get_supermemory(cls):
        """
        Supermemory client — has its own dedicated HTTP client with auth headers.
        Do NOT inject the general HTTP client here (it has no SM auth headers).
        """
        if cls._sm_client is None:
            from app.supermemory.client import SupermemoryClient
            cls._sm_client = SupermemoryClient()
        return cls._sm_client

    @classmethod
    def get_openai(cls):
        """Shared AsyncOpenAI client."""
        if cls._openai_client is None:
            from openai import AsyncOpenAI
            cls._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return cls._openai_client
