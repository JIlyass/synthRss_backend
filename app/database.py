"""
app/database.py — SQLAlchemy engine, session factory, declarative base.
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from app.config import settings


# ── Declarative base (all models inherit from this) ──────────────────────────
class Base(DeclarativeBase):
    pass


# ── Engine ───────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # detect stale connections
    pool_recycle=3600,
    echo=False,
)

# ── Session factory ──────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
