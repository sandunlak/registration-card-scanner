"""Safe SQLite database backup utility.

Uses SQLite's native online backup API (sqlite3.Connection.backup)
which creates a consistent point-in-time snapshot without locking
or interrupting active write transactions.
"""

from __future__ import annotations

import argparse
import datetime
import logging
from pathlib import Path
import sqlite3

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_backup(
    destination_dir: str | Path | None = None,
    backup_filename: str | None = None,
) -> Path:
    """Create a point-in-time snapshot of the SQLite database.

    Args:
        destination_dir: Directory where the backup file will be saved.
                         Defaults to `./data/backups`.
        backup_filename: Custom filename. Defaults to `app_backup_YYYYMMDD_HHMMSS.db`.

    Returns:
        Path to the created backup file.
    """
    db_url = settings.database_url
    if not ("sqlite" in db_url):
        raise ValueError("Backup utility is currently configured for SQLite databases.")

    source_path_str = db_url.split(":///")[-1]
    source_path = Path(source_path_str).resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"Source database file not found at: {source_path}")

    # Determine backup destination
    dest_dir = (
        Path(destination_dir)
        if destination_dir
        else source_path.parent.parent / "backups"
    )
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = backup_filename or f"app_backup_{timestamp}.db"
    backup_path = dest_dir / filename

    # Perform online backup
    source_conn = sqlite3.connect(source_path)
    dest_conn = sqlite3.connect(backup_path)

    try:
        source_conn.backup(dest_conn)
        logger.info("Backup successfully created at %s", backup_path)
    finally:
        dest_conn.close()
        source_conn.close()

    return backup_path


def restore_backup(backup_path: str | Path) -> None:
    """Restore database from a backup file using safe online copy."""
    src = Path(backup_path).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Backup file not found at: {src}")

    db_url = settings.database_url
    target_path_str = db_url.split(":///")[-1]
    target_path = Path(target_path_str).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    backup_conn = sqlite3.connect(src)
    target_conn = sqlite3.connect(target_path)

    try:
        backup_conn.backup(target_conn)
        logger.info("Database successfully restored from %s", src)
    finally:
        target_conn.close()
        backup_conn.close()


def main() -> None:
    """CLI entrypoint: `python -m app.core.backup`."""
    parser = argparse.ArgumentParser(description="Registration Card Scanner DB Backup Tool")
    parser.add_argument("--action", choices=["backup", "restore"], default="backup")
    parser.add_argument("--file", help="Path to backup file for restore, or target directory for backup")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    if args.action == "backup":
        result = create_backup(destination_dir=args.file)
        print(f"Database backed up to: {result}")
    elif args.action == "restore":
        if not args.file:
            parser.error("--file is required when restoring")
        restore_backup(args.file)
        print(f"Database restored from: {args.file}")


if __name__ == "__main__":
    main()
