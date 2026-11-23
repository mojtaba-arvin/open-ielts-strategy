"""Private, local human-review and calibration for generated practice answers.

This module measures reviewer agreement and rubric observations. It does not
predict IELTS bands, certify examiner equivalence, or infer learner outcomes.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

RUBRIC = {
    "task_relevance": "Addresses the learner's actual task",
    "evidence_grounding": "Claims are supported by cited published strategy IDs",
    "clarity": "Explanation is understandable and coherent",
    "actionability": "Practice advice is specific and usable",
    "factual_safety": "Avoids unsupported IELTS rules, scores, and guarantees",
}
_ALLOWED = {key: range(1, 6) for key in RUBRIC}


class PracticeReviewStore:
    """SQLite store for private human annotations; never part of a public pack."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS practice_review_items (
                item_id TEXT PRIMARY KEY,
                pack_version TEXT NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                output_sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS practice_reviews (
                item_id TEXT NOT NULL REFERENCES practice_review_items(item_id) ON DELETE CASCADE,
                reviewer_id TEXT NOT NULL,
                rubric_json TEXT NOT NULL,
                rationale TEXT NOT NULL DEFAULT '',
                reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(item_id, reviewer_id)
            );
        """)
        self.connection.commit()

    def close(self):
        self.connection.close()

    def register_output(self, item_id: str, *, pack_version: str,
                        manifest_sha256: str, output_sha256: str):
        for value, name in ((item_id, "item_id"), (pack_version, "pack_version"),
                            (manifest_sha256, "manifest_sha256"), (output_sha256, "output_sha256")):
            if not isinstance(value, str) or not value.strip() or len(value) > 200:
                raise ValueError(f"{name} must be non-empty bounded text")
        if not re.fullmatch(r"[0-9a-f]{64}", manifest_sha256) or not re.fullmatch(r"[0-9a-f]{64}", output_sha256):
            raise ValueError("manifest_sha256 and output_sha256 must be lowercase SHA-256 hex digests")
        try:
            self.connection.execute(
                "INSERT INTO practice_review_items(item_id,pack_version,manifest_sha256,output_sha256) VALUES(?,?,?,?)",
                (item_id, pack_version, manifest_sha256, output_sha256),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("review item already exists or violates the local review schema") from exc

    def submit_review(self, item_id: str, reviewer_id: str, scores: dict[str, int], *, rationale: str = ""):
        if not isinstance(reviewer_id, str) or not reviewer_id.strip() or len(reviewer_id) > 120:
            raise ValueError("reviewer_id must be non-empty bounded text")
        if not isinstance(scores, dict) or set(scores) != set(RUBRIC):
            raise ValueError("scores must contain every required rubric dimension exactly once")
        for key, value in scores.items():
            if type(value) is not int or value not in _ALLOWED[key]:
                raise ValueError(f"{key} must be an integer from 1 to 5")
        if not isinstance(rationale, str) or len(rationale) > 4000:
            raise ValueError("rationale must be text of at most 4000 characters")
        try:
            cursor = self.connection.execute(
                "INSERT INTO practice_reviews(item_id,reviewer_id,rubric_json,rationale) VALUES(?,?,?,?)",
                (item_id, reviewer_id, json.dumps(scores, sort_keys=True), rationale),
            )
            self.connection.commit()
            return cursor.rowcount == 1
        except sqlite3.IntegrityError as exc:
            raise ValueError("unknown review item or reviewer has already submitted a rating") from exc

    def calibration_report(self) -> dict[str, Any]:
        rows = self.connection.execute(
            "SELECT item_id, reviewer_id, rubric_json FROM practice_reviews ORDER BY item_id, reviewer_id"
        ).fetchall()
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            grouped.setdefault(row["item_id"], []).append(json.loads(row["rubric_json"]))
        dimensions = {}
        for dimension in RUBRIC:
            pairs = []
            exact = total = 0
            for reviews in grouped.values():
                for i in range(len(reviews)):
                    for j in range(i + 1, len(reviews)):
                        a, b = reviews[i][dimension], reviews[j][dimension]
                        pairs.append((a, b))
                        exact += a == b
                        total += 1
            if not pairs:
                dimensions[dimension] = {"paired_reviews": 0, "exact_agreement": None, "weighted_kappa": None}
                continue
            observed = sum(1 - ((a - b) / 4) ** 2 for a, b in pairs) / len(pairs)
            left = [a for a, _ in pairs]
            right = [b for _, b in pairs]
            expected = 0.0
            for score_a in range(1, 6):
                for score_b in range(1, 6):
                    pa = left.count(score_a) / len(left)
                    pb = right.count(score_b) / len(right)
                    expected += pa * pb * (1 - ((score_a - score_b) / 4) ** 2)
            kappa = (observed - expected) / (1 - expected) if expected < 1 else None
            dimensions[dimension] = {
                "paired_reviews": len(pairs),
                "exact_agreement": round(exact / total, 4),
                "weighted_kappa": round(kappa, 4) if kappa is not None else None,
            }
        return {
            "reviewed_item_count": len(grouped),
            "review_count": len(rows),
            "reviewer_agreement": dimensions,
            "rubric": RUBRIC,
            "interpretation": "Descriptive reviewer agreement only; not examiner equivalence, IELTS band calibration, or educational-effectiveness evidence.",
        }
