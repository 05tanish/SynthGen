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
