"""Private SQLite backup/restore helpers. Backups are not encrypted."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def _ensure_private_parent(directory: Path) -> None:
    """Create missing parent directories as private without changing existing ones."""
    missing = []
    current = directory
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent

    for candidate in reversed(missing):
        try:
            candidate.mkdir(mode=0o700)
        except FileExistsError:
            # Another process may have created it; never change permissions on
            # a directory we did not create ourselves.
            continue
        try:
            candidate.chmod(0o700)
        except OSError:
            pass


def backup_database(source_path: str | Path, destination_path: str | Path) -> dict:
    source = Path(source_path).expanduser()
    destination = Path(destination_path).expanduser()
    if not source.is_file() or source.resolve() == destination.resolve():
        raise ValueError("source database must exist and destination must be different")
    if destination.exists():
        raise FileExistsError("refusing to overwrite an existing backup")
    if destination.parent.resolve() == Path.cwd().resolve():
        raise ValueError("store backups in a dedicated private directory, not the repository root")
    _ensure_private_parent(destination.parent)
    try:
        with sqlite3.connect(str(source)) as src, sqlite3.connect(str(destination)) as dst:
            src.backup(dst)
            check = dst.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                raise sqlite3.DatabaseError("backup integrity check failed")
        try:
            destination.chmod(0o600)
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
    if destination.parent.resolve() == Path.cwd().resolve():
        raise ValueError("restore into a private local directory, not repository root")
    _ensure_private_parent(destination.parent)
    try:
        with sqlite3.connect(backup.resolve().as_uri() + "?mode=ro", uri=True) as src, sqlite3.connect(str(destination)) as dst:
            if src.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise sqlite3.DatabaseError("backup integrity check failed")
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise sqlite3.DatabaseError("restored database integrity check failed")
        try:
            destination.chmod(0o600)
        except OSError:
            pass
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {"restored_path": str(destination), "integrity": "ok", "encrypted": False}
