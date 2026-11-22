"""Resolve explicitly selected skills and their pinned dependencies."""
from __future__ import annotations

from typing import Any


def resolve_dependencies(selected: list[str], entries: list[dict]) -> list[str]:
    """Return a deterministic topological order, rejecting malformed lock data."""
    if not isinstance(selected, list):
        raise ValueError("selected skills must be a list")
    if not isinstance(entries, list):
        raise ValueError("skill entries must be a list")

    manifest: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"skill entry {index} must be an object")
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError(f"skill entry {index} has an invalid name")
        if name in manifest:
            raise ValueError(f"duplicate skill name: {name}")
        dependencies = entry.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise ValueError(f"{name}: dependencies must be a list")
        if any(
            not isinstance(dependency, str)
            or not dependency.strip()
            or dependency != dependency.strip()
            for dependency in dependencies
        ):
            raise ValueError(f"{name}: dependencies must contain non-empty canonical names")
        if len(dependencies) != len(set(dependencies)):
            raise ValueError(f"{name}: duplicate dependency")
        manifest[name] = entry

    for index, skill in enumerate(selected):
        if not isinstance(skill, str) or not skill.strip() or skill != skill.strip():
            raise ValueError(f"selected skill {index} must be a non-empty canonical name")

    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name not in manifest:
            raise ValueError(f"unknown skill dependency: {name}")
        if name in visiting:
            raise ValueError(f"dependency cycle detected at: {name}")
        if name in visited:
            return
        visiting.add(name)
        for dependency in manifest[name].get("dependencies", []):
            visit(dependency)
        visiting.remove(name)
        visited.add(name)
        ordered.append(name)

    for skill in selected:
        visit(skill)
    return ordered
