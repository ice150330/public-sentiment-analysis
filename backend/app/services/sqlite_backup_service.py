"""SQLite online backup service."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.database import DATABASE_URL


class SQLiteBackupError(RuntimeError):
    """Raised when a SQLite backup operation cannot be completed."""


@dataclass(frozen=True)
class DatabaseBackup:
    filename: str
    path: Path
    size_bytes: int
    created_at: str

    def to_public_dict(self) -> dict:
        return {
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "download_url": f"/api/v1/system/database/backups/{self.filename}",
        }


def backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_sqlite_database_path(database_url: str = DATABASE_URL) -> Path:
    """Resolve the active SQLite database path from DATABASE_URL."""
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        raise SQLiteBackupError("Only SQLite database backup is supported")

    database = url.database
    if not database or database == ":memory:":
        raise SQLiteBackupError("File-based SQLite database is required for backup")

    path = Path(database)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def resolve_backup_dir() -> Path:
    configured = os.getenv("SQLITE_BACKUP_DIR")
    if configured:
        path = Path(configured)
        return path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()
    return backend_root() / "backups"


def _backup_from_path(path: Path) -> DatabaseBackup:
    stat = path.stat()
    return DatabaseBackup(
        filename=path.name,
        path=path,
        size_bytes=stat.st_size,
        created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
    )


def create_sqlite_backup() -> DatabaseBackup:
    """Create a consistent SQLite backup using the native online backup API."""
    source_path = resolve_sqlite_database_path()
    if not source_path.exists():
        raise SQLiteBackupError(f"SQLite database not found: {source_path}")

    backup_dir = resolve_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    filename = f"sentiment-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    target_path = backup_dir / filename

    try:
        with sqlite3.connect(source_path) as source, sqlite3.connect(target_path) as target:
            source.backup(target)
    except sqlite3.Error as exc:
        if target_path.exists():
            target_path.unlink()
        raise SQLiteBackupError(f"SQLite backup failed: {exc}") from exc

    return _backup_from_path(target_path)


def list_sqlite_backups() -> list[DatabaseBackup]:
    backup_dir = resolve_backup_dir()
    if not backup_dir.exists():
        return []

    backups = [_backup_from_path(path) for path in backup_dir.glob("*.db") if path.is_file()]
    return sorted(backups, key=lambda item: item.created_at, reverse=True)


def get_sqlite_backup_path(filename: str) -> Path:
    safe_name = Path(filename).name
    if safe_name != filename or not filename.endswith(".db"):
        raise SQLiteBackupError("Invalid backup filename")

    path = (resolve_backup_dir() / safe_name).resolve()
    backup_root = resolve_backup_dir().resolve()
    if backup_root not in path.parents and path != backup_root:
        raise SQLiteBackupError("Invalid backup path")
    if not path.is_file():
        raise FileNotFoundError(filename)
    return path
