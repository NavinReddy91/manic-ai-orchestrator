"""
JWT authentication against DigiMarkIn Core (the hub).

If DIGIMARKIN_JWKS_URL is not set, authentication is disabled for testing.
In production, this verifies JWTs using the hub's public keys from JWKS.
"""

import time
import logging
from fastapi import Header, HTTPException, Depends
from jose import jwt, JWTError
import httpx

from .config import settings

logger = logging.getLogger(__name__)

_jwks_cache = {"keys": None, "fetched_at": 0}
_JWKS_TTL_SECONDS = 600


async def _get_jwks() -> dict:
    """Fetch and cache JWKS from DigiMarkIn."""
    now = time.time()
    if _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"] < _JWKS_TTL_SECONDS):
        return _jwks_cache["keys"]

    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(settings.digimarkin_jwks_url)
        resp.raise_for_status()
        jwks = resp.json()

    _jwks_cache["keys"] = jwks
    _jwks_cache["fetched_at"] = now
    return jwks


async def get_current_user(authorization: str = Header(None)) -> dict:
    """
    FastAPI dependency. Returns decoded JWT claims with `sub` (user ID).

    If DIGIMARKIN_JWKS_URL is not set, returns a test user for development.
    """
    # Development mode: if JWKS not configured, return test user
    if not settings.digimarkin_jwks_url:
        logger.debug(
            "JWT auth disabled (DIGIMARKIN_JWKS_URL not set) — using test user"
        )
        return {
            "sub": "test-user-id",
            "email": "test@example.com",
            "name": "Test User",
        }

    # Production mode: verify JWT
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1]

    try:
        jwks = await _get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        key = next(
            (k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None
        )
        if key is None:
            raise HTTPException(status_code=401, detail="Unknown signing key (kid)")

        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.digimarkin_jwt_audience,
            issuer=settings.digimarkin_jwt_issuer,
        )
        if "sub" not in claims:
            raise HTTPException(status_code=401, detail="Token missing subject")
        return claims

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
