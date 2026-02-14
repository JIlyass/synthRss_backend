"""
app/core/security.py — Password hashing (bcrypt) and JWT utilities.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

logger = logging.getLogger(__name__)

# ── bcrypt context ────────────────────────────────────────────────────────────
# rounds=12 provides strong security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# bcrypt limitation
MAX_BCRYPT_LENGTH = 72


def hash_password(plain: str) -> str:
    """Return the bcrypt hash of a plain-text password.

    Args:
        plain: Plain-text password (validated to be 8-72 chars by Pydantic)

    Returns:
        bcrypt hashed password (safe for storage)

    Raises:
        ValueError: If hashing fails
    """
    try:
        truncated = plain[:MAX_BCRYPT_LENGTH]
        return pwd_context.hash(truncated)
    except Exception as e:
        logger.error(f"Password hashing failed: {type(e).__name__}")
        raise ValueError("HASHING_ERROR") from e


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt comparison — returns True if passwords match.

    Args:
        plain: Plain-text password from user
        hashed: Hashed password from database

    Returns:
        True if passwords match, False otherwise
    """
    try:
        truncated = plain[:MAX_BCRYPT_LENGTH]
        return pwd_context.verify(truncated, hashed)
    except Exception as e:
        logger.warning(f"Password verification failed: {type(e).__name__}")
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Sign a JWT token whose subject is the user's email."""
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Decode + validate a JWT. Returns the subject (email) or None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError as e:
        logger.debug(f"JWT decode error: {type(e).__name__}")
        return None
