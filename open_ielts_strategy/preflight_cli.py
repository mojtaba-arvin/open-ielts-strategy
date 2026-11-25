"""Offline-first preflight checks for authoring and consuming IELTS knowledge."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from .knowledge_pack_status import inspect_knowledge_pack

OPTIONAL_MODULES = {
    "documents": "pypdf",
    "local-embeddings": "sentence_transformers",
    "mcp": "mcp",
    "http-mcp": "uvicorn",
    "redis-rate-limit": "redis",
    "schema-validation": "jsonschema",
}


def _writable_location(path: Path) -> tuple[bool, str]:
    """Check an existing target or nearest existing parent without creating files."""
    candidate = path
    if candidate.exists():
        if candidate.is_dir():
            return os.access(candidate, os.W_OK), "directory_exists"
        return os.access(candidate, os.W_OK), "file_exists"
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    if not candidate.exists():
        return False, "no_existing_parent"
    return candidate.is_dir() and os.access(candidate, os.W_OK), "nearest_existing_parent"


def _ollama_models(timeout: float = 1.5) -> tuple[set[str] | None, str | None]:
    """Read model names from the local Ollama daemon; never sends learner content."""
    request = Request("http://127.0.0.1:11434/api/tags", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(1_000_000).decode("utf-8"))
    except (OSError, URLError, TimeoutError, ValueError) as exc:
        return None, type(exc).__name__
    models = payload.get("models")
    if not isinstance(models, list):
        return None, "invalid_ollama_response"
    names = {
        item.get("name")
        for item in models
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    return names, None


def run_preflight(
    *,
    mode: str = "author",
    db: str = ".local/knowledge.sqlite3",
    pack: str = "knowledge",
    provider: str | None = None,
    model: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
) -> dict:
    checks: list[dict] = []

    def add(name: str, status: str, detail: str, **extra) -> None:
        checks.append({"name": name, "status": status, "detail": detail, **extra})

    python_ok = sys.version_info >= (3, 11)
    add(
        "python",
        "ok" if python_ok else "blocked",
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}; requires Python 3.11+",
    )

    db_path = Path(db).expanduser()
    db_writable, db_reason = _writable_location(db_path)
    add(
        "private_database_path",
        "ok" if db_writable else "blocked",
        db_reason if db_writable else f"not_writable: {db_reason}",
        path=str(db_path),
    )

    pack_result = inspect_knowledge_pack(pack)
    if pack_result["usable"]:
        add(
            "published_knowledge_pack",
            "ok",
            "pack_integrity_verified",
            path=str(pack),
            pack_version=pack_result.get("pack_version"),
            manifest_sha256=pack_result.get("manifest_sha256"),
            counts=pack_result.get("counts"),
        )
    elif mode == "consume":
        add(
            "published_knowledge_pack",
            "blocked",
            pack_result["reason"],
            path=str(pack),
            next_action=pack_result["next_action"],
        )
    else:
        add(
            "published_knowledge_pack",
            "info",
            f"not_ready_for_consumption: {pack_result['reason']}",
            path=str(pack),
            next_action="A pack is optional while privately authoring knowledge.",
        )

    optional = {
        name: importlib.util.find_spec(module) is not None
        for name, module in OPTIONAL_MODULES.items()
    }
    add("optional_dependencies", "info", "Availability only; optional extras are not required for the core CLI.", available=optional)

    if provider == "ollama":
        names, error = _ollama_models()
        if error:
            add(
                "ollama",
                "blocked",
                "local_ollama_unreachable",
                endpoint="http://127.0.0.1:11434",
                error=error,
                next_action="Start Ollama locally; this check does not download models.",
            )
        elif model and model not in (names or set()):
            add(
                "ollama_model",
                "blocked",
                "requested_model_not_installed",
                model=model,
                installed=sorted(names or set()),
                next_action="Install the model locally or choose an installed model.",
            )
        else:
            add(
                "ollama",
                "ok",
                "local_service_reachable",
                endpoint="http://127.0.0.1:11434",
                installed_models=sorted(names or set()),
            )
    elif provider == "openai-compatible":
        configured = bool(os.environ.get(api_key_env))
        add(
            "api_credentials",
            "ok" if configured else "blocked",
            "environment_variable_present" if configured else "environment_variable_missing",
            variable=api_key_env,
            next_action=None if configured else f"Set {api_key_env} in your shell; its value is never printed.",
        )
    elif model:
        add("model_selection", "blocked", "provider_required_when_model_is_selected")

    blocked = sum(item["status"] == "blocked" for item in checks)
    warnings = sum(item["status"] == "warning" for item in checks)
    return {
        "mode": mode,
        "status": "blocked" if blocked else ("warning" if warnings else "ready"),
        "usable": blocked == 0,
        "summary": {"passed": sum(item["status"] == "ok" for item in checks), "blocked": blocked, "warnings": warnings},
        "checks": checks,
        "network": "No remote requests. If --provider ollama is selected, only a GET to the local loopback Ollama tags endpoint is made; no learner content is sent.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ielts preflight",
        description="Check local prerequisites without creating files or sending learner content.",
    )
    parser.add_argument("--mode", choices=("author", "consume"), default="author")
    parser.add_argument("--db", default=".local/knowledge.sqlite3", help="Private SQLite database path (authoring only).")
    parser.add_argument("--pack", default="knowledge", help="Published Knowledge Pack directory (consumption only).")
    parser.add_argument("--provider", choices=("ollama", "openai-compatible"))
    parser.add_argument("--model", help="Explicitly selected model name.")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    args = parser.parse_args(argv)
    if args.model and not args.provider:
        parser.error("--model requires an explicit --provider")
    result = run_preflight(
        mode=args.mode,
        db=args.db,
        pack=args.pack,
        provider=args.provider,
        model=args.model,
        api_key_env=args.api_key_env,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["usable"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
