#!/usr/bin/env python3
"""Validate skill versions, case files, and source-registry defaults offline."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from open_ielts_strategy.composition import resolve_dependencies
from open_ielts_strategy.evaluation import validate_case
from open_ielts_strategy.provenance import validate_source_record
ROOT=Path(__file__).resolve().parents[1]
SEMVER=re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

def main():
    errors=[]
    lock=json.loads((ROOT/"skills.lock").read_text())
    registry=json.loads((ROOT/"registry/sources.json").read_text())
    if lock.get("lockfile_version") != 1: errors.append("unsupported skills.lock version")
    names=set()
    for entry in lock.get("skills",[]):
        sid, version=entry.get("name"), entry.get("version")
        if not sid or sid in names: errors.append(f"missing/duplicate skill: {sid}"); continue
        names.add(sid)
        if not SEMVER.fullmatch(version or ""): errors.append(f"{sid}: invalid SemVer")
        skill=ROOT/"skills"/sid/"SKILL.md"
        cases=ROOT/"skills"/sid/"evals/cases.json"
        if not skill.is_file(): errors.append(f"missing {skill.relative_to(ROOT)}")
        if not cases.is_file(): errors.append(f"missing {cases.relative_to(ROOT)}")
        if skill.is_file():
            body=skill.read_text()
            if not body.startswith("---\n") or "\n---\n" not in body[4:]: errors.append(f"{sid}: invalid frontmatter fence")
            else:
                fm=body.split("---",2)[1]
                for field in ("name:","description:","license:","version:"):
                    if field not in fm: errors.append(f"{sid}: frontmatter missing {field}")
                if f"version: {version}" not in fm: errors.append(f"{sid}: version mismatch")
        if cases.is_file():
            try:
                data=json.loads(cases.read_text())
            except json.JSONDecodeError as exc:
                errors.append(f"{sid}: invalid evaluation JSON: {exc}")
                data=None
            if not isinstance(data,list) or not data:
                errors.append(f"{sid}: evaluation cases must be a non-empty JSON array")
            else:
                ids=set()
                for index, case in enumerate(data):
                    for error in validate_case(case):
                        errors.append(f"{sid}: case[{index}]: {error}")
                    if isinstance(case,dict):
                        case_id=case.get("id")
                        if isinstance(case_id,str) and case_id.strip():
                            if case_id in ids: errors.append(f"{sid}: duplicate eval ID: {case_id}")
                            ids.add(case_id)
    try:
        resolve_dependencies(list(names), lock.get("skills", []))
    except ValueError as exc:
        errors.append(f"skills.lock dependency graph: {exc}")
    source_ids=set()
    for src in registry.get("sources",[]):
        sid=src.get("id") if isinstance(src, dict) else None
        if not sid or sid in source_ids: errors.append(f"missing/duplicate source id: {sid}"); continue
        source_ids.add(sid)
        errors.extend(f"{sid}: {error}" for error in validate_source_record(src))
    if errors:
        print("VALIDATION FAILED\n"+"\n".join("- "+e for e in errors)); return 1
    print(f"VALIDATION PASSED: {len(names)} skill(s), {len(source_ids)} source record(s)"); return 0

if __name__=="__main__": sys.exit(main())
