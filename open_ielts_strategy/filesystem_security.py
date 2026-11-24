"""Filesystem helpers for private local application data."""
from __future__ import annotations

from pathlib import Path


def ensure_private_directory(directory: Path) -> None:
    """Create missing directory ancestors as 0700 without changing existing ones.

    Directories are created one level at a time so every newly-created level
    receives the private mode. If another process wins a creation race, its
    directory is treated as pre-existing and is never chmodded here.
    """
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
            # Another process created it; do not alter permissions we do not own.
            continue
        try:
            candidate.chmod(0o700)
        except OSError:
            # Permission hardening is best-effort on filesystems without chmod.
            pass
