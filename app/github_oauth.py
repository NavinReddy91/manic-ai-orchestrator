"""
Sonic AI — GitHub OAuth Integration (Optional)
Only active if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET are configured.
"""

import json
import secrets
import httpx
import logging
import redis
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .config import settings
from .auth import get_current_user
from .models import ConnectedAccount, Organization
from .db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/github", tags=["github"])

# Only initialize if GitHub is configured
_fernet = Fernet(settings.token_encryption_key.encode())
_redis_client = (
    redis.Redis.from_url(settings.redis_url, decode_responses=True)
    if settings.redis_url
    else None
)
_OAUTH_STATE_TTL = 600


def _check_github_config():
    """Check if GitHub OAuth is configured."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(
            status_code=501,
            detail="GitHub OAuth not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.",
        )
    if not _redis_client:
        raise HTTPException(
            status_code=503,
            detail="Redis not configured. GitHub OAuth requires Redis for state management.",
        )


@router.get("/connect")
async def connect(
    organization_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start GitHub OAuth flow."""
    _check_github_config()

    org = (
        db.query(Organization)
        .filter_by(id=organization_id, user_id=user["sub"])
        .first()
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    state = secrets.token_urlsafe(24)
    _redis_client.setex(
        f"oauth_state:{state}",
        _OAUTH_STATE_TTL,
        json.dumps({"user_id": user["sub"], "organization_id": organization_id}),
    )

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "repo read:user",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{query}")


@router.get("/callback")
async def callback(code: str, state: str, db: Session = Depends(get_db)):
    """Handle GitHub OAuth callback."""
    _check_github_config()

    raw = _redis_client.get(f"oauth_state:{state}")
    if not raw:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    _redis_client.delete(f"oauth_state:{state}")

    pending = json.loads(raw)
    user_id = pending["user_id"]
    organization_id = pending["organization_id"]

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=400, detail=f"GitHub token exchange failed: {token_data}"
            )

        who_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        github_login = who_resp.json().get("login")

    encrypted = _fernet.encrypt(access_token.encode()).decode()

    existing = (
        db.query(ConnectedAccount)
        .filter_by(user_id=user_id, organization_id=organization_id, provider="github")
        .first()
    )
    if existing:
        existing.encrypted_token = encrypted
        existing.provider_account_login = github_login
    else:
        db.add(
            ConnectedAccount(
                user_id=user_id,
                organization_id=organization_id,
                provider="github",
                provider_account_login=github_login,
                encrypted_token=encrypted,
            )
        )
    db.commit()

    # Redirect to a success page (configurable or default)
    return RedirectResponse(f"/?github=connected&organization_id={organization_id}")


def get_github_token(db: Session, user_id: str, organization_id: str) -> str | None:
    """
    Get GitHub token for an organization.
    Returns None if not connected or GitHub OAuth not configured.
    """
    if not settings.github_client_id:
        return None

    row = (
        db.query(ConnectedAccount)
        .filter_by(user_id=user_id, organization_id=organization_id, provider="github")
        .first()
    )
    if not row:
        return None
    return _fernet.decrypt(row.encrypted_token.encode()).decode()
