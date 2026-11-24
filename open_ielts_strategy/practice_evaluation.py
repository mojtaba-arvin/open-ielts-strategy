"""Private, local human-review and calibration for generated practice answers.

This module measures reviewer agreement and rubric observations. It does not
predict IELTS bands, certify examiner equivalence, or infer learner outcomes.
"""
from __future__ import annotations

import json
import os
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


def _ensure_private_parent(directory: Path) -> None:
    """Create missing database directories as private without changing existing ones."""
    missing = []
    current = directory
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            break
        current = current.parent

    for candidate in reversed(missing):
        try:
            candidate.mkdir(mode=0o700)
        except FileExistsError:
            # A concurrent creator owns this directory; do not change its mode.
            continue
        try:
            candidate.chmod(0o700)
        except OSError:
            pass


class PracticeReviewStore:
    """SQLite store for private human annotations; never part of a public pack."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            db_path = Path(self.path).expanduser()
            _ensure_private_parent(db_path.parent)
            self.path = str(db_path)
        self.connection = sqlite3.connect(self.path)
        if self.path != ":memory:":
            os.chmod(self.path, 0o600)
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
        grouped: dict[str, dict[str, dict]] = {}
        for row in rows:
            grouped.setdefault(row["item_id"], {})[row["reviewer_id"]] = json.loads(row["rubric_json"])

        dimensions = {}
        for dimension in RUBRIC:
            pair_samples: dict[tuple[str, str], list[tuple[int, int]]] = {}
            exact = total = 0
            for reviews in grouped.values():
                reviewers = sorted(reviews)
                for index, reviewer_a in enumerate(reviewers):
                    for reviewer_b in reviewers[index + 1:]:
                        a = reviews[reviewer_a][dimension]
                        b = reviews[reviewer_b][dimension]
                        pair_samples.setdefault((reviewer_a, reviewer_b), []).append((a, b))
                        exact += a == b
                        total += 1

            pair_kappas = []
            for samples in pair_samples.values():
                left = [a for a, _ in samples]
                right = [b for _, b in samples]
                observed = sum(1 - ((a - b) / 4) ** 2 for a, b in samples) / len(samples)
                expected = 0.0
                for score_a in range(1, 6):
                    for score_b in range(1, 6):
                        pa = left.count(score_a) / len(left)
                        pb = right.count(score_b) / len(right)
                        expected += pa * pb * (1 - ((score_a - score_b) / 4) ** 2)
                if expected < 1:
                    pair_kappas.append(((observed - expected) / (1 - expected), len(samples)))

            weighted_kappa = (
                sum(kappa * sample_count for kappa, sample_count in pair_kappas)
                / sum(sample_count for _, sample_count in pair_kappas)
                if pair_kappas else None
            )
            dimensions[dimension] = {
                "paired_reviews": total,
                "reviewer_pair_count": len(pair_samples),
                "weighted_kappa_pair_count": len(pair_kappas),
                "exact_agreement": round(exact / total, 4) if total else None,
                "weighted_kappa": round(weighted_kappa, 4) if weighted_kappa is not None else None,
            }

        return {
            "reviewed_item_count": len(grouped),
            "review_count": len(rows),
            "reviewer_agreement": dimensions,
            "rubric": RUBRIC,
            "interpretation": "Pairwise quadratic-weighted Cohen kappa is averaged across reviewer pairs, weighted by their shared item count. Descriptive agreement only; not examiner equivalence, IELTS band calibration, or educational-effectiveness evidence.",
        }
