#!/usr/bin/env python3
"""Validate skill versions, case files, and source-registry defaults offline."""
import json, re, sys
from pathlib import Path
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
            data=json.loads(cases.read_text())
            ids=[c.get("id") for c in data]
            if not data or len(ids)!=len(set(ids)): errors.append(f"{sid}: empty or duplicate eval IDs")
    source_ids=set()
    for src in registry.get("sources",[]):
        sid=src.get("id")
        if not sid or sid in source_ids: errors.append(f"missing/duplicate source id: {sid}"); continue
        source_ids.add(sid)
        if src.get("legal_status") not in {"pending","cleared","licensed","restricted","blocked","expired","under_review"}: errors.append(f"{sid}: invalid legal_status")
        if src.get("public_content_allowed") not in (False, True): errors.append(f"{sid}: public_content_allowed must be boolean")
        if src.get("public_content_allowed") is True:
            record=src.get("permission_record") or {}
            if src.get("legal_status") not in {"cleared","licensed"} or not record.get("private_evidence_ref") or not src.get("allowed_uses"):
                errors.append(f"{sid}: public content requires cleared/licensed status, private evidence, and explicit allowed_uses")
    if errors:
        print("VALIDATION FAILED\n"+"\n".join("- "+e for e in errors)); return 1
    print(f"VALIDATION PASSED: {len(names)} skill(s), {len(source_ids)} source record(s)"); return 0

if __name__=="__main__": sys.exit(main())
