from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    digimarkin_jwks_url: str
    digimarkin_jwt_issuer: str
    digimarkin_jwt_audience: str

    github_client_id: str
    github_client_secret: str
    github_redirect_uri: str

    anthropic_api_key: str

    database_url: str
    redis_url: str

    token_encryption_key: str

    # Cost control: max Claude API calls per task (0 = unlimited)
    max_llm_calls_per_task: int = 0

    class Config:
        env_file = ".env"
        extra = "ignore"  # docker-compose.yml also passes POSTGRES_PASSWORD, which Settings doesn't need directly


settings = Settings()
