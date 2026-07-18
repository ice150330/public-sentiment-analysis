"""
SQLite database backup script.

Usage:
    cd backend
    python scripts/backup_sqlite.py
    python scripts/backup_sqlite.py --backup-dir ./backups
"""

import argparse
import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from app.services.sqlite_backup_service import SQLiteBackupError, create_sqlite_backup


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an online SQLite backup.")
    parser.add_argument("--backup-dir", help="Target backup directory. Defaults to backend/backups.")
    args = parser.parse_args()

    if args.backup_dir:
        os.environ["SQLITE_BACKUP_DIR"] = args.backup_dir

    try:
        backup = create_sqlite_backup()
    except SQLiteBackupError as exc:
        print(f"Backup failed: {exc}")
        return 1

    print("Backup created")
    print(f"  file: {backup.filename}")
    print(f"  path: {backup.path}")
    print(f"  size: {backup.size_bytes} bytes")
    print(f"  created_at: {backup.created_at}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
