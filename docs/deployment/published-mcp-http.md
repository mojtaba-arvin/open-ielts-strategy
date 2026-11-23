# Published MCP Streamable HTTP deployment

The published MCP service is a read-only consumer of a verified Knowledge Pack. It does not expose private SQLite ingestion, extraction, source review, or publication tools.

## Install and run

Install the HTTP extra:

```bash
python -m pip install '.[http-mcp]'
export IELTS_MCP_BEARER_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
ielts-published-knowledge-mcp-http \
  --pack ./knowledge \
  --host 127.0.0.1 \
  --port 8000 \
  --allowed-hosts localhost,127.0.0.1
```

The MCP endpoint is provided by the MCP SDK Streamable HTTP transport (normally `/mcp`); `/healthz` is a minimal unauthenticated liveness endpoint. Every MCP request requires `Authorization: Bearer <token>`. Configure either the legacy `IELTS_MCP_BEARER_TOKEN` or a JSON registry in `IELTS_MCP_TOKENS_JSON`. Each registry entry has exactly `token`, `subject`, and `scopes`; the only accepted scope is `knowledge:read`. Tokens shorter than 32 characters are rejected. Token values are hashed in memory and never written to audit logs. Remove a registry entry to revoke a token. Never put raw tokens in source control, command history, URLs, or client logs.

Example registry shape (replace the placeholder with a generated secret and inject it through a secret manager):

```json
[
  {
    "token": "<random-secret-at-least-32-characters>",
    "subject": "learner-17",
    "scopes": ["knowledge:read"]
  }
]
```


## Container deployment

```bash
export IELTS_MCP_BEARER_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
docker compose -f compose.published-mcp.yml up --build -d
```

Compose binds the published service to host loopback only, mounts `./knowledge` read-only, runs as an unprivileged UID, drops Linux capabilities, enables a read-only root filesystem, and requires either the bearer token or token-registry environment variable. The Knowledge Pack must already exist and pass the loader's integrity checks. The Knowledge Pack must already exist and pass the loader's integrity checks.

## Reverse proxy / remote access

Do not expose the container port directly to the public internet. Put it behind a TLS-terminating reverse proxy or private network gateway. Configure the exact proxy-facing Host values with `--allowed-hosts`; configure browser origins explicitly with `--allowed-origins` when browser clients are used. The app intentionally ignores forwarded client-IP headers. If a proxy is used, restrict direct access to the app port and apply trusted-proxy IP handling and connection limits at the proxy.

The middleware checks Host and optional Origin allowlists, validates bearer tokens using constant-time digest comparison, rate-limits by authenticated subject (default 2 requests/second, burst 20), enforces request body limits (default 1 MiB, including chunked bodies), and emits structured JSON audit events to stdout with request ID, subject, status, byte counts, and duration—but never request/response content or credentials. Authentication failures also receive a small per-IP in-memory throttle. The default limiter is process-local. For shared limits across workers/replicas, install the `redis-rate-limit` extra and configure `IELTS_MCP_REDIS_URL`; the Redis Lua token bucket uses Redis server time, hashed subject keys, and fails closed if Redis is unavailable. Static subject tokens provide distinct per-user/service principals for read-only authorization and per-subject rate limits, but they are not OIDC, delegated authorization, or a federated identity system. Rotate/revoke by updating the secret registry and restarting clients/service.

## Operational boundaries

- STDIO remains the recommended local desktop integration; HTTP is opt-in.
- The pack is loaded and validated at process startup. Restart after replacing a pack.
- The container does not mount the private authoring database or local source corpus.
- Do not configure model-backed tools unless the service is intentionally allowed to send retrieved published context and learner prompts to the selected model provider. For remote embeddings, pass `--embedding-provider openai-compatible --embedding-model-name <model>` and inject `OPENAI_API_KEY` through the runtime secret manager; Compose forwards the variable when set. The embedding endpoint receives published strategy/example text and search queries. Local cached embeddings remain available with `--embedding-provider local --embedding-model-path <path>`.
- Model API keys belong in a secret manager, not Compose literals.
- The liveness endpoint does not prove MCP readiness or educational quality.
- Backups, deployment availability, TLS, identity federation/OIDC, durable tamper-resistant audit retention, external secret synchronization, and incident response remain deployment-operator responsibilities. Static subject tokens, optional Redis distributed limits, and stdout audit events are implemented as foundations.
- This deployment is a security baseline, not a completed production security certification. Conduct threat modeling and penetration testing before public exposure.
