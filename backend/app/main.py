"""Registration Card Scanner — FastAPI application entry point.

Wires together routers, middleware, lifecycle hooks, and error handlers.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.exceptions import AppError
from app.routers import fields, health, projects, records

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown logic."""
    logging.basicConfig(level=settings.log_level)
    logger.info("Starting Registration Card Scanner API v%s", app.version)
    await create_db_and_tables()
    logger.info("Database ready")
    yield
    logger.info("Shutting down Registration Card Scanner API")


app = FastAPI(
    title="Registration Card Scanner API",
    description=(
        "Locally-runnable AI service that digitises handwritten and printed "
        "registration cards for migration consultancy events."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Consistent JSON error response for all domain exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)

# Project management & configurable field endpoints
app.include_router(projects.router, prefix="/api/projects")
app.include_router(fields.router, prefix="/api/projects")
app.include_router(records.router, prefix="/api/projects")

# Alias /api/v1/projects for backwards compatibility
app.include_router(projects.router, prefix="/api/v1/projects")
app.include_router(fields.router, prefix="/api/v1/projects")
app.include_router(records.router, prefix="/api/v1/projects")
