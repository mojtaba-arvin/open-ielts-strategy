"""Reviewable public-record diff between two verified Knowledge Pack revisions."""
from __future__ import annotations

import difflib
import json
from typing import Any

from .knowledge_pack import KnowledgePack, load_knowledge_pack
from .publication_scan import scan_publication_leaks

_RECORD_COLLECTIONS = {
    "strategies": "strategies",
    "concepts": "concepts",
    "relationships": "relationships",
    "learning_paths": "learning_paths",
}


def _canonical(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def generate_publication_diff(current: KnowledgePack, candidate: KnowledgePack) -> dict:
    """Create a deterministic public diff; never stages, commits, or pushes it."""
    candidate_payloads = [
        _canonical(record)
        for collection in _RECORD_COLLECTIONS
        for record in getattr(candidate, collection)
    ]
    secret_scan = scan_publication_leaks(candidate_payloads, [])
    if not secret_scan["passed"]:
        raise ValueError("candidate pack contains secret-like material; publication diff blocked")

    changes = []
    for collection, label in _RECORD_COLLECTIONS.items():
        before = {item["id"]: item for item in getattr(current, collection)}
        after = {item["id"]: item for item in getattr(candidate, collection)}
        for record_id in sorted(set(before) | set(after)):
            old, new = before.get(record_id), after.get(record_id)
            if old == new:
                continue
            status = "added" if old is None else "removed" if new is None else "modified"
            diff_lines = list(difflib.unified_diff(
                _canonical(old).splitlines(keepends=True) if old is not None else [],
                _canonical(new).splitlines(keepends=True) if new is not None else [],
                fromfile=f"{label}/{record_id} (current)",
                tofile=f"{label}/{record_id} (candidate)",
            ))
            changes.append({
                "record_type": collection,
                "record_id": record_id,
                "status": status,
                "diff": "".join(diff_lines),
            })
    if changes and candidate.pack_version == current.pack_version:
        raise ValueError("candidate pack version must change when published records change")
    return {
        "current_pack_version": current.pack_version,
        "candidate_pack_version": candidate.pack_version,
        "current_manifest_sha256": current.manifest_sha256,
        "candidate_manifest_sha256": candidate.manifest_sha256,
        "change_count": len(changes),
        "changes": changes,
        "secret_scan_passed": True,
        "git_commit_created": False,
        "git_push_performed": False,
        "requires_human_review": True,
    }


def diff_pack_directories(current_path: str, candidate_path: str) -> dict:
    current = load_knowledge_pack(current_path)
    candidate = load_knowledge_pack(candidate_path)
    return generate_publication_diff(current, candidate)
