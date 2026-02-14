"""
Production-ready health check endpoint
"""
from fastapi import APIRouter
from app.database import SessionLocal
from app.supermemory.client import SupermemoryClient
import httpx

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Comprehensive health check for production monitoring
    """
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check Database
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_status["services"]["database"] = "connected"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Supermemory
    try:
        sm_client = SupermemoryClient()
        # Simple ping - don't actually search
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{sm_client.base_url}/health")
            if response.status_code == 200:
                health_status["services"]["supermemory"] = "connected"
            else:
                health_status["services"]["supermemory"] = f"status: {response.status_code}"
    except Exception as e:
        health_status["services"]["supermemory"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check OpenAI (optional - don't want to burn API calls)
    from app.config import settings
    if settings.OPENAI_API_KEY:
        health_status["services"]["openai"] = "configured"
    else:
        health_status["services"]["openai"] = "not_configured"
        health_status["status"] = "degraded"
    
    return health_status

@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "FIWB AI Backend",
        "version": "1.0.0",
        "status": "operational"
    }
