from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://webops:webops@localhost:5432/webops"
    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "webops"
    minio_root_password: str = "webops123"
    minio_bucket: str = "evidence"
    minio_secure: bool = False

    gemini_api_key: str = ""
    gemini_model_lite: str = "gemini-2.5-flash-lite"
    gemini_model: str = "gemini-2.5-flash"
    ollama_base_url: str = ""
    ollama_model: str = ""
    llm_provider: str = ""

    mock_site_base_url: str = "http://127.0.0.1:5050"
    log_dir: str = "logs"

    # raw MinIO artifacts (screenshots/HTML/traces) older than this are purged
    # by the scheduler's retention job; the Evidence row and its metadata are
    # never deleted, only the object key and bytes (engineering guidelines, section 10).
    retention_days_raw_artifacts: int = 90

    jwt_secret: str = "dev-only-change-in-production"
    jwt_expires_minutes: int = 480

    # comma-separated explicit origins the frontend is served from - never a
    # wildcard, since the API issues auth cookies/bearer tokens (engineering
    # guidelines, section 8: never widen trust beyond what a request actually needs).
    # Defaults cover the local Docker Compose frontend and Vite dev server.
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
