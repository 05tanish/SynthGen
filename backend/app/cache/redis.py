import redis
from app.core.config import settings
from app.core.logging import logger

_redis_client = None


def get_redis_client() -> redis.Redis:
    """
    Lazily initialize and return the Redis client.
    Supports both Upstash HTTP REST API and standard Redis protocol.
    Defers connection until first use so a Redis unavailability
    at startup does NOT crash the entire application.
    """
    global _redis_client
    if _redis_client is None:
        try:
            if settings.UPSTASH_REDIS_URL.startswith("https://"):
                # Upstash HTTP REST API - use upstash-redis package
                try:
                    from upstash_redis import Redis as UpstashRedis
                    _redis_client = UpstashRedis(
                        url=settings.UPSTASH_REDIS_URL,
                        token=settings.UPSTASH_REDIS_TOKEN if settings.UPSTASH_REDIS_TOKEN else None
                    )
                    logger.info("Redis client initialized with Upstash HTTP REST API")
                except ImportError:
                    logger.error("upstash-redis package not installed. Install with: pip install upstash-redis")
                    raise
            elif settings.UPSTASH_REDIS_URL.startswith(("redis://", "rediss://")):
                # Standard Redis protocol
                _redis_client = redis.Redis.from_url(
                    settings.UPSTASH_REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                logger.info("Redis client initialized with standard Redis protocol")
            else:
                # Fallback to localhost
                _redis_client = redis.Redis(
                    host="localhost", port=6379, decode_responses=True, socket_connect_timeout=5
                )
                logger.info("Redis client initialized with localhost fallback")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise
    return _redis_client
