"""
Rate limiting for task creation. Uses Redis to track per-user request counts
with sliding windows. Falls back to no rate limiting if Redis is not available.
"""

import time
import logging
from fastapi import HTTPException, Request
from .config import settings

# Optional redis import
try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)

# Lazy initialization - only create when needed
_redis_client = None


def _get_redis():
    """Lazy Redis initialization."""
    global _redis_client
    if redis is None:
        return None
    if _redis_client is None and settings.redis_url:
        try:
            _redis_client = redis.Redis.from_url(
                settings.redis_url, decode_responses=True
            )
            # Test connection
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Rate limiting disabled.")
            _redis_client = False  # Mark as failed to avoid retrying
    return _redis_client if _redis_client is not False else None


def check_rate_limit(user_id: str) -> None:
    """
    Check if user has exceeded rate limits. Raises HTTPException(429) if so.
    Uses two sliding windows: per-minute and per-hour.
    Silently passes if Redis is not available.
    """
    redis_client = _get_redis()
    if not redis_client:
        # Rate limiting disabled if Redis not available
        return

    now = time.time()

    # Check per-minute limit
    minute_key = f"rate_limit:{user_id}:minute"
    minute_count = redis_client.zcard(minute_key)
    if minute_count >= settings.rate_limit_tasks_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {settings.rate_limit_tasks_per_minute} tasks per minute",
        )

    # Check per-hour limit
    hour_key = f"rate_limit:{user_id}:hour"
    hour_count = redis_client.zcard(hour_key)
    if hour_count >= settings.rate_limit_tasks_per_hour:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {settings.rate_limit_tasks_per_hour} tasks per hour",
        )

    # Record this request in both windows
    redis_client.zadd(minute_key, {str(now): now})
    redis_client.zadd(hour_key, {str(now): now})

    # Clean up old entries (older than 1 minute / 1 hour)
    redis_client.zremrangebyscore(minute_key, 0, now - 60)
    redis_client.zremrangebyscore(hour_key, 0, now - 3600)

    # Set expiry on keys so they auto-clean
    redis_client.expire(minute_key, 120)
    redis_client.expire(hour_key, 3700)
