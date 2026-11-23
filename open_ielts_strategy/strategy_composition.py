"""Source-grounded comparison and playbook drafts from reviewed knowledge cards."""
from __future__ import annotations

import json
from pathlib import Path

PREFERENCE_KEYS = {"time_budget_minutes", "preferred_skills", "constraints", "practice_context"}


def _validate_preferences(preferences: dict | None) -> dict:
    prefs = {} if preferences is None else preferences
    if not isinstance(prefs, dict) or set(prefs) - PREFERENCE_KEYS:
        raise ValueError("preferences contain unsupported fields")
    if "time_budget_minutes" in prefs and (
        type(prefs["time_budget_minutes"]) is not int or not 1 <= prefs["time_budget_minutes"] <= 240
    ):
        raise ValueError("time_budget_minutes must be between 1 and 240")
    for key in ("preferred_skills", "constraints"):
        if key in prefs and (
            not isinstance(prefs[key], list) or len(prefs[key]) > 30
            or any(not isinstance(value, str) or not value.strip() or len(value) > 300 for value in prefs[key])
        ):
            raise ValueError(f"{key} must be a list of at most 30 short strings")
    if "practice_context" in prefs and (
        not isinstance(prefs["practice_context"], str) or len(prefs["practice_context"]) > 1000
    ):
        raise ValueError("practice_context must be text no longer than 1000 characters")
    return dict(prefs)


def _validate_card(card: dict) -> None:
    required = {"card_id", "source_id", "source_title", "text", "start_char", "end_char", "status"}
    if not isinstance(card, dict) or not required.issubset(card):
        raise ValueError("each card must include source-linked identity, text, offsets, and status")
    if not isinstance(card["text"], str) or not card["text"].strip():
        raise ValueError("card text must be non-empty")
    if type(card["start_char"]) is not int or type(card["end_char"]) is not int or card["start_char"] < 0 or card["end_char"] <= card["start_char"]:
        raise ValueError("card offsets are invalid")
    if card["status"] not in {"needs_review", "supported", "conflicting", "user_approved", "superseded", "rejected"}:
        raise ValueError("card review status is invalid")


def compare_recommendations(cards: list[dict], relations: list[dict] | None = None) -> dict:
    """Present source recommendations side by side; only explicit human links are conflicts."""
    if not isinstance(cards, list):
        raise ValueError("cards must be a list")
    for card in cards:
        _validate_card(card)
    relation_rows = relations or []
    ids = {card["card_id"] for card in cards}
    relevant = [
        relation for relation in relation_rows
        if relation.get("from_card_id") in ids and relation.get("to_card_id") in ids
    ]
    return {
        "items": [
            {
                "card_id": card["card_id"], "source_id": card["source_id"],
                "source_title": card["source_title"], "text": card["text"],
                "status": card["status"], "anchor": {
                    "start_char": card["start_char"], "end_char": card["end_char"],
                },
            }
            for card in cards
        ],
        "human_curated_relations": relevant,
        "automatic_conflict_detection": False,
        "interpretation": "Differences are shown without deciding which recommendation is correct.",
    }


def build_playbook(cards: list[dict], *, title: str,
                   preferences: dict | None = None) -> dict:
    """Build an ordered, cited draft; card order is supplied by the learner, not inferred."""
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise ValueError("title must be 1..200 characters")
    if not isinstance(cards, list) or not cards:
        raise ValueError("at least one selected card is required")
    for card in cards:
        _validate_card(card)
    prefs = _validate_preferences(preferences)
    steps = []
    for index, card in enumerate(cards, start=1):
        steps.append({
            "step": index,
            "instruction": card["text"],
            "source": {
                "card_id": card["card_id"], "source_id": card["source_id"],
                "source_title": card["source_title"],
                "start_char": card["start_char"], "end_char": card["end_char"],
            },
            "review_status": card["status"],
            "requires_personal_review": card["status"] != "user_approved",
        })
    return {
        "title": title.strip(), "steps": steps,
        "learner_preferences": prefs,
        "ordering": "explicit-selection-order",
        "draft": True, "claim_eligible": False,
        "limitations": [
            "This playbook composes source excerpts; it does not validate their educational correctness.",
            "User approval is a personal-use decision, not independent scientific validation.",
            "Conflicting sources are not silently reconciled.",
        ],
    }


def save_preferences(path: str | Path, preferences: dict) -> Path:
    """Store learner constraints separately from source-derived claims."""
    prefs = _validate_preferences(preferences)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = destination.with_suffix(destination.suffix + ".tmp")
    temp.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(destination)
    try:
        destination.chmod(0o600)
    except OSError:
        pass
    return destination


def load_preferences(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return _validate_preferences(data)
