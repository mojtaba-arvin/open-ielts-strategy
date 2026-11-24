"""Create a private local workspace for authoring Knowledge Pack records."""
from __future__ import annotations
import json, os, shutil
from pathlib import Path
from .knowledge_pack import KnowledgePackError

STRATEGY_TEMPLATE = {
    "id": "REPLACE_WITH_STABLE_ID",
    "schema_version": "1.0",
    "title": "REPLACE_WITH_TITLE",
    "skill": "speaking",
    "summary": "REPLACE_WITH_DESCRIPTION",
    "purpose": [
        "REPLACE_WITH_GOAL"
    ],
    "reasoning": [
        "REPLACE_WITH_REASONING"
    ],
    "steps": [
        "REPLACE_WITH_STEP_1",
        "REPLACE_WITH_STEP_2"
    ],
    "applicability": {
        "question_types": [],
        "parts": [],
        "conditions": []
    },
    "limitations": [
        "REPLACE_WITH_LIMITATION"
    ],
    "common_mistakes": [
        "REPLACE_WITH_MISTAKE"
    ],
    "examples": [
        "REPLACE_WITH_ORIGINAL_EXAMPLE"
    ],
    "relationships": {
        "requires": [],
        "complements": [],
        "conflicts_with": [],
        "alternatives": []
    },
    "provenance": {
        "basis": "CHOOSE_original_independently_authored_public_domain_or_permissioned",
        "public_references": []
    },
    "review": {
        "content_status": "draft",
        "publication_status": "pending"
    },
    "version": "0.1.0"
}

WORKSPACE_README = """# Private Knowledge Pack authoring workspace

This is a draft workspace, NOT a published or loadable Knowledge Pack.
Replace placeholders, choose a truthful provenance basis, and complete content
and rights/publication reviews independently. Only then set both review fields
to approved. For source-derived records, map private reviewed item IDs using
--source-item RECORD_ID=SITEM_ID; never put private IDs in public JSON.

Build into a new candidate directory, inspect the full diff, and use the
separately authorized release workflow only after human review.
"""
GITIGNORE = "*.sqlite\\n*.sqlite3\\n*.db\\n.local/\\napprovals/\\nprivate-sources/\\n"

def initialize_workspace(destination: str | Path) -> dict:
    root = Path(destination).expanduser().absolute()
    if root.exists() or root.is_symlink():
        raise KnowledgePackError("workspace destination already exists; refusing to overwrite")
    root.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        root.mkdir(mode=0o700); created = True
        (root / "drafts").mkdir(mode=0o700)
        files = {"README.md": WORKSPACE_README, ".gitignore": GITIGNORE,
                 "drafts/strategy.template.json": json.dumps(STRATEGY_TEMPLATE, ensure_ascii=False, indent=2) + "\\n"}
        for relative, content in files.items():
            target = root / relative
            with target.open("x", encoding="utf-8", newline="\\n") as stream: stream.write(content)
            if os.name != "nt": target.chmod(0o600)
        return {"created": True, "workspace": str(root), "published_pack_created": False,
                "draft_files": ["drafts/strategy.template.json"]}
    except Exception:
        if created: shutil.rmtree(root, ignore_errors=True)
        raise
