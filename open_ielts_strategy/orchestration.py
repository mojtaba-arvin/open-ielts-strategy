"""Deterministic MVP semantic routing and conflict resolution."""
import math
import re
from datetime import datetime, timezone

WRITING = "ielts-writing-feedback"


def route(text):
    normalized = text.lower()
    if re.search(r"\b(speaking|listening|reading)\b", normalized):
        return {"skill_id": None, "confidence": 0.98, "reason": "non-writing IELTS task"}
    task = bool(re.search(
        r"\b(task\s*[12]|task one|task two|chart|graph|table|essay|opinion|discuss both)\b",
        normalized,
    ))
    draft = bool(re.search(
        r"\b(essay|draft|my writing|my response|report|paragraph)\b",
        normalized,
    ))
    if task and draft:
        return {
            "skill_id": WRITING,
            "confidence": 0.94,
            "reason": "IELTS writing task and learner draft detected",
        }
    if draft and "ielts" in normalized:
        return {
            "skill_id": WRITING,
            "confidence": 0.72,
            "reason": "IELTS learner draft; clarify task",
        }
    return {"skill_id": None, "confidence": 0.35, "reason": "insufficient evidence"}


def resolve_conflicts(candidates):
    if not candidates:
        return None

    required = {"skill_id", "priority", "confidence", "validated_at"}
    ranked = []
    for candidate in candidates:
        if not isinstance(candidate, dict) or not required.issubset(candidate):
            raise ValueError("candidate missing conflict metadata")
        if not isinstance(candidate["skill_id"], str) or not candidate["skill_id"].strip():
            raise ValueError("skill_id must be non-empty text")
        if type(candidate["priority"]) is not int:
            raise ValueError("priority must be an integer")

        confidence = candidate["confidence"]
        if type(confidence) not in (int, float):
            raise ValueError("confidence must be a finite number between 0 and 1")
        try:
            finite_confidence = math.isfinite(confidence)
        except OverflowError:
            finite_confidence = False
        if not finite_confidence:
            raise ValueError("confidence must be a finite number between 0 and 1")
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be a finite number between 0 and 1")

        timestamp = candidate["validated_at"]
        if not isinstance(timestamp, str) or not timestamp:
            raise ValueError("validated_at must be timezone-aware ISO-8601")
        try:
            normalized_timestamp = (
                timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp
            )
            validated_at = datetime.fromisoformat(normalized_timestamp)
        except ValueError as exc:
            raise ValueError("validated_at must be timezone-aware ISO-8601") from exc
        if validated_at.tzinfo is None or validated_at.utcoffset() is None:
            raise ValueError("validated_at must be timezone-aware ISO-8601")

        try:
            validated_at_utc = validated_at.astimezone(timezone.utc)
        except OverflowError as exc:
            raise ValueError("validated_at cannot be normalized to UTC") from exc

        ranked.append((
            (candidate["priority"], confidence, validated_at_utc),
            candidate,
        ))

    best_rank = max(rank for rank, _ in ranked)
    return min(
        (candidate for rank, candidate in ranked if rank == best_rank),
        key=lambda candidate: candidate["skill_id"],
    )
