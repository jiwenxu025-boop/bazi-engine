"""Online SQLite backup and verification helpers for runtime-only application data."""

import sqlite3
from pathlib import Path


def backup_runtime_database(source: Path, destination: Path) -> None:
    """Create a consistent SQLite backup without stopping the running application."""
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as backup_connection:
        source_connection.backup(backup_connection)
    verify_runtime_database(destination)


def verify_runtime_database(path: Path) -> None:
    """Reject backups that SQLite cannot read consistently."""
    with sqlite3.connect(path) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if result != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {result}")
