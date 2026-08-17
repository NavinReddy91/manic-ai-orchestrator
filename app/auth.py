"""
Manic AI — Simple API Key Authentication
If API_KEY is not set in .env, authentication is disabled (for testing).
"""

import logging
from fastapi import Header, HTTPException, Depends
from .config import settings

logger = logging.getLogger(__name__)


async def get_current_user(x_api_key: str = Header(None, alias="X-API-Key")) -> dict:
    """
    FastAPI dependency for authentication.

    If API_KEY is not configured, returns a default test user (open access).
    If API_KEY is set, requires X-API-Key header to match.
    """
    # Development mode: no auth required
    if not settings.api_key:
        return {
            "sub": "test-user",
            "role": "admin",
            "name": "Test User",
        }

    # Production mode: validate API key
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header.",
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )

    # In a real system, you'd look up the user from the API key
    # For now, return a generic user
    return {
        "sub": "api-user",
        "role": "user",
        "name": "API User",
    }
