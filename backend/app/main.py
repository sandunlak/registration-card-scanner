"""
Registration Card Scanner — FastAPI application entry point.

All heavyweight model loading (PaddleOCR, etc.) happens in individual
services, not here.  This file wires together routers, middleware, and
startup/shutdown lifecycle hooks only.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.routers import health

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated @app.on_event)
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
# Future routers (added in later milestones):
# app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
# app.include_router(cards.router,    prefix="/api/v1/cards",    tags=["cards"])
# app.include_router(templates.router,prefix="/api/v1/templates",tags=["templates"])
# app.include_router(export.router,   prefix="/api/v1/export",   tags=["export"])
