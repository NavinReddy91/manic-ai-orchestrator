"""
Rate limiting for task creation. Uses Redis to track per-user request counts
with sliding windows.
"""

import time
import redis
from fastapi import HTTPException, Request
from .config import settings

_redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def check_rate_limit(user_id: str) -> None:
    """
    Check if user has exceeded rate limits. Raises HTTPException(429) if so.
    Uses two sliding windows: per-minute and per-hour.
    """
    now = time.time()

    # Check per-minute limit
    minute_key = f"rate_limit:{user_id}:minute"
    minute_count = _redis_client.zcard(minute_key)
    if minute_count >= settings.rate_limit_tasks_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {settings.rate_limit_tasks_per_minute} tasks per minute",
        )

    # Check per-hour limit
    hour_key = f"rate_limit:{user_id}:hour"
    hour_count = _redis_client.zcard(hour_key)
    if hour_count >= settings.rate_limit_tasks_per_hour:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {settings.rate_limit_tasks_per_hour} tasks per hour",
        )

    # Record this request in both windows
    _redis_client.zadd(minute_key, {str(now): now})
    _redis_client.zadd(hour_key, {str(now): now})

    # Clean up old entries (older than 1 minute / 1 hour)
    _redis_client.zremrangebyscore(minute_key, 0, now - 60)
    _redis_client.zremrangebyscore(hour_key, 0, now - 3600)

    # Set expiry on keys so they auto-clean
    _redis_client.expire(minute_key, 120)
    _redis_client.expire(hour_key, 3700)
