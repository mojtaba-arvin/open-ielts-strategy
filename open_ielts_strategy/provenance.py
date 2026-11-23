"""Fail-closed validation for metadata-only source provenance records."""
from datetime import datetime
from urllib.parse import urlparse

LEGAL_STATUSES = {"pending", "cleared", "licensed", "restricted", "blocked", "expired", "under_review"}
PERMITTED_PUBLIC_STATUSES = {"cleared", "licensed"}
PERMISSION_FIELDS = ("private_evidence_ref", "reviewer", "reviewed_at", "notes")


def _parse_timezone_aware(value):
    """Parse an ISO-8601 timestamp only when it carries an explicit UTC offset."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp must be non-empty text")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


def validate_source_record(source):
    """Return validation errors; public availability is never treated as permission."""
    if not isinstance(source, dict):
        return ["source record must be an object"]
    errors = []
    for field in ("id", "name", "source_type", "source_url"):
        value = source.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be non-empty text")
    url = source.get("source_url")
    if isinstance(url, str) and url.strip():
        try:
            parsed = urlparse(url)
            safe_url = parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
        except ValueError:
            safe_url = False
        if not safe_url:
            errors.append("source_url must be HTTPS without embedded credentials")
    status = source.get("legal_status")
    if not isinstance(status, str) or status not in LEGAL_STATUSES:
        errors.append("invalid legal_status")
    allowed = source.get("public_content_allowed")
    if type(allowed) is not bool:
        errors.append("public_content_allowed must be boolean")
    uses = source.get("allowed_uses")
    if not isinstance(uses, list) or any(not isinstance(x, str) or not x.strip() for x in uses):
        errors.append("allowed_uses must be a list of non-empty strings")
    elif len(uses) != len(set(uses)):
        errors.append("allowed_uses must not contain duplicates")
    permission = source.get("permission_record")
    if not isinstance(permission, dict):
        errors.append("permission_record must be an object")
        permission = {}
    for field in PERMISSION_FIELDS:
        if not isinstance(permission.get(field), str):
            errors.append(f"permission_record.{field} must be text")
    if allowed is True:
        if status not in PERMITTED_PUBLIC_STATUSES:
            errors.append("public content requires cleared or licensed status")
        for field in ("private_evidence_ref", "reviewer"):
            if not isinstance(permission.get(field), str) or not permission[field].strip():
                errors.append(f"public content requires permission_record.{field}")
        try:
            _parse_timezone_aware(permission.get("reviewed_at"))
        except (TypeError, ValueError):
            errors.append("public content requires a timezone-aware permission review timestamp")
        if not isinstance(uses, list) or not uses:
            errors.append("public content requires explicit allowed_uses")
    expiry = source.get("expiry")
    if expiry is not None:
        try:
            _parse_timezone_aware(expiry)
        except (TypeError, ValueError):
            errors.append("expiry must be null or timezone-aware ISO-8601")
    return errors
