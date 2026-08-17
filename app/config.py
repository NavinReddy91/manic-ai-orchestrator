"""
Configuration settings. All fields have defaults so the app can start even
without full configuration — you can add variables incrementally.

For Render deployment:
- DATABASE_URL: Set in Render's Environment tab (from managed Postgres)
- REDIS_URL: Set in Render's Environment tab (from managed Redis)
- LLM_API_KEY: Set in Render's Environment tab
- Other fields: Add as needed

For Docker Compose deployment:
- All values come from .env file
"""

import logging
from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # --- DigiMarkIn hub (JWT verification) ---
    # These can be empty for testing — auth will be disabled if not set
    digimarkin_jwks_url: str = ""
    digimarkin_jwt_issuer: str = ""
    digimarkin_jwt_audience: str = ""

    # --- GitHub OAuth ---
    # These can be empty — GitHub integration will be disabled if not set
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = ""

    # --- LLM provider ---
    # Options: anthropic, openai, groq, gemini, openrouter, local
    llm_provider: str = "groq"
    llm_api_key: str = ""  # Required for actual LLM calls
    llm_model: str = "llama-3.3-70b-versatile"  # default for Groq
    llm_base_url: str = (
        ""  # required for local provider (e.g., http://localhost:11434/v1)
    )

    # --- Infrastructure ---
    # For Render: set DATABASE_URL and REDIS_URL in Environment tab
    # For Docker: these come from .env with service names (postgres, redis)
    database_url: str = "postgresql://nexus:nexus@localhost:5432/nexus_orchestrator"
    redis_url: str = "redis://localhost:6379/0"

    # Token encryption key — auto-generate if not set (for testing only)
    # In production, set this explicitly and keep it stable across restarts
    token_encryption_key: str = ""

    # --- Cost control ---
    max_llm_calls_per_task: int = 0  # 0 = unlimited

    # --- Rate limiting ---
    rate_limit_tasks_per_minute: int = 10  # max tasks per user per minute
    rate_limit_tasks_per_hour: int = 100  # max tasks per user per hour

    # --- Task timeout ---
    task_timeout_minutes: int = 30  # auto-fail tasks stuck in "running" for this long

    # --- Admin/debug ---
    admin_secret: str = ""  # if set, enables /admin endpoints with this Bearer token
    admin_allowed_ips: str = (
        ""  # comma-separated IPs allowed to access /admin (empty = all)
    )

    # --- File size limits ---
    max_file_size_bytes: int = 1_000_000  # 1MB max per file written by coding agents
    max_files_per_commit: int = 50  # max files in a single commit

    class Config:
        env_file = ".env"
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Auto-generate token encryption key if not set (for testing)
        if not self.token_encryption_key:
            logger.warning(
                "TOKEN_ENCRYPTION_KEY not set — auto-generating a temporary key. "
                "This means encrypted tokens (GitHub OAuth) won't survive restarts. "
                "Set TOKEN_ENCRYPTION_KEY in production!"
            )
            self.token_encryption_key = Fernet.generate_key().decode()

        # Validate critical settings
        self._validate_settings()

    def _validate_settings(self):
        """Log warnings for missing optional but recommended settings."""
        if not self.digimarkin_jwks_url:
            logger.warning(
                "DIGIMARKIN_JWKS_URL not set — JWT authentication will fail. "
                "Set this in production or use a test JWT bypass."
            )

        if not self.llm_api_key:
            logger.warning(
                "LLM_API_KEY not set — LLM calls will fail. "
                "Set this to use any AI provider."
            )

        if self.llm_provider == "local" and not self.llm_base_url:
            logger.warning(
                "LLM_PROVIDER=local but LLM_BASE_URL not set — "
                "set LLM_BASE_URL (e.g., http://localhost:11434/v1)"
            )


settings = Settings()
