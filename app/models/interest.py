"""
app/models/interest.py

`interests` table — catalogue of available research/interest topics.
`user_interests` — many-to-many association table between users and interests.
"""
from sqlalchemy import BigInteger, String, Table, ForeignKey, Column
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ── Association table (no ORM class needed — pure join table) ─────────────────
user_interests = Table(
    "user_interests",
    Base.metadata,
    Column("user_id",     ForeignKey("users.id",     ondelete="CASCADE"), primary_key=True),
    Column("interest_id", ForeignKey("interests.id", ondelete="CASCADE"), primary_key=True),
)


class Interest(Base):
    """
    Normalised catalogue of interest topics.
    Records are inserted on first use (upsert-style via get_or_create).
    """
    __tablename__ = "interests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Interest id={self.id} name={self.name!r}>"
