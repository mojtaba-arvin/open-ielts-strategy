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
    FORMAT, KnowledgePackError, _SEMVER, _validate_concept, _validate_learning_path,
    _validate_relationship, _validate_strategy, load_knowledge_pack,
)


def build_knowledge_pack(strategies: list[dict[str, Any]], destination: str | Path, *,
                         pack_version: str, human_confirmed: bool,
                         concepts: list[dict[str, Any]] | None = None,
                         relationships: list[dict[str, Any]] | None = None,
                         learning_paths: list[dict[str, Any]] | None = None,
                         store=None,
                         source_item_ids_by_strategy: dict[str, list[str]] | None = None,
                         semantic_embedding_provider=None) -> dict:
    """Build a new local pack; never commits or pushes to Git.

    The legacy source_item_ids_by_strategy mapping accepts any published record
    ID. Source-derived records must map to private semantic item IDs whose
    content/publication approvals and rights basis pass the SQLite gate. Private
    IDs, source bodies, and review notes are never written into the pack.
    """
    if human_confirmed is not True:
        raise KnowledgePackError("pack build requires explicit human confirmation")
    if not isinstance(strategies, list) or not strategies:
        raise KnowledgePackError("strategies must be a non-empty list")
    if not isinstance(pack_version, str) or not _SEMVER.fullmatch(pack_version):
        raise KnowledgePackError("pack_version must be semantic version text")
    source_item_ids_by_strategy = source_item_ids_by_strategy or {}
    if not isinstance(source_item_ids_by_strategy, dict):
        raise KnowledgePackError("source approval mapping must be an object")

    concepts = concepts or []
    relationships = relationships or []
    learning_paths = learning_paths or []
    if any(not isinstance(value, list) for value in (concepts, relationships, learning_paths)):
        raise KnowledgePackError("concepts, relationships, and learning_paths must be arrays")

    validated_groups = {
        "strategies": [_validate_strategy(item, f"<strategy:{index}>") for index, item in enumerate(strategies)],
        "concepts": [_validate_concept(item, f"<concept:{index}>") for index, item in enumerate(concepts)],
        "relationships": [_validate_relationship(item, f"<relationship:{index}>") for index, item in enumerate(relationships)],
        "learning-paths": [_validate_learning_path(item, f"<learning-path:{index}>") for index, item in enumerate(learning_paths)],
    }
    all_records = [item for group in validated_groups.values() for item in group]
    identifiers = [item["id"] for item in all_records]
    if len(identifiers) != len(set(identifiers)):
        raise KnowledgePackError("record IDs must be unique across the Knowledge Pack")
    strategy_ids = {item["id"] for item in validated_groups["strategies"]}
    entity_ids = strategy_ids | {item["id"] for item in validated_groups["concepts"]}
    for item in validated_groups["strategies"]:
        for relation_ids in item["relationships"].values():
            missing = sorted(set(relation_ids) - strategy_ids)
            if missing:
                raise KnowledgePackError(f"{item['id']}: relationship references unknown strategies: {missing}")
    for item in validated_groups["concepts"]:
        missing = sorted(set(item["related_strategies"]) - strategy_ids)
        if missing:
            raise KnowledgePackError(f"{item['id']}: related_strategies references unknown strategies: {missing}")
    for item in validated_groups["relationships"]:
        if item["from_id"] not in entity_ids or item["to_id"] not in entity_ids:
            raise KnowledgePackError(f"{item['id']}: relationship references an unknown entity")
    for item in validated_groups["learning-paths"]:
        missing = sorted({step["strategy_id"] for step in item["steps"]} - strategy_ids)
        if missing:
            raise KnowledgePackError(f"{item['id']}: learning path references unknown strategies: {missing}")

    unknown_mappings = set(source_item_ids_by_strategy) - set(identifiers)
    if unknown_mappings:
        raise KnowledgePackError(f"source approval mapping references unknown records: {sorted(unknown_mappings)}")
    expected_rights_basis = {
        "original": "self_authored",
        "independently_authored": "independently_authored",
        "public_domain": "public_domain",
        "permissioned": "permission_confirmed",
    }
    from .knowledge_pipeline import assert_items_publishable
    private_sources_by_key = {}
    for item in all_records:
        record_id = item["id"]
        item_ids = source_item_ids_by_strategy.get(record_id, [])
        if item["provenance"]["basis"] != "original" and not item_ids:
            raise KnowledgePackError(f"{record_id}: source-derived provenance requires private publication-review IDs")
        if item_ids:
            if not isinstance(item_ids, list) or not item_ids or any(not isinstance(value, str) for value in item_ids):
                raise KnowledgePackError(f"{record_id}: source item mapping must be a non-empty list of IDs")
            if len(item_ids) > 100:
                raise KnowledgePackError(f"{record_id}: at most 100 source items may be mapped")
            if store is None:
                raise KnowledgePackError("private SQLite store is required to verify source-derived approvals")
            unique_item_ids = list(dict.fromkeys(item_ids))
            try:
                approvals = assert_items_publishable(store, unique_item_ids)
            except (ValueError, KeyError) as exc:
                raise KnowledgePackError(f"{record_id}: source-derived items failed publication approval") from exc
            required_basis = expected_rights_basis[item["provenance"]["basis"]]
            if any(record["rights_basis"] != required_basis for record in approvals):
                raise KnowledgePackError(f"{record_id}: private publication rights basis does not match public provenance")
            placeholders = ",".join("?" for _ in unique_item_ids)
            rows = store._connection.execute(
                f"""SELECT i.item_id, s.source_id, s.body, i.text
                    FROM semantic_items i JOIN sources s ON s.source_id=i.source_id
                    WHERE i.item_id IN ({placeholders})""",
                tuple(unique_item_ids),
            ).fetchall()
            for row in rows:
                private_text = row["body"] or row["text"]
                if private_text:
                    private_sources_by_key[(row["source_id"], private_text)] = {
                        "source_id": row["source_id"], "text": private_text,
                    }

    from .publication_scan import scan_publication_leaks
    scan_payloads = [
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for item in all_records
    ]
    leak_report = scan_publication_leaks(scan_payloads, list(private_sources_by_key.values()))
    if not leak_report["passed"]:
        raise KnowledgePackError("publication leak scan detected private source overlap or secret material")
    semantic_leak_report = None
    if semantic_embedding_provider is not None:
        from .semantic_publication_scan import scan_semantic_publication_leaks
        semantic_leak_report = scan_semantic_publication_leaks(
            scan_payloads, list(private_sources_by_key.values()), semantic_embedding_provider,
        )
        if not semantic_leak_report["passed"]:
            raise KnowledgePackError("semantic publication scan detected high-similarity private source overlap")

    root = Path(destination).expanduser().absolute()
    if root.exists():
        raise KnowledgePackError("destination already exists; pack builder never overwrites an existing directory")
    parent = root.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".knowledge-pack-", dir=parent))
    try:
        file_entries = []
        for directory, records in validated_groups.items():
            for item in sorted(records, key=lambda value: value["id"]):
                if directory == "strategies":
                    relative = Path(directory) / item["skill"] / f"{item['id']}.json"
                else:
                    relative = Path(directory) / f"{item['id']}.json"
                target = staging / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                payload = (json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                target.write_bytes(payload)
                file_entries.append({"path": relative.as_posix(), "sha256": hashlib.sha256(payload).hexdigest()})
        file_entries.sort(key=lambda item: item["path"])
        manifest = {
            "format": FORMAT,
            "schema_version": "1.0",
            "pack_version": pack_version,
            "files": file_entries,
        }
        manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        (staging / "manifest.json").write_bytes(manifest_bytes)
        pack = load_knowledge_pack(staging)
        os.replace(staging, root)
        return {
            "destination": str(root),
            "pack_version": pack.pack_version,
            "strategy_count": len(pack.strategies),
            "concept_count": len(pack.concepts),
            "relationship_count": len(pack.relationships),
            "learning_path_count": len(pack.learning_paths),
            "manifest_sha256": pack.manifest_sha256,
            "exact_leak_scan": leak_report,
            "semantic_leak_scan": semantic_leak_report or {"status": "not_run", "reason": "no local semantic embedding provider configured"},
            "committed_to_git": False,
            "pushed_to_remote": False,
        }
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
