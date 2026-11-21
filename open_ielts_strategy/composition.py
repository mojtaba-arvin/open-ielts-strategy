"""Resolve explicitly selected skills and their pinned dependencies."""
from __future__ import annotations

def resolve_dependencies(selected: list[str], entries: list[dict]) -> list[str]:
    manifest = {entry["name"]: entry for entry in entries}
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
