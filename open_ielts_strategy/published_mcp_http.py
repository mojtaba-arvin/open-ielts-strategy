"""Authenticated Streamable HTTP transport for the published-only MCP server.

The transport is intentionally stateless with respect to private authoring data.
Deploy behind a TLS-terminating reverse proxy; the bearer token is a shared
service credential, not per-user identity or a substitute for network policy.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .http_security import AuthTokenRegistry, RedisTokenBucket


class _TokenBucket:
    def __init__(self, rate: float, burst: int, clock: Callable[[], float] = time.monotonic):
        if rate <= 0 or burst < 1:
            raise ValueError("rate must be positive and burst must be at least one")
        self.rate, self.burst, self.clock = rate, burst, clock
        self._state: dict[str, tuple[float, float]] = {}

    def allow(self, key: str) -> bool:
        now = self.clock()
        tokens, updated = self._state.get(key, (float(self.burst), now))
        tokens = min(float(self.burst), tokens + max(0.0, now - updated) * self.rate)
        if tokens < 1.0:
            self._state[key] = (tokens, now)
            return False
        self._state[key] = (tokens - 1.0, now)
        if len(self._state) > 10000:
            cutoff = now - max(60.0, self.burst / self.rate * 4)
            self._state = {k: v for k, v in self._state.items() if v[1] >= cutoff}
            if len(self._state) > 10000:
                newest = sorted(self._state.items(), key=lambda item: item[1][1], reverse=True)[:8000]
                self._state = dict(newest)
        return True


class AuthenticatedMCPMiddleware:
    """Small ASGI boundary: host/origin allowlists, bearer auth, body cap, rate limit."""

    def __init__(self, app, *, token: str | None = None, tokens_json: str | None = None,
                 allowed_hosts: set[str], allowed_origins: set[str] | None = None,
                 rate: float = 2.0, burst: int = 20, max_body_bytes: int = 1_000_000,
                 rate_limiter=None, audit_sink: Callable[[dict], None] | None = None):
        self.token_registry = AuthTokenRegistry.from_environment(token=token, tokens_json=tokens_json)
        if audit_sink is not None and not callable(audit_sink):
            raise ValueError("audit_sink must be callable")
        if not allowed_hosts:
            raise ValueError("at least one allowed Host value is required")
        if max_body_bytes < 1024:
            raise ValueError("max_body_bytes must be at least 1024")
        self.app = app
        self.allowed_hosts = {value.casefold() for value in allowed_hosts}
        self.allowed_origins = set(allowed_origins or ())
        self.limiter = rate_limiter or _TokenBucket(rate, burst)
        self.auth_failure_limiter = _TokenBucket(rate=1.0, burst=5)
        self.max_body_bytes = max_body_bytes
        self.audit_sink = audit_sink or (lambda event: print(json.dumps(event, sort_keys=True), flush=True))

    @staticmethod
    async def _respond(send, status: int, message: str):
        body = (message + "\n").encode("utf-8")
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8"),
                                (b"content-length", str(len(body)).encode("ascii")),
                                (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = time.monotonic()
        request_id = uuid.uuid4().hex
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        path = scope.get("path", "")
        method = scope.get("method", "")
        client = scope.get("client") or ("unknown", 0)
        client_ip = str(client[0])
        subject = None
        status = 500
        received = 0
        sent = 0

        async def audited_send(message):
            nonlocal status, sent
            if message["type"] == "http.response.start":
                status = int(message["status"])
            elif message["type"] == "http.response.body":
                sent += len(message.get("body", b""))
            await send(message)

        async def respond(code: int, message: str):
            nonlocal status
            status = code
            await self._respond(audited_send, code, message)

        try:
            host = headers.get(b"host", b"").decode("latin1").split(":", 1)[0].casefold()
            if host not in self.allowed_hosts:
                return await respond(421, "host not allowed")
            if path == "/healthz" and method == "GET":
                subject = "health-check"
                return await respond(200, "ok")
            origin = headers.get(b"origin")
            if origin and self.allowed_origins and origin.decode("latin1") not in self.allowed_origins:
                return await respond(403, "origin not allowed")
            principal = self.token_registry.authenticate(headers.get(b"authorization", b""))
            if principal is None:
                if not self.auth_failure_limiter.allow(client_ip):
                    return await respond(429, "authentication rate limit exceeded")
                return await respond(401, "unauthorized")
            if "knowledge:read" not in principal["scopes"]:
                return await respond(403, "insufficient scope")
            subject = principal["subject"]
            try:
                allowed = self.limiter.allow("subject:" + subject)
            except Exception:
                return await respond(503, "rate limiter unavailable")
            if not allowed:
                return await respond(429, "rate limit exceeded")
            content_length = headers.get(b"content-length")
            if content_length:
                try:
                    declared_length = int(content_length)
                    if declared_length < 0:
                        return await respond(400, "invalid content length")
                    if declared_length > self.max_body_bytes:
                        return await respond(413, "request body too large")
                except ValueError:
                    return await respond(400, "invalid content length")

            exceeded = False
            async def limited_receive():
                nonlocal received, exceeded
                message = await receive()
                if message["type"] == "http.request":
                    received += len(message.get("body", b""))
                    if received > self.max_body_bytes:
                        exceeded = True
                        return {"type": "http.disconnect"}
                return message

            async def guarded_send(message):
                if not exceeded:
                    await audited_send(message)

            await self.app(scope, limited_receive, guarded_send)
            if exceeded:
                await respond(413, "request body too large")
            return None
        finally:
            event = {
                "event": "published_mcp_http_request",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "subject": subject,
                "client_ip": client_ip,
                "method": method,
                "path": path,
                "status": status,
                "request_bytes": received,
                "response_bytes": sent,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
            }
            try:
                self.audit_sink(event)
            except Exception:
                pass


def create_http_app(pack_path: str | Path, *, token: str | None = None, tokens_json: str | None = None,
                    embedding_model_path: str | None = None,
                    embedding_provider_name: str | None = None,
                    embedding_model_name: str | None = None,
                    embedding_endpoint: str = "https://api.openai.com/v1/embeddings",
                    embedding_api_key_env: str = "OPENAI_API_KEY",
                    provider_name: str | None = None, model: str | None = None,
                    endpoint: str | None = None, api_key_env: str = "OPENAI_API_KEY",
                    allowed_hosts: set[str] | None = None,
                    allowed_origins: set[str] | None = None,
                    rate: float = 2.0, burst: int = 20,
                    max_body_bytes: int = 1_000_000, redis_url: str | None = None,
                    audit_sink: Callable[[dict], None] | None = None):
    from .published_knowledge_mcp import build_server
    server = build_server(pack_path, embedding_model_path=embedding_model_path,
                          embedding_provider_name=embedding_provider_name,
                          embedding_model_name=embedding_model_name,
                          embedding_endpoint=embedding_endpoint,
                          embedding_api_key_env=embedding_api_key_env,
                          provider_name=provider_name, model=model,
                          endpoint=endpoint, api_key_env=api_key_env)
    app_factory = getattr(server, "streamable_http_app", None)
    if not callable(app_factory):
        raise RuntimeError("installed MCP SDK does not expose streamable_http_app(); install the supported mcp extra")
    app = app_factory()
    rate_limiter = RedisTokenBucket(redis_url, rate=rate, burst=burst) if redis_url else None
    return AuthenticatedMCPMiddleware(
        app, token=token, tokens_json=tokens_json,
        allowed_hosts=allowed_hosts or {"localhost", "127.0.0.1"},
        allowed_origins=allowed_origins, rate=rate, burst=burst,
        max_body_bytes=max_body_bytes, rate_limiter=rate_limiter, audit_sink=audit_sink,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", default="knowledge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--token-env", default="IELTS_MCP_BEARER_TOKEN")
    parser.add_argument("--tokens-env", default="IELTS_MCP_TOKENS_JSON")
    parser.add_argument("--redis-url-env", default="IELTS_MCP_REDIS_URL")
    parser.add_argument("--allowed-hosts", default="localhost,127.0.0.1")
    parser.add_argument("--allowed-origins", default="")
    parser.add_argument("--rate", type=float, default=2.0, help="requests per second per authenticated subject")
    parser.add_argument("--burst", type=int, default=20)
    parser.add_argument("--max-body-bytes", type=int, default=1_000_000)
    parser.add_argument("--embedding-provider", choices=("local", "openai-compatible"))
    parser.add_argument("--embedding-model-path")
    parser.add_argument("--embedding-model-name")
    parser.add_argument("--embedding-endpoint", default="https://api.openai.com/v1/embeddings")
    parser.add_argument("--embedding-api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--provider", choices=("ollama", "openai-compatible"))
    parser.add_argument("--model")
    parser.add_argument("--endpoint")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    args = parser.parse_args(argv)
    try:
        import uvicorn
        token = os.environ.get(args.token_env) or None
        tokens_json = os.environ.get(args.tokens_env) or None
        if not token and not tokens_json:
            raise ValueError(f"configure {args.token_env} or {args.tokens_env}")
        redis_url = os.environ.get(args.redis_url_env) or None
        if not 1 <= args.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        app = create_http_app(
            args.pack, token=token, tokens_json=tokens_json, redis_url=redis_url,
            embedding_model_path=args.embedding_model_path,
            embedding_provider_name=args.embedding_provider, embedding_model_name=args.embedding_model_name,
            embedding_endpoint=args.embedding_endpoint, embedding_api_key_env=args.embedding_api_key_env,
            provider_name=args.provider, model=args.model, endpoint=args.endpoint,
            api_key_env=args.api_key_env,
            allowed_hosts={x.strip() for x in args.allowed_hosts.split(",") if x.strip()},
            allowed_origins={x.strip() for x in args.allowed_origins.split(",") if x.strip()},
            rate=args.rate, burst=args.burst, max_body_bytes=args.max_body_bytes,
        )
        uvicorn.run(app, host=args.host, port=args.port, log_level="info",
                    proxy_headers=False, server_header=False, date_header=False)
    except (ImportError, OSError, RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
