#!/usr/bin/env python3
"""Validate skill versions, case files, and source-registry defaults offline."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.composition import resolve_dependencies
from open_ielts_strategy.evaluation import validate_case
from open_ielts_strategy.provenance import validate_source_record

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def validate_repository_data(lock, registry, root=ROOT):
    """Validate parsed repository metadata without crashing on malformed JSON shapes."""
    errors = []
    if not isinstance(lock, dict):
        errors.append("skills.lock must be a JSON object")
        lock = {}
    if not isinstance(registry, dict):
        errors.append("source registry must be a JSON object")
        registry = {}

    if type(lock.get("lockfile_version")) is not int or lock.get("lockfile_version") != 1:
        errors.append("unsupported skills.lock version")

    skills = lock.get("skills")
    names = set()
    ordered_names = []
    valid_entries = []
    if not isinstance(skills, list) or not skills:
        errors.append("skills.lock skills must be a non-empty list")
        skills = []
    for index, entry in enumerate(skills):
        if not isinstance(entry, dict):
            errors.append(f"skills.lock skills[{index}] must be an object")
            continue
        valid_entries.append(entry)
        sid = entry.get("name")
        if not isinstance(sid, str) or not IDENTIFIER.fullmatch(sid):
            errors.append(f"skills.lock skills[{index}] has an invalid skill name")
            continue
        if sid in names:
            errors.append(f"missing/duplicate skill: {sid}")
            continue
        names.add(sid)
        ordered_names.append(sid)

        version = entry.get("version")
        valid_version = isinstance(version, str) and SEMVER.fullmatch(version) is not None
        if not valid_version:
            errors.append(f"{sid}: invalid SemVer")

        skill = root / "skills" / sid / "SKILL.md"
        cases = root / "skills" / sid / "evals" / "cases.json"
        if not skill.is_file():
            errors.append(f"missing {skill.relative_to(root)}")
        if not cases.is_file():
            errors.append(f"missing {cases.relative_to(root)}")
        if skill.is_file() and valid_version:
            body = skill.read_text(encoding="utf-8")
            if not body.startswith("---\\n") or "\\n---\\n" not in body[4:]:
                errors.append(f"{sid}: invalid frontmatter fence")
            else:
                fm = body.split("---", 2)[1]
                for field in ("name:", "description:", "license:", "version:"):
                    if field not in fm:
                        errors.append(f"{sid}: frontmatter missing {field}")
                if f"version: {version}" not in fm:
                    errors.append(f"{sid}: version mismatch")
        if cases.is_file():
            try:
                data = json.loads(cases.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{sid}: invalid evaluation JSON: {exc}")
                data = None
            if not isinstance(data, list) or not data:
                errors.append(f"{sid}: evaluation cases must be a non-empty JSON array")
            else:
                ids = set()
                for case_index, case in enumerate(data):
                    for error in validate_case(case):
                        errors.append(f"{sid}: case[{case_index}]: {error}")
                    if isinstance(case, dict):
                        case_id = case.get("id")
                        if isinstance(case_id, str) and case_id.strip():
                            if case_id in ids:
                                errors.append(f"{sid}: duplicate eval ID: {case_id}")
                            ids.add(case_id)

    try:
        resolve_dependencies(ordered_names, valid_entries)
    except (TypeError, ValueError) as exc:
        errors.append(f"skills.lock dependency graph: {exc}")

    sources = registry.get("sources")
    source_ids = set()
    if not isinstance(sources, list):
        errors.append("source registry sources must be a list")
        sources = []
    for index, source in enumerate(sources):
        errors.extend(
            f"source[{index}]: {error}" for error in validate_source_record(source)
        )
        if not isinstance(source, dict):
            continue
        sid = source.get("id")
        if not isinstance(sid, str) or not IDENTIFIER.fullmatch(sid):
            errors.append(f"source[{index}] has an invalid source id")
            continue
        if sid in source_ids:
            errors.append(f"missing/duplicate source id: {sid}")
        source_ids.add(sid)

    return errors, len(names), len(source_ids)


def main():
    try:
        lock = json.loads((ROOT / "skills.lock").read_text(encoding="utf-8"))
        registry = json.loads((ROOT / "registry/sources.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"VALIDATION FAILED\\n- unable to read repository metadata: {exc}")
        return 1

    errors, skill_count, source_count = validate_repository_data(lock, registry)
    if errors:
        print("VALIDATION FAILED\\n" + "\\n".join("- " + error for error in errors))
        return 1
    print(f"VALIDATION PASSED: {skill_count} skill(s), {source_count} source record(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
