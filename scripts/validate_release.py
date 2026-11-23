"""Fail-closed release claim register validation; no model or network access."""
import ast
import os
import re
import tomllib
from datetime import datetime
from pathlib import Path

CLAIM_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")

def validate_claim_registry(data):
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data.get("schema_version") != 1:
        return ["claim registry must be an object with schema_version 1"]
    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        return ["claims must be a non-empty list"]
    errors = []
    seen = set()
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{prefix} must be an object")
            continue
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not CLAIM_ID.fullmatch(claim_id):
            errors.append(f"{prefix}.id must be a canonical claim identifier")
        elif claim_id in seen:
            errors.append(f"duplicate claim id: {claim_id}")
        else:
            seen.add(claim_id)
        if not isinstance(claim.get("description"), str) or not claim["description"].strip():
            errors.append(f"{prefix}.description must be non-empty text")
        status = claim.get("status")
        if not isinstance(status, str) or status not in {"not_established", "validated", "retired"}:
            errors.append(f"{prefix}.status is invalid")
        allowed = claim.get("public_claim_allowed")
        if type(allowed) is not bool:
            errors.append(f"{prefix}.public_claim_allowed must be boolean")
            continue
        evidence = claim.get("evidence_refs")
        if not isinstance(evidence, list) or any(not isinstance(item, str) or not item.strip() for item in evidence):
            errors.append(f"{prefix}.evidence_refs must be a list of non-empty references")
            evidence = []
        if allowed:
            if status != "validated":
                errors.append(f"{prefix}: public claims require validated status")
            if not evidence:
                errors.append(f"{prefix}: public claims require evidence_refs")
            for field in ("reviewer", "method", "scope"):
                if not isinstance(claim.get(field), str) or not claim[field].strip():
                    errors.append(f"{prefix}: public claims require {field}")
            sample_count = claim.get("sample_count")
            if type(sample_count) is not int or sample_count < 1:
                errors.append(f"{prefix}: public claims require positive integer sample_count")
            reviewed_at = claim.get("reviewed_at")
            try:
                parsed = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    raise ValueError("timezone required")
            except (AttributeError, TypeError, ValueError):
                errors.append(f"{prefix}: public claims require timezone-aware reviewed_at")
    return errors


def validate_release_preflight(root: Path, release_tag: str | None = None) -> list[str]:
    """Validate package metadata, CLI entry points, licensing notices, and tag/version alignment."""
    root = Path(root)
    errors = []
    pyproject_path = root / "pyproject.toml"
    try:
        project_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"unable to read pyproject.toml: {exc}"]

    project = project_data.get("project")
    if not isinstance(project, dict):
        return ["pyproject.toml must declare a [project] table"]
    version = project.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version):
        errors.append("project.version must be canonical SemVer MAJOR.MINOR.PATCH")
        version = None

    init_path = root / "open_ielts_strategy" / "__init__.py"
    try:
        init_text = init_path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"package __init__.py is missing or unreadable: {exc}")
    else:
        version_line = next(
            (line for line in init_text.splitlines() if line.strip().startswith("__version__")),
            None,
        )
        if version_line is None or "=" not in version_line:
            errors.append("package __init__.py must declare __version__")
        else:
            declared_version = version_line.split("=", 1)[1].strip().strip("'\\\"")
            if version is not None and declared_version != version:
                errors.append("package __version__ does not match project.version")

    if release_tag is not None:
        if not isinstance(release_tag, str) or not re.fullmatch(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", release_tag):
            errors.append("release tag must be canonical vMAJOR.MINOR.PATCH")
        elif version is not None and release_tag != f"v{version}":
            errors.append(f"release tag {release_tag} does not match project.version v{version}")

    readme = project.get("readme", "README.md")
    readme_path = readme.get("file") if isinstance(readme, dict) else readme
    if not isinstance(readme_path, str) or not (root / readme_path).is_file():
        errors.append("project.readme must point to an existing file")

    license_value = project.get("license")
    license_text = license_value.get("text") if isinstance(license_value, dict) else license_value
    if license_text != "MIT":
        errors.append("project.license must explicitly declare MIT for software code")
    for filename in ("LICENSE", "LICENSE-CONTENT", "NOTICE"):
        if not (root / filename).is_file():
            errors.append(f"required licensing notice is missing: {filename}")
    license_files = project.get("license-files")
    if not isinstance(license_files, list) or not {
        "LICENSE", "LICENSE-CONTENT", "NOTICE"
    }.issubset(set(license_files)):
        errors.append("project.license-files must package LICENSE, LICENSE-CONTENT, and NOTICE")
    if (root / "LICENSE").is_file() and "MIT License" not in (root / "LICENSE").read_text(encoding="utf-8"):
        errors.append("LICENSE must contain the MIT software license")
    if (root / "NOTICE").is_file():
        notice = (root / "NOTICE").read_text(encoding="utf-8")
        if "LICENSE-CONTENT" not in notice:
            errors.append("NOTICE must identify the separate content license notice")

    scripts = project.get("scripts")
    if not isinstance(scripts, dict) or not scripts:
        errors.append("project.scripts must declare at least one CLI entry point")
    else:
        for script_name, target in sorted(scripts.items()):
            if not isinstance(target, str) or ":" not in target:
                errors.append(f"CLI entry point {script_name} must use module:callable syntax")
                continue
            module_name, callable_name = target.split(":", 1)
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", module_name) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", callable_name):
                errors.append(f"CLI entry point {script_name} has an invalid target")
                continue
            module_path = root.joinpath(*module_name.split(".")).with_suffix(".py")
            try:
                tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
            except (OSError, SyntaxError) as exc:
                errors.append(f"CLI entry point {script_name} target is unreadable: {exc}")
                continue
            defined = {
                node.name for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            }
            if callable_name not in defined:
                errors.append(f"CLI entry point {script_name} targets missing callable {target}")
    return errors


def main():
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "docs/release-claims.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"RELEASE GATE FAILED: {exc}")
        return 1
    errors = validate_claim_registry(data)
    errors.extend(validate_release_preflight(Path(__file__).resolve().parents[1], os.environ.get("RELEASE_TAG")))
    if errors:
        print("RELEASE GATE FAILED\n" + "\n".join("- " + error for error in errors))
        return 1
    print(f"RELEASE GATE PASSED: {len(data['claims'])} claim(s); unsupported public claims remain disabled")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
