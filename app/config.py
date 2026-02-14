"""
app/config.py — Centralised application settings loaded from environment variables
"""
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    # La valeur par défaut est utilisée uniquement si DATABASE_URL n'est pas trouvée dans Railway
    DATABASE_URL: str = "postgresql+psycopg2://postgres:admin@localhost:5432/brieflyai"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_postgres_protocol(cls, v: str) -> str:
        """Remplace postgres:// par postgresql:// pour SQLAlchemy 2.0+"""
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg2://", 1)
        # S'assurer que psycopg2 est bien spécifié comme driver
        if isinstance(v, str) and "postgresql://" in v and "+psycopg2" not in v:
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    # ── JWT (MUST be set in Railway variables for production) ─────────────────
    SECRET_KEY: str = "change-me-to-a-32-character-random-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Ajoutez l'URL de votre Vercel dans les variables Railway sous le nom ALLOWED_ORIGINS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── App info ──────────────────────────────────────────────────────────────
    APP_TITLE: str = "BrieflyAI API"
    APP_VERSION: str = "1.0.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore" # Ignore les variables supplémentaires envoyées par Railway
    )

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated CORS origins, handling edge cases."""
        if not self.ALLOWED_ORIGINS or not isinstance(self.ALLOWED_ORIGINS, str):
            return []
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        return origins if origins else []


settings = Settings()
