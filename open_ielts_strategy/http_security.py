"""Token identity and optional shared rate-limit primitives for HTTP MCP."""
from __future__ import annotations

import hashlib
import hmac
import json
import re


class AuthTokenRegistry:
    """Store only token digests and expose read-only principal scopes."""

    def __init__(self, tokens: list[dict]):
        if not isinstance(tokens, list) or not 1 <= len(tokens) <= 1000:
            raise ValueError("token registry must contain 1..1000 entries")
        self._tokens = []
        seen = set()
        for item in tokens:
            if not isinstance(item, dict) or set(item) != {"token", "subject", "scopes"}:
                raise ValueError("each token entry requires exactly token, subject, and scopes")
            token, subject, scopes = item["token"], item["subject"], item["scopes"]
            if not isinstance(token, str) or len(token) < 32 or len(token) > 4096:
                raise ValueError("each bearer token must contain 32..4096 characters")
            if not isinstance(subject, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}", subject):
                raise ValueError("token subject must be a stable bounded identifier")
            if not isinstance(scopes, list) or not scopes or any(scope != "knowledge:read" for scope in scopes):
                raise ValueError("published MCP tokens must have the knowledge:read scope")
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            if digest in seen:
                raise ValueError("duplicate bearer token in registry")
            seen.add(digest)
            self._tokens.append((digest, {"subject": subject, "scopes": tuple(sorted(set(scopes)))}))

    @classmethod
    def from_environment(cls, *, token: str | None = None, tokens_json: str | None = None):
        if tokens_json:
            try:
                entries = json.loads(tokens_json)
            except json.JSONDecodeError as exc:
                raise ValueError("token registry environment variable must be valid JSON") from exc
            return cls(entries)
        if token:
            return cls([{"token": token, "subject": "shared-service", "scopes": ["knowledge:read"]}])
        raise ValueError("configure either a shared bearer token or a token registry")

    def authenticate(self, authorization: bytes) -> dict | None:
        try:
            scheme, value = authorization.decode("utf-8").split(" ", 1)
        except (UnicodeDecodeError, ValueError):
            return None
        if scheme.casefold() != "bearer" or not value:
            return None
        candidate = hashlib.sha256(value.encode("utf-8")).digest()
        principal = None
        for digest, entry in self._tokens:
            if hmac.compare_digest(candidate, digest):
                principal = entry
        return principal


class RedisTokenBucket:
    """Atomic distributed token bucket backed by Redis and fail-closed on errors."""

    _SCRIPT = """
local now = redis.call('TIME')
local instant = tonumber(now[1]) + tonumber(now[2]) / 1000000
local rate = tonumber(ARGV[1])
local burst = tonumber(ARGV[2])
local state = redis.call('HMGET', KEYS[1], 'tokens', 'updated')
local tokens = tonumber(state[1])
local updated = tonumber(state[2])
if tokens == nil then tokens = burst end
if updated == nil then updated = instant end
tokens = math.min(burst, tokens + math.max(0, instant - updated) * rate)
local allowed = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
end
redis.call('HMSET', KEYS[1], 'tokens', tokens, 'updated', instant)
redis.call('PEXPIRE', KEYS[1], math.ceil(math.max(60000, burst / rate * 4000)))
return allowed
"""

    def __init__(self, url: str, *, rate: float, burst: int, prefix: str = "open-ielts:mcp:rate:", client=None):
        if not isinstance(url, str) or not url.startswith(("redis://", "rediss://")):
            raise ValueError("Redis rate-limit URL must use redis:// or rediss://")
        if rate <= 0 or burst < 1:
            raise ValueError("rate must be positive and burst must be at least one")
        if client is None:
            try:
                import redis
            except ImportError as exc:
                raise RuntimeError("install the redis extra to enable distributed MCP rate limiting") from exc
            client = redis.Redis.from_url(url, socket_connect_timeout=3, socket_timeout=3,
                                          health_check_interval=30)
        self.client, self.rate, self.burst, self.prefix = client, float(rate), int(burst), prefix

    def allow(self, key: str) -> bool:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        result = self.client.eval(self._SCRIPT, 1, self.prefix + digest, self.rate, self.burst)
        return bool(result)
