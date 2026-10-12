"""Health-check router."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    """Returns `{"status": "ok"}` when the API is running.

    Use this endpoint to verify the backend is reachable before the
    frontend attempts other requests.
    """
    return HealthResponse(status="ok", version="0.1.0")
