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
    # Options: anthropic, openai, groq, gemini, openrouter
    llm_provider: str = "groq"
    llm_api_key: str
    llm_model: str = "llama-3.3-70b-versatile"  # default for Groq

    # --- Infrastructure ---
    database_url: str
    redis_url: str
    token_encryption_key: str

    # --- Cost control ---
    max_llm_calls_per_task: int = 0  # 0 = unlimited

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
