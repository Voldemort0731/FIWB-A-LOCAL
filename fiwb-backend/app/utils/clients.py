import httpx
from app.config import settings

class SharedClients:
    """
    Singleton-style container for HTTP and API clients.
    Ensures connection pool reuse across the entire application.
    """
    _sm_client = None
    _openai_client = None
    _http_client = None

    @classmethod
    def get_http_client(cls):
        """Reusable HTTPX Client (Async) with optimized pooling."""
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
        """Reusable SupermemoryClient wrapper."""
        if cls._sm_client is None:
            from app.supermemory.client import SupermemoryClient
            cls._sm_client = SupermemoryClient()
            # Inject the shared http client into it
            cls._sm_client.client = cls.get_http_client() 
        return cls._sm_client

    @classmethod
    def get_openai(cls):
        """Reusable OpenAI Client."""
        if cls._openai_client is None:
            from openai import AsyncOpenAI
            cls._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return cls._openai_client
