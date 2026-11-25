"""Human-gated promotion of private strategy drafts to Pack-ready candidates."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .filesystem_security import ensure_private_directory
from .knowledge_pack import _validate_strategy
from .knowledge_pipeline import assert_items_publishable

RIGHTS_TO_PROVENANCE = {
    "self_authored": "original",
    "independently_authored": "independently_authored",
    "public_domain": "public_domain",
    "permission_confirmed": "permissioned",
}


class StrategyPromotionError(ValueError):
    """Raised when a draft is not eligible for human-confirmed promotion."""


def _write_private_json(path: Path, value: dict) -> bytes:
    ensure_private_directory(path.parent)
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return payload


def promote_strategy_draft(
    store,
    draft_path: str | Path,
    destination: str | Path,
    *,
    reviewer: str,
    review_note: str,
    confirm_content_review: bool,
    receipt_dir: str | Path = ".local/strategy-drafts/promotions",
) -> dict:
    """Promote only after explicit strategy review and persisted source publication approvals.

    The model cannot set provenance or approval. Provenance is derived from
    publication-review rows for every mapped semantic item. Mixed rights bases
    fail closed because one public strategy record has one provenance basis.
    """
    if confirm_content_review is not True:
        raise StrategyPromotionError("promotion requires --confirm-content-review")
    if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 200:
        raise StrategyPromotionError("reviewer must be non-empty text no longer than 200 characters")
    if not isinstance(review_note, str) or not review_note.strip() or len(review_note) > 4_000:
        raise StrategyPromotionError("a human content-review note is required (1..4000 characters)")

    source_path = Path(draft_path).expanduser().resolve(strict=True)
    if not source_path.is_file() or source_path.stat().st_size > 256_000:
        raise StrategyPromotionError("draft must be a regular file no larger than 256 KB")
    try:
        envelope = json.loads(source_path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StrategyPromotionError("private draft must contain valid UTF-8 JSON") from exc

    expected_keys = {
        "draft_format", "draft_version", "draft_id", "status", "strategy",
        "private_source", "generation", "review",
    }
    if not isinstance(envelope, dict) or set(envelope) != expected_keys:
        raise StrategyPromotionError("private draft envelope fields are invalid")
    if envelope["draft_format"] != "open-ielts-private-strategy-draft" or envelope["draft_version"] != 1:
        raise StrategyPromotionError("unsupported private strategy draft format")
    if envelope["status"] != "needs_human_review":
        raise StrategyPromotionError("only a needs_human_review draft can be promoted")
    if envelope["review"] != {
        "content_status": "pending", "publication_status": "pending", "approved": False,
    }:
        raise StrategyPromotionError("draft review state was changed; refusing to infer approval")

    private_source = envelope["private_source"]
    if not isinstance(private_source, dict):
        raise StrategyPromotionError("private source mapping is missing")
    source_id = private_source.get("source_id")
    item_ids = private_source.get("semantic_item_ids")
    if (not isinstance(source_id, str) or not source_id.startswith("src_")
            or not isinstance(item_ids, list) or not 1 <= len(item_ids) <= 100
            or any(not isinstance(value, str) or not value.startswith("sitem_") for value in item_ids)
            or len(item_ids) != len(set(item_ids))):
        raise StrategyPromotionError("private source-item mapping is invalid")

    try:
        approvals = assert_items_publishable(store, item_ids)
    except (ValueError, KeyError) as exc:
        raise StrategyPromotionError("all mapped semantic items need independent content and publication approval") from exc
    placeholders = ",".join("?" for _ in item_ids)
    rows = store._connection.execute(
        f"SELECT item_id, source_id FROM semantic_items WHERE item_id IN ({placeholders})",
        tuple(item_ids),
    ).fetchall()
    if len(rows) != len(item_ids) or any(row["source_id"] != source_id for row in rows):
        raise StrategyPromotionError("every mapped semantic item must belong to the draft's recorded source")

    rights_bases = {row["rights_basis"] for row in approvals}
    if len(rights_bases) != 1:
        raise StrategyPromotionError("mapped items have mixed rights bases; split the strategy or resolve rights independently")
    rights_basis = next(iter(rights_bases))
    provenance_basis = RIGHTS_TO_PROVENANCE.get(rights_basis)
    if provenance_basis is None:
        raise StrategyPromotionError("mapped items do not have a supported publication rights basis")

    strategy = envelope["strategy"]
    if not isinstance(strategy, dict) or "provenance" in strategy or "review" in strategy:
        raise StrategyPromotionError("model draft must not supply provenance or approval fields")
    candidate = dict(strategy)
    candidate["provenance"] = {"basis": provenance_basis, "public_references": []}
    candidate["review"] = {
        "content_status": "approved",
        "publication_status": "approved",
    }
    _validate_strategy(candidate, "<private-strategy-draft>")

    output_path = Path(destination).expanduser().absolute()
    if output_path.exists():
        raise StrategyPromotionError("destination already exists; promotion never overwrites")
    receipt_id = envelope["draft_id"]
    if not isinstance(receipt_id, str) or not receipt_id.startswith("draft_"):
        raise StrategyPromotionError("draft ID is invalid")
    receipt_path = Path(receipt_dir).expanduser() / f"{receipt_id}.promotion.json"
    if receipt_path.exists():
        raise StrategyPromotionError("a promotion receipt already exists for this draft")

    candidate_payload = (json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_private_json(output_path, candidate)
        receipt = {
            "receipt_format": "open-ielts-strategy-promotion",
            "receipt_version": 1,
            "draft_id": receipt_id,
            "strategy_id": candidate["id"],
            "source_id": source_id,
            "semantic_item_ids": item_ids,
            "rights_basis": rights_basis,
            "provenance_basis": provenance_basis,
            "content_reviewer": reviewer.strip(),
            "content_review_note": review_note.strip(),
            "content_reviewed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "candidate_path": str(output_path),
            "candidate_sha256": hashlib.sha256(candidate_payload).hexdigest(),
        }
        _write_private_json(receipt_path, receipt)
    except Exception:
        try:
            output_path.unlink()
        except OSError:
            pass
        raise

    return {
        "strategy_id": candidate["id"],
        "candidate_path": str(output_path),
        "promotion_receipt": str(receipt_path),
        "status": "pack_candidate_requires_builder_confirmation",
        "provenance_basis": provenance_basis,
        "mapped_item_count": len(item_ids),
        "source_item_args": [f"--source-item {candidate['id']}={item_id}" for item_id in item_ids],
        "published": False,
    }
