"""Deterministic local Knowledge Pack builder with explicit human confirmation."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .knowledge_pack import (
    FORMAT, KnowledgePackError, _validate_strategy, load_knowledge_pack,
)


def build_knowledge_pack(strategies: list[dict[str, Any]], destination: str | Path, *,
                         pack_version: str, human_confirmed: bool,
                         store=None,
                         source_item_ids_by_strategy: dict[str, list[str]] | None = None) -> dict:
    """Build a new local pack; never commits or pushes to Git.

    Source-derived strategy records must map to private semantic item IDs whose
    content and publication approvals both pass the SQLite governance gate.
    Those private IDs and review notes are used only for the check and never enter
    the generated pack.
    """
    if human_confirmed is not True:
        raise KnowledgePackError("pack build requires explicit human confirmation")
    if not isinstance(strategies, list) or not strategies:
        raise KnowledgePackError("strategies must be a non-empty list")
    if not isinstance(pack_version, str):
        raise KnowledgePackError("pack_version must be semantic version text")
    from .knowledge_pack import _SEMVER
    if not _SEMVER.fullmatch(pack_version):
        raise KnowledgePackError("pack_version must be semantic version text")
    source_item_ids_by_strategy = source_item_ids_by_strategy or {}
    if not isinstance(source_item_ids_by_strategy, dict):
        raise KnowledgePackError("source_item_ids_by_strategy must be an object")

    validated = [_validate_strategy(item, f"<{index}>") for index, item in enumerate(strategies)]
    identifiers = [item["id"] for item in validated]
    if len(identifiers) != len(set(identifiers)):
        raise KnowledgePackError("strategy IDs must be unique")
    known = set(identifiers)
    for item in validated:
        for relation_ids in item["relationships"].values():
            missing = sorted(set(relation_ids) - known)
            if missing:
                raise KnowledgePackError(f"{item['id']}: relationship references unknown strategies: {missing}")

    unknown_mappings = set(source_item_ids_by_strategy) - known
    if unknown_mappings:
        raise KnowledgePackError(f"source approval mapping references unknown strategies: {sorted(unknown_mappings)}")
    expected_rights_basis = {
        "original": "self_authored",
        "independently_authored": "independently_authored",
        "public_domain": "public_domain",
        "permissioned": "permission_confirmed",
    }
    from .knowledge_pipeline import assert_items_publishable
    for item in validated:
        strategy_id = item["id"]
        item_ids = source_item_ids_by_strategy.get(strategy_id, [])
        if item["provenance"]["basis"] != "original" and not item_ids:
            raise KnowledgePackError(f"{strategy_id}: source-derived provenance requires private publication-review IDs")
        if item_ids:
            if not isinstance(item_ids, list) or any(not isinstance(value, str) for value in item_ids):
                raise KnowledgePackError(f"{strategy_id}: source item mapping must be a list of IDs")
            if store is None:
                raise KnowledgePackError("private SQLite store is required to verify source-derived approvals")
            try:
                approvals = assert_items_publishable(store, list(dict.fromkeys(item_ids)))
            except (ValueError, KeyError) as exc:
                raise KnowledgePackError(f"{strategy_id}: source-derived items failed publication approval") from exc
            required_basis = expected_rights_basis[item["provenance"]["basis"]]
            if any(record["rights_basis"] != required_basis for record in approvals):
                raise KnowledgePackError(f"{strategy_id}: private publication rights basis does not match public provenance")

    root = Path(destination).expanduser().absolute()
    if root.exists():
        raise KnowledgePackError("destination already exists; pack builder never overwrites an existing directory")
    parent = root.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".knowledge-pack-", dir=parent))
    try:
        file_entries = []
        for item in sorted(validated, key=lambda value: value["id"]):
            relative = Path("strategies") / item["skill"] / f"{item['id']}.json"
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = (json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            target.write_bytes(payload)
            file_entries.append({
                "path": relative.as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
            })
        manifest = {
            "format": FORMAT,
            "schema_version": "1.0",
            "pack_version": pack_version,
            "files": file_entries,
        }
        manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        (staging / "manifest.json").write_bytes(manifest_bytes)
        # Verify the exact staged artifact before making it visible at destination.
        pack = load_knowledge_pack(staging)
        os.replace(staging, root)
        return {
            "destination": str(root),
            "pack_version": pack.pack_version,
            "strategy_count": len(pack.strategies),
            "manifest_sha256": pack.manifest_sha256,
            "committed_to_git": False,
            "pushed_to_remote": False,
        }
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
