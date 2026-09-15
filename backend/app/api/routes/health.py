from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.cache.redis import get_redis_client
from app.core.logging import logger
from app.core.config import settings
from datetime import datetime
import sys

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check endpoint for monitoring service status.
    Returns detailed status of all critical services.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": getattr(settings, 'ENVIRONMENT', 'production'),
        "services": {
            "database": "unknown",
            "redis": "unknown",
            "llm_provider": settings.LLM_PROVIDER
        }
    }

    # Check Database
    try:
        from sqlalchemy import text
        result = db.execute(text("SELECT 1"))
        result.fetchone()
        health_status["services"]["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = "disconnected"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        health_status["services"]["redis"] = "connected"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        health_status["services"]["redis"] = "disconnected"
        # Redis failure is not critical, mark as degraded but operational
        if health_status["status"] == "healthy":
            health_status["status"] = "degraded"

    # If database is down, mark as unhealthy (critical)
    if health_status["services"]["database"] == "disconnected":
        health_status["status"] = "unhealthy"

    return health_status


@router.get("/health/simple")
def simple_health_check():
    """
    Simple health check that just returns OK.
    Useful for basic uptime monitoring without dependencies.
    """
    return {"status": "ok"}


@router.get("/health/llm")
def llm_health_check():
    """Check if LLM service is properly configured"""
    
    try:
        # Check if API key is set
        if not settings.LLM_API_KEY or settings.LLM_API_KEY == "":
            return {
                "status": "error",
                "provider": settings.LLM_PROVIDER,
                "model": settings.LLM_MODEL,
                "error": "LLM_API_KEY environment variable is not set"
            }
        
        # Check if API key looks valid (not a placeholder)
        if "placeholder" in settings.LLM_API_KEY.lower() or "your_" in settings.LLM_API_KEY.lower():
            return {
                "status": "error",
                "provider": settings.LLM_PROVIDER,
                "model": settings.LLM_MODEL,
                "error": "LLM_API_KEY appears to be a placeholder value"
            }
        
        # Try to initialize the LLM
        try:
            from app.core.llm_provider import LLMProvider
            llm = LLMProvider.get_llm(temperature=0.0)
            return {
                "status": "ok",
                "provider": settings.LLM_PROVIDER,
                "model": settings.LLM_MODEL,
                "api_key_length": len(settings.LLM_API_KEY),
                "api_key_prefix": settings.LLM_API_KEY[:10] + "..." if len(settings.LLM_API_KEY) > 10 else "too_short"
            }
        except Exception as e:
            logger.error(f"LLM initialization failed: {e}", exc_info=True)
            return {
                "status": "error",
                "provider": settings.LLM_PROVIDER,
                "model": settings.LLM_MODEL,
                "error": f"Failed to initialize LLM: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"LLM health check failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }
