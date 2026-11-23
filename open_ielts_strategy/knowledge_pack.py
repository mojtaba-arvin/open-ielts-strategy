"""Deterministic, dependency-free reader for published IELTS Knowledge Packs.

This module deliberately does not import the private SQLite, extraction, or model
provider layers. A cloned repository can consume a validated pack offline.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

FORMAT = "open-ielts-knowledge-pack"
MAX_MANIFEST_BYTES = 1_000_000
MAX_STRATEGY_BYTES = 256_000
MAX_PACK_FILES = 5_000
MAX_TOTAL_BYTES = 50_000_000
SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")
_PRIVATE_KEYS = {
    "source_id", "source_ids", "extraction_id", "extraction_ids",
    "source_body", "transcript", "transcript_text", "private_source_path",
    "review_note", "rights_evidence_path",
}


class KnowledgePackError(ValueError):
    """Raised when a published pack is invalid or unsafe to consume."""


@dataclass(frozen=True)
class KnowledgePack:
    root: Path
    schema_version: str
    pack_version: str
    strategies: tuple[dict[str, Any], ...]
    manifest_sha256: str
    concepts: tuple[dict[str, Any], ...] = ()
    relationships: tuple[dict[str, Any], ...] = ()
    learning_paths: tuple[dict[str, Any], ...] = ()

    def get_concept(self, concept_id: str) -> dict[str, Any] | None:
        return next((item for item in self.concepts if item["id"] == concept_id), None)

    def get_learning_path(self, path_id: str) -> dict[str, Any] | None:
        return next((item for item in self.learning_paths if item["id"] == path_id), None)

    def get_strategy(self, strategy_id: str) -> dict[str, Any] | None:
        return next((item for item in self.strategies if item["id"] == strategy_id), None)

    def search_strategies(self, query: str, *, skill: str | None = None,
                          limit: int = 10) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be non-empty text")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        stopwords = {"a", "an", "and", "are", "as", "at", "be", "can", "do", "for", "from", "how", "i", "in", "is", "it", "of", "on", "or", "the", "this", "to", "what", "when", "where", "which", "who", "with", "you"}
        terms = tuple(term for term in dict.fromkeys(re.findall(r"[a-z0-9]+", query.casefold())) if term not in stopwords)
        ranked = []
        for item in self.strategies:
            if skill is not None and item["skill"] != skill:
                continue
            haystack = " ".join((
                item["id"], item["title"], item["summary"],
                " ".join(item.get("purpose", [])),
                " ".join(item.get("steps", [])),
                " ".join(item.get("applicability", {}).get("question_types", [])),
            )).casefold()
            score = sum(1 for term in terms if term in haystack)
            if score:
                ranked.append((score, item["id"], item))
        ranked.sort(key=lambda value: (-value[0], value[1]))
        return [item for _, _, item in ranked[:limit]]


def _reject_private_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.casefold() in _PRIVATE_KEYS:
                raise KnowledgePackError(f"private field is not allowed in published knowledge: {path}.{key}")
            _reject_private_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_private_fields(child, f"{path}[{index}]")


def _safe_pack_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise KnowledgePackError("manifest paths must be non-empty POSIX relative paths")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise KnowledgePackError(f"unsafe manifest path: {relative!r}")
    candidate = root.joinpath(*pure.parts)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise KnowledgePackError(f"manifest path escapes pack or does not exist: {relative!r}") from exc
    current = root
    for part in pure.parts:
        current = current / part
        if current.is_symlink():
            raise KnowledgePackError(f"symlink entries are not allowed: {relative!r}")
    if not resolved.is_file():
        raise KnowledgePackError(f"manifest entry is not a regular file: {relative!r}")
    return resolved


def _validate_strategy(item: Any, relative: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise KnowledgePackError(f"{relative}: strategy must be a JSON object")
    _reject_private_fields(item)
    required = {
        "id", "schema_version", "title", "skill", "summary", "purpose",
        "reasoning", "steps", "applicability", "limitations",
        "common_mistakes", "examples", "relationships", "provenance",
        "review", "version",
    }
    if set(item) != required:
        missing, extra = sorted(required - set(item)), sorted(set(item) - required)
        raise KnowledgePackError(f"{relative}: strategy fields mismatch (missing={missing}, extra={extra})")
    for field in ("id", "title", "summary", "skill", "version"):
        if not isinstance(item[field], str) or not item[field].strip():
            raise KnowledgePackError(f"{relative}: {field} must be non-empty text")
    if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,127}", item["id"]):
        raise KnowledgePackError(f"{relative}: invalid strategy ID")
    if item["skill"] not in {"speaking", "writing", "reading", "listening", "general"}:
        raise KnowledgePackError(f"{relative}: unsupported skill")
    if len(item["title"]) > 160 or len(item["summary"]) > 2000:
        raise KnowledgePackError(f"{relative}: title or summary exceeds its length limit")
    if not _SEMVER.fullmatch(item["version"]):
        raise KnowledgePackError(f"{relative}: version must be semantic version text")
    if not isinstance(item["schema_version"], str) or item["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS:
        raise KnowledgePackError(f"{relative}: unsupported strategy schema version")
    for field in ("purpose", "reasoning", "steps", "limitations", "common_mistakes", "examples"):
        if not isinstance(item[field], list) or any(not isinstance(v, str) or not v.strip() for v in item[field]):
            raise KnowledgePackError(f"{relative}: {field} must be an array of non-empty strings")
    applicability = item["applicability"]
    if not isinstance(applicability, dict) or set(applicability) != {"question_types", "parts", "conditions"}:
        raise KnowledgePackError(f"{relative}: invalid applicability object")
    if any(not isinstance(applicability[key], list) or any(not isinstance(v, str) for v in applicability[key])
           for key in applicability):
        raise KnowledgePackError(f"{relative}: applicability values must be string arrays")
    relationships = item["relationships"]
    if not isinstance(relationships, dict) or set(relationships) != {
        "requires", "complements", "conflicts_with", "alternatives"
    }:
        raise KnowledgePackError(f"{relative}: invalid relationships object")
    if any(not isinstance(relationships[key], list) or any(not isinstance(v, str) for v in relationships[key])
           for key in relationships):
        raise KnowledgePackError(f"{relative}: relationship values must be string arrays")
    provenance = item["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {"basis", "public_references"}:
        raise KnowledgePackError(f"{relative}: invalid public provenance object")
    if not isinstance(provenance["basis"], str) or provenance["basis"] not in {"original", "independently_authored", "public_domain", "permissioned"}:
        raise KnowledgePackError(f"{relative}: provenance basis is not publishable")
    if not isinstance(provenance["public_references"], list):
        raise KnowledgePackError(f"{relative}: public_references must be an array")
    for reference in provenance["public_references"]:
        parsed = urlparse(reference) if isinstance(reference, str) else None
        if parsed is None or parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise KnowledgePackError(f"{relative}: public_references must contain credential-free HTTPS URLs")
    review = item["review"]
    if review != {"content_status": "approved", "publication_status": "approved"}:
        raise KnowledgePackError(f"{relative}: both content and publication approval are required")
    return item


def _validate_public_provenance_and_review(item: dict, relative: str) -> None:
    provenance = item.get("provenance")
    if not isinstance(provenance, dict) or set(provenance) != {"basis", "public_references"}:
        raise KnowledgePackError(f"{relative}: invalid public provenance object")
    if not isinstance(provenance["basis"], str) or provenance["basis"] not in {
        "original", "independently_authored", "public_domain", "permissioned"
    }:
        raise KnowledgePackError(f"{relative}: provenance basis is not publishable")
    if not isinstance(provenance["public_references"], list):
        raise KnowledgePackError(f"{relative}: public_references must be an array")
    for reference in provenance["public_references"]:
        try:
            parsed = urlparse(reference) if isinstance(reference, str) else None
        except ValueError as exc:
            raise KnowledgePackError(f"{relative}: invalid public HTTPS reference") from exc
        if parsed is None or parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise KnowledgePackError(f"{relative}: public_references must contain credential-free HTTPS URLs")
    if item.get("review") != {"content_status": "approved", "publication_status": "approved"}:
        raise KnowledgePackError(f"{relative}: both content and publication approval are required")


def _validate_concept(item: Any, relative: str) -> dict[str, Any]:
    required = {"id", "schema_version", "title", "definition", "related_strategies",
                "provenance", "review", "version"}
    if not isinstance(item, dict) or set(item) != required:
        raise KnowledgePackError(f"{relative}: invalid concept fields")
    _reject_private_fields(item)
    if any(not isinstance(item[key], str) or not item[key].strip()
           for key in ("id", "schema_version", "title", "definition", "version")):
        raise KnowledgePackError(f"{relative}: concept text fields must be non-empty")
    if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,127}", item["id"]):
        raise KnowledgePackError(f"{relative}: invalid concept ID")
    if item["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS or not _SEMVER.fullmatch(item["version"]):
        raise KnowledgePackError(f"{relative}: unsupported concept schema or version")
    if not isinstance(item["related_strategies"], list) or any(
        not isinstance(value, str) or not value for value in item["related_strategies"]
    ):
        raise KnowledgePackError(f"{relative}: related_strategies must be non-empty string IDs")
    _validate_public_provenance_and_review(item, relative)
    return item


def _validate_relationship(item: Any, relative: str) -> dict[str, Any]:
    required = {"id", "schema_version", "from_id", "to_id", "type", "rationale", "provenance", "review"}
    if not isinstance(item, dict) or set(item) != required:
        raise KnowledgePackError(f"{relative}: invalid relationship fields")
    _reject_private_fields(item)
    for key in ("id", "schema_version", "from_id", "to_id", "type", "rationale"):
        if not isinstance(item[key], str) or not item[key].strip():
            raise KnowledgePackError(f"{relative}: relationship {key} must be non-empty text")
    if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,127}", item["id"]):
        raise KnowledgePackError(f"{relative}: invalid relationship ID")
    if item["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS:
        raise KnowledgePackError(f"{relative}: unsupported relationship schema version")
    if item["type"] not in {"requires", "complements", "conflicts_with", "alternative_to", "defines", "illustrates"}:
        raise KnowledgePackError(f"{relative}: unsupported relationship type")
    if len(item["rationale"]) > 2000:
        raise KnowledgePackError(f"{relative}: relationship rationale exceeds size limit")
    _validate_public_provenance_and_review(item, relative)
    return item


def _validate_learning_path(item: Any, relative: str) -> dict[str, Any]:
    required = {"id", "schema_version", "title", "skill", "description", "objectives",
                "steps", "prerequisites", "provenance", "review", "version"}
    if not isinstance(item, dict) or set(item) != required:
        raise KnowledgePackError(f"{relative}: invalid learning path fields")
    _reject_private_fields(item)
    for key in ("id", "schema_version", "title", "skill", "description", "version"):
        if not isinstance(item[key], str) or not item[key].strip():
            raise KnowledgePackError(f"{relative}: learning path {key} must be non-empty text")
    if not re.fullmatch(r"[a-z][a-z0-9_.-]{2,127}", item["id"]):
        raise KnowledgePackError(f"{relative}: invalid learning path ID")
    if item["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS or not _SEMVER.fullmatch(item["version"]):
        raise KnowledgePackError(f"{relative}: unsupported learning path schema or version")
    if item["skill"] not in {"speaking", "writing", "reading", "listening", "general"}:
        raise KnowledgePackError(f"{relative}: unsupported learning path skill")
    for key in ("objectives", "prerequisites"):
        if not isinstance(item[key], list) or any(not isinstance(value, str) or not value.strip() for value in item[key]):
            raise KnowledgePackError(f"{relative}: {key} must be arrays of non-empty strings")
    if not isinstance(item["steps"], list) or not item["steps"]:
        raise KnowledgePackError(f"{relative}: learning path requires at least one step")
    for step in item["steps"]:
        if not isinstance(step, dict) or set(step) != {"order", "strategy_id", "activity"}:
            raise KnowledgePackError(f"{relative}: invalid learning path step")
        if type(step["order"]) is not int or step["order"] < 1:
            raise KnowledgePackError(f"{relative}: step order must be a positive integer")
        if any(not isinstance(step[key], str) or not step[key].strip() for key in ("strategy_id", "activity")):
            raise KnowledgePackError(f"{relative}: step strategy_id and activity must be non-empty text")
    orders = [step["order"] for step in item["steps"]]
    if len(orders) != len(set(orders)):
        raise KnowledgePackError(f"{relative}: learning path step order values must be unique")
    _validate_public_provenance_and_review(item, relative)
    return item


def load_knowledge_pack(path: str | Path) -> KnowledgePack:
    """Load and verify a directory pack; no database, network, or LLM is required."""
    root = Path(path).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise KnowledgePackError("knowledge pack path must be a directory")
    manifest_path = _safe_pack_file(root, "manifest.json")
    try:
        if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
            raise KnowledgePackError("manifest exceeds size limit")
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise KnowledgePackError("manifest.json is unreadable or invalid JSON") from exc
    if not isinstance(manifest, dict) or set(manifest) != {
        "format", "schema_version", "pack_version", "files"
    }:
        raise KnowledgePackError("manifest has an unsupported shape")
    if manifest["format"] != FORMAT:
        raise KnowledgePackError("unsupported knowledge pack format")
    if not isinstance(manifest["schema_version"], str) or manifest["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS:
        raise KnowledgePackError("unsupported knowledge pack schema version")
    if not isinstance(manifest["pack_version"], str) or not _SEMVER.fullmatch(manifest["pack_version"]):
        raise KnowledgePackError("pack_version must be semantic version text")
    files = manifest["files"]
    if not isinstance(files, list) or not files or len(files) > MAX_PACK_FILES:
        raise KnowledgePackError("manifest files must contain 1..5000 entries")
    seen = set()
    strategies, concepts, relationships, learning_paths = [], [], [], []
    total_bytes = 0
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise KnowledgePackError("each manifest file entry must contain path and sha256")
        relative, expected = entry["path"], entry["sha256"]
        if not isinstance(relative, str) or relative in seen:
            raise KnowledgePackError(f"duplicate manifest path: {relative!r}")
        seen.add(relative)
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise KnowledgePackError(f"invalid SHA-256 for {relative!r}")
        file_path = _safe_pack_file(root, relative)
        file_size = file_path.stat().st_size
        if file_size > MAX_STRATEGY_BYTES:
            raise KnowledgePackError(f"knowledge record exceeds size limit: {relative}")
        total_bytes += file_size
        if total_bytes > MAX_TOTAL_BYTES:
            raise KnowledgePackError("knowledge pack exceeds total size limit")
        payload = file_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected:
            raise KnowledgePackError(f"checksum mismatch: {relative}")
        if not relative.endswith(".json"):
            raise KnowledgePackError(f"published knowledge records must use JSON: {relative}")
        try:
            record = json.loads(payload)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise KnowledgePackError(f"invalid JSON knowledge record: {relative}") from exc
        if relative.startswith("strategies/"):
            parts = PurePosixPath(relative).parts
            if len(parts) < 3:
                raise KnowledgePackError(f"strategy files must be grouped under a skill directory: {relative}")
            validated = _validate_strategy(record, relative)
            if parts[1] != validated["skill"]:
                raise KnowledgePackError(f"{relative}: strategy skill does not match its directory")
            strategies.append(validated)
        elif relative.startswith("concepts/"):
            concepts.append(_validate_concept(record, relative))
        elif relative.startswith("relationships/"):
            relationships.append(_validate_relationship(record, relative))
        elif relative.startswith("learning-paths/"):
            learning_paths.append(_validate_learning_path(record, relative))
        else:
            raise KnowledgePackError(f"unsupported v1 pack file: {relative}")
    if not strategies:
        raise KnowledgePackError("Knowledge Pack must contain at least one strategy")
    all_records = strategies + concepts + relationships + learning_paths
    all_ids = [item["id"] for item in all_records]
    if len(all_ids) != len(set(all_ids)):
        raise KnowledgePackError("record IDs must be unique across the Knowledge Pack")
    strategy_ids = {item["id"] for item in strategies}
    entity_ids = strategy_ids | {item["id"] for item in concepts}
    for item in strategies:
        for relation_ids in item["relationships"].values():
            missing = sorted(set(relation_ids) - strategy_ids)
            if missing:
                raise KnowledgePackError(f"{item['id']}: relationship references unknown strategies: {missing}")
    for item in concepts:
        missing = sorted(set(item["related_strategies"]) - strategy_ids)
        if missing:
            raise KnowledgePackError(f"{item['id']}: related_strategies references unknown strategies: {missing}")
    for item in relationships:
        if item["from_id"] not in entity_ids or item["to_id"] not in entity_ids:
            raise KnowledgePackError(f"{item['id']}: relationship references an unknown entity")
    for item in learning_paths:
        missing = sorted({step["strategy_id"] for step in item["steps"]} - strategy_ids)
        if missing:
            raise KnowledgePackError(f"{item['id']}: learning path references unknown strategies: {missing}")
    strategies.sort(key=lambda item: item["id"])
    concepts.sort(key=lambda item: item["id"])
    relationships.sort(key=lambda item: item["id"])
    learning_paths.sort(key=lambda item: item["id"])
    return KnowledgePack(
        root=root, schema_version=manifest["schema_version"],
        pack_version=manifest["pack_version"], strategies=tuple(strategies),
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        concepts=tuple(concepts), relationships=tuple(relationships),
        learning_paths=tuple(learning_paths),
    )
