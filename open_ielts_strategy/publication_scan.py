"""Local publication leakage checks; source text never appears in reports."""
from __future__ import annotations

import re
from typing import Any

MIN_EXACT_MATCH_CHARS = 48
MAX_SCAN_TEXT_CHARS = 50_000_000
_SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "openai_style_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "bearer_credential": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{24,}"),
}


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).casefold().strip()


def scan_publication_leaks(payloads: list[str], private_sources: list[dict[str, Any]], *,
                           min_match_chars: int = MIN_EXACT_MATCH_CHARS) -> dict:
    """Find long exact source overlaps and common secret patterns.

    Reports contain source IDs and offsets for the private local reviewer, but
    never include matched text, source bodies, tokens, or payload excerpts.
    """
    if not isinstance(payloads, list) or any(not isinstance(value, str) for value in payloads):
        raise ValueError("payloads must be a list of text values")
    if not isinstance(private_sources, list) or any(not isinstance(value, dict) for value in private_sources):
        raise ValueError("private_sources must be a list of source records")
    if type(min_match_chars) is not int or not 32 <= min_match_chars <= 512:
        raise ValueError("min_match_chars must be between 32 and 512")
    combined = "\n".join(payloads)
    if len(combined) > MAX_SCAN_TEXT_CHARS:
        raise ValueError("publication scan payload exceeds size limit")
    normalized_payload = _normalize(combined)
    secret_findings = [
        {"kind": name, "count": len(pattern.findall(combined))}
        for name, pattern in _SECRET_PATTERNS.items()
        if pattern.search(combined)
    ]
    exact_findings = []
    for source in private_sources:
        source_id, body = source.get("source_id"), source.get("text")
        if not isinstance(source_id, str) or not isinstance(body, str) or not body:
            continue
        normalized_source = _normalize(body)
        if len(normalized_source) < min_match_chars:
            continue
        matches = []
        seen = set()
        step = max(16, min_match_chars // 2)
        for offset in range(0, len(normalized_source) - min_match_chars + 1, step):
            span = normalized_source[offset:offset + min_match_chars]
            if span in seen:
                continue
            seen.add(span)
            if span in normalized_payload:
                matches.append({"source_offset": offset, "match_length": min_match_chars})
                if len(matches) >= 100:
                    break
        if matches:
            exact_findings.append({
                "source_id": source_id,
                "match_count": len(matches),
                "matches": matches,
            })
    return {
        "passed": not exact_findings and not secret_findings,
        "exact_source_overlaps": exact_findings,
        "secret_findings": secret_findings,
        "matched_text_included": False,
        "source_bodies_included": False,
    }
