"""
app/models/user.py

`users` table with a many-to-many relationship to `interests`.
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.interest import Interest, user_interests


class User(Base):
    __tablename__ = "users"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)

    # ── Identity ──────────────────────────────────────────────────────────────
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email:     Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)

    # ── Security ──────────────────────────────────────────────────────────────
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Status ────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(tz=timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    interests: Mapped[list[Interest]] = relationship(
        "Interest",
        secondary=user_interests,
        lazy="selectin",   # auto-loaded in a single extra query — no N+1
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
