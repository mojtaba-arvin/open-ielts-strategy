"""Dependency-aware Study Mode planning over a published Knowledge Pack."""
from __future__ import annotations

from .published_learning import get_published_learning_path

_VALID_SKILLS = {"speaking", "writing", "reading", "listening", "general"}


def build_study_progression(pack, *, skill: str, completed_path_ids=(), limit: int = 20) -> dict:
    if skill not in _VALID_SKILLS:
        raise ValueError("unsupported IELTS skill")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    completed = set(completed_path_ids)
    if any(not isinstance(value, str) or not value for value in completed):
        raise ValueError("completed_path_ids must contain non-empty path IDs")
    paths = {item["id"]: item for item in pack.learning_paths
             if item["skill"] in {skill, "general"} or skill == "general"}
    unknown_completed = completed - {item["id"] for item in pack.learning_paths}
    if unknown_completed:
        raise ValueError("unknown completed learning paths: " + ", ".join(sorted(unknown_completed)))
    dependencies = {}
    for path_id, item in paths.items():
        required = set(item["prerequisites"])
        missing = required - {candidate["id"] for candidate in pack.learning_paths}
        if missing:
            raise ValueError(f"learning path {path_id} has unknown prerequisites: {', '.join(sorted(missing))}")
        dependencies[path_id] = required
    visiting, visited = set(), set()

    def visit(path_id):
        if path_id in visiting:
            raise ValueError(f"learning path prerequisite cycle includes {path_id}")
        if path_id in visited:
            return
        visiting.add(path_id)
        for prerequisite in dependencies[path_id]:
            if prerequisite in dependencies:
                visit(prerequisite)
        visiting.remove(path_id)
        visited.add(path_id)

    for path_id in sorted(dependencies):
        visit(path_id)

    planned = []
    for path_id, item in sorted(paths.items()):
        unmet = sorted(dependencies[path_id] - completed)
        resolved = get_published_learning_path(pack, path_id)
        planned.append({
            **resolved,
            "progress": {
                "status": "completed" if path_id in completed else ("blocked" if unmet else "available"),
                "completed": path_id in completed,
                "unmet_prerequisites": unmet,
                "step_count": len(resolved["resolved_steps"]),
                "next_step": next((step for step in resolved["resolved_steps"]
                                   if step["order"] > 0), None) if path_id not in completed else None,
            },
            "objectives": list(item["objectives"]),
        })
    available = [item for item in planned if item["progress"]["status"] == "available"]
    return {
        "status": "ready" if planned else "no-published-learning-path",
        "skill": skill,
        "completed_path_ids": sorted(completed),
        "available_path_ids": [item["learning_path"]["id"] for item in available],
        "learning_paths": planned[:limit],
        "pack_version": pack.pack_version,
        "manifest_sha256": pack.manifest_sha256,
        "progress_semantics": "Completion is supplied by the caller; this planner does not infer mastery.",
        "claim_eligible": False,
    }
