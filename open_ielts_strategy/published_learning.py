"""Mentor and Study capabilities over a published Knowledge Pack."""
from __future__ import annotations

import json
from typing import Any

from .knowledge_pack import KnowledgePack
from .publication_scan import scan_publication_leaks
from .text_generation import GenerationError, TextGenerationProvider


def get_published_learning_path(pack: KnowledgePack, path_id: str) -> dict:
    path = pack.get_learning_path(path_id)
    if path is None:
        raise KeyError(f"unknown published learning path: {path_id}")
    steps = []
    for step in sorted(path["steps"], key=lambda value: value["order"]):
        strategy = pack.get_strategy(step["strategy_id"])
        if strategy is None:
            raise ValueError(f"learning path references an unavailable strategy: {step['strategy_id']}")
        steps.append({
            **step,
            "strategy_title": strategy["title"],
            "strategy_version": strategy["version"],
            "strategy_summary": strategy["summary"],
        })
    return {
        "learning_path": path,
        "resolved_steps": steps,
        "pack_version": pack.pack_version,
        "manifest_sha256": pack.manifest_sha256,
    }


def get_published_concept(pack: KnowledgePack, concept_id: str) -> dict:
    concept = pack.get_concept(concept_id)
    if concept is None:
        raise KeyError(f"unknown published concept: {concept_id}")
    return {
        "concept": concept,
        "related_strategies": [
            pack.get_strategy(strategy_id) for strategy_id in concept["related_strategies"]
        ],
        "pack_version": pack.pack_version,
        "manifest_sha256": pack.manifest_sha256,
    }


def create_published_study_plan(pack: KnowledgePack, *, skill: str, limit: int = 5) -> dict:
    if not isinstance(skill, str) or skill not in {"speaking", "writing", "reading", "listening", "general"}:
        raise ValueError("unsupported IELTS skill")
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")
    paths = [
        get_published_learning_path(pack, item["id"])
        for item in pack.learning_paths
        if item["skill"] in {skill, "general"} or skill == "general"
    ][:limit]
    return {
        "status": "ready" if paths else "no-published-learning-path",
        "skill": skill,
        "learning_paths": paths,
        "pack_version": pack.pack_version,
        "manifest_sha256": pack.manifest_sha256,
        "note": "Study paths are curated sequences, not guaranteed score-improvement plans.",
    }


def explain_published_strategy(pack: KnowledgePack, strategy_id: str, *,
                               provider: TextGenerationProvider,
                               learner_question: str | None = None) -> dict:
    strategy = pack.get_strategy(strategy_id)
    if strategy is None:
        raise KeyError(f"unknown published strategy: {strategy_id}")
    if learner_question is not None and (
        not isinstance(learner_question, str) or len(learner_question) > 2000
    ):
        raise ValueError("learner_question must be text no longer than 2000 characters")
    context = {
        "strategy": strategy,
        "learner_question": learner_question,
        "pack_version": pack.pack_version,
        "manifest_sha256": pack.manifest_sha256,
    }
    prompt = (
        "Act as an IELTS learning mentor. Explain the supplied approved strategy accurately and simply. "
        "Use only the supplied strategy record. Do not invent official IELTS rules, score guarantees, or unsupported "
        "claims. Explain when it applies, why it helps, its limitations, and a short exercise. Return exactly JSON "
        "with keys explanation, when_to_use, limitations, exercise. Each value must be a non-empty string.\n"
        "PUBLISHED_STRATEGY_JSON_BEGIN\n" + json.dumps(context, ensure_ascii=False, sort_keys=True)
        + "\nPUBLISHED_STRATEGY_JSON_END"
    )
    result = _parse_structured_text(provider.generate(prompt), {"explanation", "when_to_use", "limitations", "exercise"})
    return {
        "strategy_id": strategy_id,
        "strategy_version": strategy["version"],
        "pack_version": pack.pack_version,
        "manifest_sha256": pack.manifest_sha256,
        **result,
        "claim_eligible": False,
    }


def generate_published_strategy_example(pack: KnowledgePack, strategy_id: str, task: str, *,
                                        provider: TextGenerationProvider) -> dict:
    strategy = pack.get_strategy(strategy_id)
    if strategy is None:
        raise KeyError(f"unknown published strategy: {strategy_id}")
    if not isinstance(task, str) or not task.strip() or len(task) > 2000:
        raise ValueError("task must contain 1..2000 characters")
    context = {
        "strategy_id": strategy_id,
        "strategy_version": strategy["version"],
        "title": strategy["title"],
        "summary": strategy["summary"],
        "steps": strategy["steps"],
        "limitations": strategy["limitations"],
        "existing_examples": strategy["examples"] + [
            example["content"] for example in pack.examples
            if example["strategy_id"] == strategy_id
        ],
        "task": task,
        "pack_version": pack.pack_version,
    }
    prompt = (
        "Create a new original IELTS learning example that demonstrates the supplied strategy. "
        "Do not copy or lightly rewrite any existing example. Do not claim an official band score. "
        "Keep it relevant to the task and explain which step demonstrates the strategy. Return exactly JSON "
        "with keys example, strategy_application, learning_note; all values must be non-empty strings.\n"
        "PUBLISHED_EXAMPLE_CONTEXT_BEGIN\n" + json.dumps(context, ensure_ascii=False, sort_keys=True)
        + "\nPUBLISHED_EXAMPLE_CONTEXT_END"
    )
    result = _parse_structured_text(
        provider.generate(prompt), {"example", "strategy_application", "learning_note"}
    )
    existing_examples = strategy["examples"] + [
        example["content"] for example in pack.examples
        if example["strategy_id"] == strategy_id
    ]
    scan = scan_publication_leaks(
        [result["example"]],
        [{"source_id": f"existing-example-{index}", "text": value}
         for index, value in enumerate(existing_examples)],
    )
    if not scan["passed"]:
        raise GenerationError("generated example contains a long exact overlap with an existing example")
    return {
        "strategy_id": strategy_id,
        "strategy_version": strategy["version"],
        "pack_version": pack.pack_version,
        "manifest_sha256": pack.manifest_sha256,
        **result,
        "claim_eligible": False,
    }


def _parse_structured_text(raw: str, required: set[str]) -> dict[str, str]:
    try:
        result = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise GenerationError("model must return the required JSON object") from exc
    if not isinstance(result, dict) or set(result) != required:
        raise GenerationError("model output does not match the required structured response contract")
    if any(not isinstance(value, str) or not value.strip() or len(value) > 12_000 for value in result.values()):
        raise GenerationError("model response fields must be non-empty text")
    return result


def get_published_example(pack: KnowledgePack, example_id: str) -> dict:
    """Resolve a separately reviewed example to its published strategy record."""
    example = pack.get_example(example_id)
    if example is None:
        raise KeyError(f"unknown published example: {example_id}")
    strategy = pack.get_strategy(example["strategy_id"])
    if strategy is None:
        raise ValueError(f"published example references an unavailable strategy: {example['strategy_id']}")
    return {
        "example": example,
        "strategy": {
            "id": strategy["id"],
            "title": strategy["title"],
            "version": strategy["version"],
            "summary": strategy["summary"],
        },
        "pack_version": pack.pack_version,
        "schema_version": pack.schema_version,
        "manifest_sha256": pack.manifest_sha256,
    }
