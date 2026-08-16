from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- DigiMarkIn hub (JWT verification) ---
    digimarkin_jwks_url: str
    digimarkin_jwt_issuer: str
    digimarkin_jwt_audience: str

    # --- GitHub OAuth ---
    github_client_id: str
    github_client_secret: str
    github_redirect_uri: str

    # --- LLM provider ---
    # Options: anthropic, openai, groq, gemini, openrouter, local
    llm_provider: str = "groq"
    llm_api_key: str
    llm_model: str = "llama-3.3-70b-versatile"  # default for Groq
    llm_base_url: str = (
        ""  # required for local provider (e.g., http://localhost:11434/v1)
    )

    # --- Infrastructure ---
    database_url: str
    redis_url: str
    token_encryption_key: str

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


settings = Settings()
