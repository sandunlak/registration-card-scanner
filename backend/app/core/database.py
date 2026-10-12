"""Async SQLite database engine and session factory."""

from __future__ import annotations

from pathlib import Path
from typing import AsyncGenerator
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
# Import models so SQLModel registers them with SQLModel.metadata
import app.models  # noqa: F401


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    """Ensure the directory containing the SQLite database file exists."""
    if "sqlite" in database_url:
        path_str = database_url.split(":///")[-1]
        if path_str and not path_str.startswith(":memory:"):
            db_path = Path(path_str).resolve()
            db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(settings.database_url)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def create_db_and_tables() -> None:
    """Create all SQLModel-registered tables if they do not exist.

    Existing tables and user data are never dropped or overwritten.
    """
    _ensure_sqlite_parent_dir(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session
