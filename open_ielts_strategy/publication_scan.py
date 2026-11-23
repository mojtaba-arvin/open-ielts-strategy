"""Local publication leakage checks; source text never appears in reports."""
from __future__ import annotations

import re
from typing import Any

MIN_EXACT_MATCH_CHARS = 48
MAX_SCAN_TEXT_CHARS = 10_000_000
MAX_SOURCE_CHARS = 1_000_000
MAX_TOTAL_SOURCE_CHARS = 5_000_000
_HASH_MASK = (1 << 64) - 1
_HASH_BASE = 257
_SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "openai_style_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "bearer_credential": re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{24,}"),
}


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).casefold().strip()


def _rolling_hashes(value: str, width: int):
    if len(value) < width:
        return
    power = pow(_HASH_BASE, width - 1, 1 << 64)
    current = 0
    for char in value[:width]:
        current = (current * _HASH_BASE + ord(char) + 1) & _HASH_MASK
    yield 0, current
    for start in range(1, len(value) - width + 1):
        outgoing = ord(value[start - 1]) + 1
        incoming = ord(value[start + width - 1]) + 1
        current = ((current - outgoing * power) * _HASH_BASE + incoming) & _HASH_MASK
        yield start, current


def scan_publication_leaks(payloads: list[str], private_sources: list[dict[str, Any]], *,
                           min_match_chars: int = MIN_EXACT_MATCH_CHARS) -> dict:
    """Find long normalized exact overlaps and common secret patterns.

    This is a bounded heuristic. Source windows are indexed with a rolling hash,
    while the public payload is scanned at every character offset. Reports
    contain private source IDs/offsets for local review, never matched text.
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

    stride = max(8, min_match_chars // 4)
    source_index: dict[int, list[tuple[str, int, str]]] = {}
    total_source_chars = 0
    for source in private_sources:
        source_id, body = source.get("source_id"), source.get("text")
        if not isinstance(source_id, str) or not isinstance(body, str) or not body:
            continue
        if len(body) > MAX_SOURCE_CHARS:
            raise ValueError("a private source exceeds the publication scan size limit")
        total_source_chars += len(body)
        if total_source_chars > MAX_TOTAL_SOURCE_CHARS:
            raise ValueError("private source text exceeds the total publication scan size limit")
        normalized_source = _normalize(body)
        if len(normalized_source) < min_match_chars:
            continue
        offsets = list(range(0, len(normalized_source) - min_match_chars + 1, stride))
        final_offset = len(normalized_source) - min_match_chars
        if offsets[-1] != final_offset:
            offsets.append(final_offset)
        for offset in offsets:
            span = normalized_source[offset:offset + min_match_chars]
            hashed = next((value for start, value in _rolling_hashes(span, min_match_chars) if start == 0), None)
            source_index.setdefault(hashed, []).append((source_id, offset, span))

    exact_matches: dict[str, list[dict]] = {}
    if source_index and len(normalized_payload) >= min_match_chars:
        for payload_offset, hashed in _rolling_hashes(normalized_payload, min_match_chars):
            candidates = source_index.get(hashed)
            if not candidates:
                continue
            public_window = normalized_payload[payload_offset:payload_offset + min_match_chars]
            for source_id, source_offset, source_window in candidates:
                if public_window != source_window:
                    continue
                matches = exact_matches.setdefault(source_id, [])
                entry = {"source_offset": source_offset, "payload_offset": payload_offset,
                         "match_length": min_match_chars}
                if entry not in matches and len(matches) < 100:
                    matches.append(entry)

    exact_findings = [
        {"source_id": source_id, "match_count": len(matches), "matches": matches}
        for source_id, matches in sorted(exact_matches.items()) if matches
    ]
    return {
        "passed": not exact_findings and not secret_findings,
        "exact_source_overlaps": exact_findings,
        "secret_findings": secret_findings,
        "matched_text_included": False,
        "source_bodies_included": False,
        "method": "normalized-exact-window-heuristic",
        "min_match_chars": min_match_chars,
        "window_stride": stride,
        "not_legal_clearance": True,
    }
