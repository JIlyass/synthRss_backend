"""
app/schemas/auth.py — Pydantic v2 schemas for Sign Up, Login and token responses.
"""
from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr, Field, field_validator, field_serializer


# ─── Sign Up ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """
    Payload from the React Sign Up form.
    Fields must match exactly what the frontend sends.
    """
    full_name: str = Field(
        ..., min_length=2, max_length=255,
        examples=["Jane Doe"]
    )
    email: EmailStr = Field(
        ..., examples=["jane@example.com"]
    )
    password: str = Field(
        ..., min_length=8, max_length=72,
        examples=["securepass123"]
    )
    interests: List[str] = Field(
        ..., min_length=1,
        examples=[["Technology", "AI", "Medicine"]]
    )

    @field_validator("full_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Full name must not be blank.")
        return v.strip()

    @field_validator("interests")
    @classmethod
    def interests_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Select at least one area of interest.")
        cleaned: List[str] = []
        seen: set[str] = set()
        for item in v:
            s = item.strip()
            if not s:
                raise ValueError("Interest values must not be empty strings.")
            if s not in seen:
                seen.add(s)
                cleaned.append(s)
        return cleaned


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Payload from the React Login form."""
    email:    EmailStr = Field(..., examples=["jane@example.com"])
    password: str      = Field(..., min_length=1, examples=["securepass123"])


# ─── Responses ────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """Generic success/info response."""
    message: str


class TokenResponse(BaseModel):
    """Successful login response — contains the JWT bearer token."""
    access_token: str
    token_type:   str = "bearer"


class UserPublicResponse(BaseModel):
    """Safe user representation (never exposes hashed_password)."""
    id:         int
    full_name:  str
    email:      str
    interests:  List[str]
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("interests")
    def serialize_interests(self, value: List) -> List[str]:
        """Convert Interest ORM objects to their names."""
        return [interest.name if hasattr(interest, "name") else str(interest) for interest in value]
