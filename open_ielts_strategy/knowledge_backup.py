"""Private SQLite backup/restore helpers. Backups are not encrypted."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def backup_database(source_path: str | Path, destination_path: str | Path) -> dict:
    source = Path(source_path).expanduser()
    destination = Path(destination_path).expanduser()
    if not source.is_file() or source.resolve() == destination.resolve():
        raise ValueError("source database must exist and destination must be different")
    if destination.exists():
        raise FileExistsError("refusing to overwrite an existing backup")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.parent.resolve() == Path.cwd().resolve():
        raise ValueError("store backups in a dedicated private directory, not the repository root")
    try:
        with sqlite3.connect(str(source)) as src, sqlite3.connect(str(destination)) as dst:
            src.backup(dst)
            check = dst.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                raise sqlite3.DatabaseError("backup integrity check failed")
        try:
            destination.chmod(0o600)
            destination.parent.chmod(0o700)
        except OSError:
            pass
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {"backup_path": str(destination), "integrity": "ok", "encrypted": False}


def restore_database(backup_path: str | Path, destination_path: str | Path) -> dict:
    backup = Path(backup_path).expanduser()
    destination = Path(destination_path).expanduser()
    if not backup.is_file() or destination.exists() or backup.resolve() == destination.resolve():
        raise ValueError("backup must exist and restore destination must be new")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.parent.resolve() == Path.cwd().resolve():
        raise ValueError("restore into a private local directory, not repository root")
    try:
        with sqlite3.connect(backup.resolve().as_uri() + "?mode=ro", uri=True) as src, sqlite3.connect(str(destination)) as dst:
            if src.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise sqlite3.DatabaseError("backup integrity check failed")
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise sqlite3.DatabaseError("restored database integrity check failed")
        try:
            destination.chmod(0o600)
            destination.parent.chmod(0o700)
        except OSError:
            pass
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {"restored_path": str(destination), "integrity": "ok", "encrypted": False}
