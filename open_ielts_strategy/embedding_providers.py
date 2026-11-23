"""Bounded HTTPS embedding provider for OpenAI-compatible APIs.

The provider is opt-in. API credentials are read only from an environment
variable; redirects are disabled and response/input sizes are bounded.
"""
from __future__ import annotations

import json
import math
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OpenAICompatibleEmbeddingProvider:
    def __init__(self, *, model: str, endpoint: str = "https://api.openai.com/v1/embeddings",
                 api_key_env: str = "OPENAI_API_KEY", timeout: float = 20.0,
                 max_retries: int = 2, opener=None, sleeper=time.sleep):
        if not isinstance(model, str) or not model.strip() or len(model) > 200:
            raise ValueError("embedding model must be non-empty bounded text")
        parsed = urlsplit(endpoint) if isinstance(endpoint, str) else None
        if (parsed is None or parsed.scheme != "https" or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise ValueError("embedding endpoint must be an HTTPS URL without credentials, query, or fragment")
        if not isinstance(api_key_env, str) or not api_key_env.isidentifier():
            raise ValueError("api_key_env must be a valid environment variable name")
        if not isinstance(timeout, (int, float)) or not 1 <= timeout <= 120:
            raise ValueError("timeout must be between 1 and 120 seconds")
        if type(max_retries) is not int or not 0 <= max_retries <= 4:
            raise ValueError("max_retries must be between 0 and 4")
        api_key = os.environ.get(api_key_env, "")
        if not api_key or len(api_key) > 4096:
            raise ValueError(f"environment variable {api_key_env} must contain the embedding API key")
        self.model = model.strip()
        self.endpoint = endpoint
        self.timeout = float(timeout)
        self.max_retries = max_retries
        self.api_key = api_key
        self._opener = opener or build_opener(_NoRedirect())
        self._sleeper = sleeper

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not isinstance(texts, list) or not 1 <= len(texts) <= 64:
            raise ValueError("embedding requests must contain 1..64 texts")
        if any(not isinstance(text, str) or not text.strip() or len(text) > 10000 for text in texts):
            raise ValueError("each embedding input must contain 1..10000 characters")
        if sum(len(text) for text in texts) > 100000:
            raise ValueError("embedding request exceeds the total input character limit")
        body = json.dumps({"model": self.model, "input": texts}, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.endpoint, data=body, method="POST",
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json", "Accept": "application/json"},
        )
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    status = getattr(response, "status", 200)
                    if status != 200:
                        raise ValueError(f"embedding provider returned HTTP {status}")
                    raw = response.read(10_000_001)
                if len(raw) > 10_000_000:
                    raise ValueError("embedding provider response exceeds 10 MB")
                payload = json.loads(raw)
                data = payload.get("data") if isinstance(payload, dict) else None
                if not isinstance(data, list) or len(data) != len(texts):
                    raise ValueError("embedding provider returned an unexpected vector count")
                ordered = [None] * len(texts)
                for item in data:
                    if not isinstance(item, dict) or type(item.get("index")) is not int:
                        raise ValueError("embedding provider returned malformed vector metadata")
                    index = item["index"]
                    vector = item.get("embedding")
                    if not 0 <= index < len(texts) or ordered[index] is not None:
                        raise ValueError("embedding provider returned duplicate or out-of-range vector indexes")
                    if not isinstance(vector, list) or not vector:
                        raise ValueError("embedding provider returned an invalid embedding vector")
                    if any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in vector):
                        raise ValueError("embedding provider returned non-finite vector values")
                    ordered[index] = [float(value) for value in vector]
                if any(vector is None for vector in ordered):
                    raise ValueError("embedding provider omitted one or more vectors")
                dimensions = {len(vector) for vector in ordered}
                if len(dimensions) != 1:
                    raise ValueError("embedding provider returned inconsistent vector dimensions")
                return ordered
            except HTTPError as exc:
                last_error = exc
                if exc.code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                    raise ValueError(f"embedding provider request failed with HTTP {exc.code}") from None
            except (URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise ValueError("embedding provider request failed after bounded retries") from None
            except json.JSONDecodeError as exc:
                raise ValueError("embedding provider returned invalid JSON") from exc
            self._sleeper(min(0.25 * (2 ** attempt), 1.0))
        raise ValueError("embedding provider request failed") from last_error
