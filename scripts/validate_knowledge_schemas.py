#!/usr/bin/env python3
"""Meta-validate Knowledge Pack JSON Schemas and their cross-schema references."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
SCHEMA_NAMES = (
    "strategy.schema.json",
    "concept.schema.json",
    "relationship.schema.json",
    "learning-path.schema.json",
    "example.schema.json",
    "knowledge-pack.schema.json",
)


def fixtures():
    provenance = {"basis": "original", "public_references": []}
    review = {"content_status": "approved", "publication_status": "approved"}
    strategy = {
        "id": "speaking.answer-development", "schema_version": "1.0",
        "title": "Answer Development", "skill": "speaking",
        "summary": "Develop a direct answer.", "purpose": [], "reasoning": [],
        "steps": [], "applicability": {"question_types": [], "parts": [], "conditions": []},
        "limitations": [], "common_mistakes": [], "examples": [],
        "relationships": {"requires": [], "complements": [], "conflicts_with": [], "alternatives": []},
        "provenance": provenance, "review": review, "version": "1.0.0",
    }
    return {
        "strategy.schema.json": strategy,
        "concept.schema.json": {
            "id": "speaking.fluency", "schema_version": "1.0",
            "title": "Fluency", "definition": "The ability to communicate smoothly.",
            "related_strategies": ["speaking.answer-development"],
            "provenance": provenance, "review": review, "version": "1.0.0",
        },
        "relationship.schema.json": {
            "id": "relation.answer-fluency", "schema_version": "1.0",
            "from_id": "speaking.answer-development", "to_id": "speaking.fluency",
            "type": "illustrates", "rationale": "The strategy supports the concept.",
            "provenance": provenance, "review": review,
        },
        "example.schema.json": {
            "id": "speaking.example.direct-answer-01", "schema_version": "1.0",
            "strategy_id": "speaking.answer-development", "skill": "speaking",
            "task": "Describe a recent learning experience.",
            "content": "I recently learned to cook a new dish.",
            "strategy_application": "The opening sentence answers the question directly.",
            "learning_note": "Follow the answer with one relevant detail.",
            "provenance": provenance, "review": review, "version": "1.0.0",
        },
        "example.schema.json": {
            "id": "speaking.example.direct-answer-01", "schema_version": "1.0",
            "strategy_id": "speaking.answer-development", "skill": "speaking",
            "task": "Describe a recent learning experience.",
            "content": "I recently learned to cook a new dish.",
            "strategy_application": "The opening sentence answers the question directly.",
            "learning_note": "Follow the answer with one relevant detail.",
            "provenance": provenance, "review": review, "version": "1.0.0",
        },
        "learning-path.schema.json": {
            "id": "speaking.foundations", "schema_version": "1.0",
            "title": "Speaking Foundations", "skill": "speaking",
            "description": "A short introductory path.", "objectives": ["Answer clearly."],
            "steps": [{"order": 1, "strategy_id": "speaking.answer-development", "activity": "Practice direct answers."}],
            "prerequisites": [], "provenance": provenance, "review": review, "version": "1.0.0",
        },
        "knowledge-pack.schema.json": {
            "format": "open-ielts-knowledge-pack", "schema_version": "1.1",
            "pack_version": "1.0.0",
            "files": [
                {"path": "strategies/speaking/speaking.answer-development.json", "sha256": "0" * 64},
                {"path": "examples/speaking/speaking.example.direct-answer-01.json", "sha256": "1" * 64},
            ],
        },
    }


def main():
    schemas = {}
    for name in SCHEMA_NAMES:
        path = SCHEMA_DIR / name
        schema = json.loads(path.read_text(encoding="utf-8"))
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ValueError(f"{name}: unsupported JSON Schema dialect")
        if not isinstance(schema.get("$id"), str):
            raise ValueError(f"{name}: stable $id is required")
        Draft202012Validator.check_schema(schema)
        schemas[name] = schema

    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    sample_data = fixtures()
    for name, schema in schemas.items():
        validator = Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())
        validator.validate(sample_data[name])
    print(f"VALIDATION PASSED: {len(schemas)} Knowledge Pack schemas and cross-schema references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
