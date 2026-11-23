"""Replaceable contracts for independently versioned capability packages.

No third-party package is imported or selected implicitly. Integrators opt in by
installing an entry point in the open_ielts_strategy.adapters group.
"""
from __future__ import annotations
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any, Callable

CAPABILITIES = {"document_ingestion", "knowledge_extraction", "audio_transcription",
                "hybrid_retrieval", "response_evaluation"}

@dataclass(frozen=True)
class AdapterDescriptor:
    name: str
    capability: str
    version: str
    factory: Callable[..., Any]

def discover_adapters() -> tuple[AdapterDescriptor, ...]:
    discovered = []
    points = entry_points()
    selected = points.select(group="open_ielts_strategy.adapters") if hasattr(points, "select") else points.get("open_ielts_strategy.adapters", ())
    for point in selected:
        capability = point.name.split(":", 1)[0]
        if capability not in CAPABILITIES:
            continue
        distribution = getattr(point, "dist", None)
        discovered.append(AdapterDescriptor(point.name, capability,
            distribution.version if distribution else "unknown", point.load))
    return tuple(sorted(discovered, key=lambda item: (item.capability, item.name)))

def resolve_adapter(capability: str, *, preferred: str | None = None,
                    descriptors: tuple[AdapterDescriptor, ...] | None = None) -> AdapterDescriptor:
    if capability not in CAPABILITIES:
        raise ValueError(f"unsupported adapter capability: {capability}")
    candidates = [item for item in (descriptors if descriptors is not None else discover_adapters())
                  if item.capability == capability]
    if preferred is not None:
        candidates = [item for item in candidates if item.name == preferred]
        if not candidates:
            raise LookupError(f"requested {capability} adapter is not installed: {preferred}")
    if not candidates:
        raise LookupError(f"no {capability} adapter is installed")
    if len(candidates) > 1:
        raise LookupError(f"multiple {capability} adapters are installed; select one explicitly: " +
                          ", ".join(item.name for item in candidates))
    return candidates[0]

def create_adapter(capability: str, *, preferred: str | None = None, config: dict | None = None):
    if config is not None and not isinstance(config, dict):
        raise ValueError("adapter config must be an object")
    descriptor = resolve_adapter(capability, preferred=preferred)
    factory = descriptor.factory()
    if not callable(factory):
        raise TypeError(f"adapter entry point did not resolve to a factory: {descriptor.name}")
    return factory(**(config or {}))
