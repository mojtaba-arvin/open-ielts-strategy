"""Fail-closed release claim register validation; no model or network access."""
import re
from datetime import datetime

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
    if errors:
        print("RELEASE GATE FAILED\n" + "\n".join("- " + error for error in errors))
        return 1
    print(f"RELEASE GATE PASSED: {len(data['claims'])} claim(s); unsupported public claims remain disabled")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
