"""Small explicit registry for knowledge-extraction providers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


class ProviderRegistry:
    def __init__(self):
        self._factories: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, factory: Callable[..., Any]) -> None:
        if not isinstance(name, str) or not name or name.strip() != name:
            raise ValueError("provider name must be non-empty normalized text")
        if not callable(factory):
            raise TypeError("provider factory must be callable")
        if name in self._factories:
            raise ValueError(f"provider already registered: {name}")
        self._factories[name] = factory

    def create(self, name: str, **config: Any) -> Any:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            raise ValueError(f"unknown provider: {name}; available: {', '.join(self.names)}") from exc
        return factory(**config)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))


def build_extraction_provider(name: str, **config: Any):
    """Construct an explicitly selected extraction provider; no default network call."""
    from .semantic_extraction import OllamaLocalProvider
    from .api_extraction import OpenAICompatibleProvider

    registry = ProviderRegistry()
    registry.register("ollama", OllamaLocalProvider)
    registry.register("openai-compatible", OpenAICompatibleProvider)
    return registry.create(name, **config)
