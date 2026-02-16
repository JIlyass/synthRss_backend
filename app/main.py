"""
app/main.py — FastAPI application factory

Registers:
  - CORS middleware (for React frontend on :3000)
  - /api/auth router (register + login)
  - /health endpoint
  - Auto-creates DB tables on startup (dev convenience)
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, Base
from fastapi.responses import PlainTextResponse

# ── Logging ───────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Import all models so SQLAlchemy registers them with Base.metadata
import app.models.interest  # noqa: F401
import app.models.user      # noqa: F401

from app.routes.auth import router as auth_router


# ── Lifespan: startup / shutdown ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — create tables if they don't exist
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables ready.")
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        raise
    yield
    logger.info("👋 BrieflyAI API shutting down.")


# ── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="Authentication API for BrieflyAI — Sign Up & Login",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS (must be before routers) ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.cors_origins,      # e.g. ["http://localhost:3000"]
    allow_origins=[*],      # e.g. ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Authorization", "Content-Type"],  # allow frontend to read auth header
    max_age=3600,  # preflight cache
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"], summary="Liveness probe")
def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": settings.APP_TITLE, "version": settings.APP_VERSION})


@app.get("/kaithhealthcheck", include_in_schema=False)
def kaith_healthcheck():
    return PlainTextResponse("ok")

@app.get("/", include_in_schema=False)
def root() -> JSONResponse:
    return JSONResponse({"message": f"Welcome to {settings.APP_TITLE}", "docs": "/docs"})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
