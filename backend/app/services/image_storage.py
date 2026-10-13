"""Private local storage helpers for project and record scoped image files."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import ValidationError


def storage_root() -> Path:
    root = Path(settings.images_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        root.chmod(0o700)
    return root


def resolve_storage_key(key: str) -> Path:
    root = storage_root()
    relative = Path(key)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValidationError("Invalid image storage reference.")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ValidationError("Image storage reference escapes the configured storage root.")
    return resolved


def write_image(project_id: int, record_id: int, folder: str, extension: str, content: bytes) -> str:
    key = f"projects/{project_id}/records/{record_id}/{folder}/{uuid4().hex}{extension}"
    path = resolve_storage_key(key)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.write_bytes(content)
        if os.name != "nt":
            path.chmod(0o600)
    except OSError:
        path.unlink(missing_ok=True)
        raise
    return key


def delete_storage_keys(keys: list[str]) -> None:
    for key in keys:
        try:
            resolve_storage_key(key).unlink(missing_ok=True)
        except (OSError, ValidationError):
            continue


def cleanup_empty_directories(project_id: int, record_id: int) -> None:
    root = storage_root()
    directory = (root / "projects" / str(project_id) / "records" / str(record_id)).resolve()
    if not directory.is_relative_to(root):
        return
    for parent in (directory, directory.parent, directory.parent.parent):
        try:
            parent.rmdir()
        except OSError:
            pass