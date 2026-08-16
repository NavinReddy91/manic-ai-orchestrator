"""
Verifies JWTs issued by DigiMarkIn Core (the hub). This service never issues
its own tokens and holds no shared secret — it only trusts the hub's public
signing keys, fetched from its JWKS endpoint and cached briefly.
"""
import time
from fastapi import Header, HTTPException
from jose import jwt, JWTError
import httpx

from .config import settings

_jwks_cache = {"keys": None, "fetched_at": 0}
_JWKS_TTL_SECONDS = 600


async def _get_jwks() -> dict:
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
    FastAPI dependency. Use as: user = Depends(get_current_user)
    Returns the decoded JWT claims (must include `sub` = DigiMarkIn user id).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1]

    try:
        jwks = await _get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        key = next((k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None)
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
