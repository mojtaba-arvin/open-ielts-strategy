"""Authenticated Streamable HTTP transport for the published-only MCP server.

The transport is intentionally stateless with respect to private authoring data.
Deploy behind a TLS-terminating reverse proxy; the bearer token is a shared
service credential, not per-user identity or a substitute for network policy.
"""
from __future__ import annotations

import argparse
import hmac
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable


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
        return True


class AuthenticatedMCPMiddleware:
    """Small ASGI boundary: host/origin allowlists, bearer auth, body cap, rate limit."""

    def __init__(self, app, *, token: str, allowed_hosts: set[str],
                 allowed_origins: set[str] | None = None, rate: float = 2.0,
                 burst: int = 20, max_body_bytes: int = 1_000_000):
        if not isinstance(token, str) or len(token) < 32:
            raise ValueError("MCP bearer token must contain at least 32 characters")
        if not allowed_hosts:
            raise ValueError("at least one allowed Host value is required")
        if max_body_bytes < 1024:
            raise ValueError("max_body_bytes must be at least 1024")
        self.app, self.token = app, token
        self.allowed_hosts = {value.casefold() for value in allowed_hosts}
        self.allowed_origins = set(allowed_origins or ())
        self.limiter = _TokenBucket(rate, burst)
        self.max_body_bytes = max_body_bytes

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
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        path = scope.get("path", "")
        host = headers.get(b"host", b"").decode("latin1").split(":", 1)[0].casefold()
        if host not in self.allowed_hosts:
            return await self._respond(send, 421, "host not allowed")
        if path == "/healthz" and scope.get("method") == "GET":
            return await self._respond(send, 200, "ok")
        origin = headers.get(b"origin")
        if origin and self.allowed_origins and origin.decode("latin1") not in self.allowed_origins:
            return await self._respond(send, 403, "origin not allowed")
        authorization = headers.get(b"authorization", b"")
        expected = ("Bearer " + self.token).encode("utf-8")
        if not hmac.compare_digest(authorization, expected):
            return await self._respond(send, 401, "unauthorized")
        client = scope.get("client") or ("unknown", 0)
        client_key = str(client[0])
        if not self.limiter.allow(client_key):
            return await self._respond(send, 429, "rate limit exceeded")
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_body_bytes:
                    return await self._respond(send, 413, "request body too large")
            except ValueError:
                return await self._respond(send, 400, "invalid content length")

        received = 0
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
                await send(message)

        await self.app(scope, limited_receive, guarded_send)
        if exceeded:
            await self._respond(send, 413, "request body too large")
        return None


def create_http_app(pack_path: str | Path, *, token: str,
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
                    max_body_bytes: int = 1_000_000):
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
    return AuthenticatedMCPMiddleware(
        app, token=token, allowed_hosts=allowed_hosts or {"localhost", "127.0.0.1"},
        allowed_origins=allowed_origins, rate=rate, burst=burst,
        max_body_bytes=max_body_bytes,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", default="knowledge")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--token-env", default="IELTS_MCP_BEARER_TOKEN")
    parser.add_argument("--allowed-hosts", default="localhost,127.0.0.1")
    parser.add_argument("--allowed-origins", default="")
    parser.add_argument("--rate", type=float, default=2.0, help="requests per second per client IP")
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
        token = os.environ.get(args.token_env, "")
        if len(token) < 32:
            raise ValueError(f"{args.token_env} must be set to a random secret of at least 32 characters")
        if not 1 <= args.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        app = create_http_app(
            args.pack, token=token, embedding_model_path=args.embedding_model_path,
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
