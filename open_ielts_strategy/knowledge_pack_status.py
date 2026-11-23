"""Operational checks for the product's published Knowledge Pack."""
from __future__ import annotations

import json
from pathlib import Path

from .knowledge_pack import KnowledgePackError, load_knowledge_pack


def inspect_knowledge_pack(path: str | Path = "knowledge") -> dict:
    """Return a safe, machine-readable status without creating or approving content."""
    root = Path(path)
    manifest = root / "manifest.json"
    if not root.exists():
        return {
            "status": "missing",
            "path": str(root),
            "usable": False,
            "reason": "knowledge_pack_directory_missing",
            "next_action": "Build a pack from rights-reviewed, content-approved and publication-approved records.",
        }
    if not manifest.is_file():
        return {
            "status": "incomplete",
            "path": str(root),
            "usable": False,
            "reason": "manifest_missing",
            "next_action": "Complete the pack manifest and its checksummed record files.",
        }
    try:
        pack = load_knowledge_pack(root)
    except (KnowledgePackError, OSError, ValueError) as exc:
        return {
            "status": "invalid",
            "path": str(root),
            "usable": False,
            "reason": "pack_validation_failed",
            "detail": str(exc),
            "next_action": "Fix validation errors; do not bypass content or publication approval gates.",
        }
    return {
        "status": "ready",
        "path": str(root),
        "usable": True,
        "pack_version": pack.pack_version,
        "schema_version": pack.schema_version,
        "manifest_sha256": pack.manifest_sha256,
        "counts": {
            "strategies": len(pack.strategies),
            "concepts": len(pack.concepts),
            "relationships": len(pack.relationships),
            "learning_paths": len(pack.learning_paths),
            "examples": len(pack.examples),
        },
    }


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", default="knowledge")
    args = parser.parse_args(argv)
    result = inspect_knowledge_pack(args.pack)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["usable"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
