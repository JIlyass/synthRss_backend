"""
app/config.py — Centralised application settings loaded from .env
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:admin@localhost:5432/brieflyai"

    # JWT (MUST be set in .env — minimum 32 characters)
    SECRET_KEY: str = "change-me-to-a-32-character-random-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS  (comma-separated string → list via property)
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # App info
    APP_TITLE: str = "BrieflyAI API"
    APP_VERSION: str = "1.0.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated CORS origins, handling edge cases."""
        if not self.ALLOWED_ORIGINS or not isinstance(self.ALLOWED_ORIGINS, str):
            return []
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        return origins if origins else []


settings = Settings()
