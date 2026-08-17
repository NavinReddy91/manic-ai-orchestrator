"""
Manic AI Orchestrator — Configuration
All fields have sensible defaults. Only LLM_API_KEY is needed to get started.
"""

import logging
from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # --- LLM provider ---
    # Options: anthropic, openai, groq, gemini, openrouter, local
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"
    llm_base_url: str = ""  # for local: http://localhost:11434/v1

    # --- Infrastructure ---
    database_url: str = "sqlite:///./manic_ai.db"  # SQLite for local/Render free
    redis_url: str = ""  # Optional: only needed for Celery worker deployment

    # --- Auth ---
    # Simple API key auth. If empty, auth is disabled (for testing).
    api_key: str = ""

    # --- GitHub (optional — only needed for coding tasks) ---
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = ""

    # --- Security ---
    token_encryption_key: str = ""  # auto-generated if empty

    # --- Cost control ---
    max_llm_calls_per_task: int = 0

    # --- Rate limiting ---
    rate_limit_tasks_per_minute: int = 10
    rate_limit_tasks_per_hour: int = 100

    # --- Task timeout ---
    task_timeout_minutes: int = 30

    # --- Admin ---
    admin_secret: str = ""
    admin_allowed_ips: str = ""

    # --- File size limits ---
    max_file_size_bytes: int = 1_000_000
    max_files_per_commit: int = 50

    # --- CORS ---
    allowed_origins: str = "*"  # comma-separated origins, or * for all

    class Config:
        env_file = ".env"
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.llm_api_key:
            import os
            self.llm_api_key = (
                os.getenv("LLM_API_KEY")
                or os.getenv("GROQ_API_KEY")
                or os.getenv("OPENAI_API_KEY")
                or os.getenv("GEMINI_API_KEY")
                or os.getenv("ANTHROPIC_API_KEY")
                or os.getenv("OPENROUTER_API_KEY")
                or ""
            )
        if not self.token_encryption_key:
            self.token_encryption_key = Fernet.generate_key().decode()
        self._validate()

    def _validate(self):
        if not self.llm_api_key:
            logger.warning(
                "LLM_API_KEY not set — LLM calls will fail until configured."
            )
        if not self.api_key:
            logger.warning(
                "API_KEY not set — authentication is disabled (open access)."
            )
        if self.llm_provider == "local" and not self.llm_base_url:
            logger.warning("LLM_PROVIDER=local but LLM_BASE_URL not set.")


settings = Settings()
