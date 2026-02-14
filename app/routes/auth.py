"""
app/routes/auth.py

Authentication router — two endpoints:
  POST /api/auth/register   → create account
  POST /api/auth/login      → authenticate + return JWT
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from app.database import get_db
from app.models.user import User
from app.models.interest import Interest
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    MessageResponse,
)
from app.core.security import hash_password, verify_password, create_access_token

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_or_create_interest(db: Session, name: str) -> Interest:
    """
    Retrieve an existing Interest by name, or insert it if it doesn't exist.
    Uses a simple select-then-insert pattern safe within a single request.
    
    Args:
        db: Database session
        name: Interest name (e.g., "Technology", "AI")
    
    Returns:
        Interest object (either existing or newly created)
    
    Raises:
        IntegrityError: If concurrent insert of same interest occurs
    """
    try:
        interest = db.query(Interest).filter(Interest.name == name).first()
        if not interest:
            interest = Interest(name=name)
            db.add(interest)
            db.flush()   # assign id without committing the outer transaction
        return interest
    except OperationalError as e:
        logger.error(f"Database error in interest lookup: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_ERROR", "message": "Database connection failed"},
        ) from e


# ── POST /api/auth/register ───────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
    responses={
        201: {"description": "Account created successfully"},
        409: {"description": "Email already registered"},
        422: {"description": "Validation error"},
        503: {"description": "Database unavailable"},
    },
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> MessageResponse:
    """
    Register a new BrieflyAI user.

    - Validates all fields (Pydantic)
    - Checks email uniqueness
    - Hashes the password with bcrypt
    - Resolves/creates Interest records
    - Persists the User with its interests (many-to-many)
    """
    # ── 1. Duplicate email check ──────────────────────────────────────────────
    try:
        existing = db.query(User).filter(User.email == payload.email.lower()).first()
        if existing:
            logger.warning(f"Registration attempt with existing email: {payload.email[:5]}...")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code":    "EMAIL_ALREADY_REGISTERED",
                    "message": "An account with this email address already exists.",
                },
            )
    except OperationalError as e:
        logger.error(f"Database error during email check: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_ERROR", "message": "Database connection failed"},
        ) from e

    # ── 2. Resolve interests (get or create each one) ─────────────────────────
    try:
        interest_objs = [_get_or_create_interest(db, name) for name in payload.interests]
    except HTTPException:
        raise  # propagate database errors

    # ── 3. Build user ─────────────────────────────────────────────────────────
    try:
        hashed_pwd = hash_password(payload.password)
    except ValueError as e:
        logger.error(f"Password hashing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "HASHING_ERROR", "message": "Internal server error"},
        ) from e

    new_user = User(
        full_name=payload.full_name.strip(),
        email=payload.email.lower(),
        hashed_password=hashed_pwd,
        is_active=True,
        interests=interest_objs,
    )

    # ── 4. Persist ────────────────────────────────────────────────────────────
    try:
        db.add(new_user)
        db.commit()
        logger.info(f"User registered: {payload.email[:5]}...")
    except IntegrityError as e:
        # Race-condition guard: concurrent request with the same email
        db.rollback()
        logger.warning(f"Race condition: Email already registered: {payload.email[:5]}...")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code":    "EMAIL_ALREADY_REGISTERED",
                "message": "An account with this email address already exists.",
            },
        ) from e
    except OperationalError as e:
        db.rollback()
        logger.error(f"Database error during user creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_ERROR", "message": "Database connection failed"},
        ) from e

    return MessageResponse(message="Account created successfully")


# ── POST /api/auth/login ──────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive a JWT access token",
    responses={
        200: {"description": "JWT bearer token returned"},
        401: {"description": "Invalid credentials"},
        403: {"description": "Account disabled"},
        503: {"description": "Database unavailable"},
    },
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Authenticate with email + password.

    - Looks up the user by email
    - Verifies password with bcrypt (constant-time)
    - Returns a signed JWT on success

    The same 401 is returned whether the email is unknown or the
    password is wrong — this prevents user enumeration attacks.
    """
    # ── 1. Look up user ───────────────────────────────────────────────────────
    try:
        user = db.query(User).filter(User.email == payload.email.lower()).first()
    except OperationalError as e:
        logger.error(f"Database error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DATABASE_ERROR", "message": "Database connection failed"},
        ) from e

    # ── 2. Verify (always run verify to prevent timing attacks) ───────────────
    # Always verify even if user doesn't exist to prevent timing attacks
    password_valid = verify_password(payload.password, user.hashed_password if user else "")
    
    if not user or not password_valid:
        logger.warning(f"Failed login attempt for: {payload.email[:5]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code":    "INVALID_CREDENTIALS",
                "message": "Incorrect email or password.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── 3. Active check ───────────────────────────────────────────────────────
    if not user.is_active:
        logger.warning(f"Login attempt with disabled account: {payload.email[:5]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code":    "ACCOUNT_DISABLED",
                "message": "Your account has been deactivated. Please contact support.",
            },
        )

    # ── 4. Issue token ────────────────────────────────────────────────────────
    try:
        token = create_access_token(subject=user.email)
        logger.info(f"Successful login: {user.email[:5]}...")
        return TokenResponse(access_token=token, token_type="bearer")
    except Exception as e:
        logger.error(f"Token generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TOKEN_ERROR", "message": "Failed to generate token"},
        ) from e
