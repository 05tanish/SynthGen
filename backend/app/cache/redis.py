import redis
from app.core.config import settings
from app.core.logging import logger

_redis_client = None


def get_redis_client() -> redis.Redis:
    """
    Lazily initialize and return the Redis client.
    Defers connection until first use so a Redis unavailability
    at startup does NOT crash the entire application.
    """
    global _redis_client
    if _redis_client is None:
        try:
            if settings.UPSTASH_REDIS_URL.startswith(("https://", "rediss://")):
                # Upstash HTTP REST client via redis-py with REST URL
                # upstash-redis requires the REST URL, so we use it with password auth
                _redis_client = redis.Redis.from_url(
                    settings.UPSTASH_REDIS_URL,
                    password=settings.UPSTASH_REDIS_TOKEN if settings.UPSTASH_REDIS_TOKEN else None,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
            elif settings.UPSTASH_REDIS_URL.startswith("redis://"):
                _redis_client = redis.Redis.from_url(
                    settings.UPSTASH_REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
            else:
                _redis_client = redis.Redis(
                    host="localhost", port=6379, decode_responses=True, socket_connect_timeout=5
                )
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise
    return _redis_client
