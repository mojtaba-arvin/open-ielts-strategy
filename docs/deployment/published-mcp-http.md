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

The MCP endpoint is provided by the MCP SDK Streamable HTTP transport (normally `/mcp`); `/healthz` is a minimal unauthenticated liveness endpoint. Every MCP request requires `Authorization: Bearer <IELTS_MCP_BEARER_TOKEN>`. Tokens shorter than 32 characters are rejected. Never put the token in source control, command history, URLs, or client logs.

## Container deployment

```bash
export IELTS_MCP_BEARER_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
docker compose -f compose.published-mcp.yml up --build -d
```

Compose binds the published service to host loopback only, mounts `./knowledge` read-only, runs as an unprivileged UID, drops Linux capabilities, enables a read-only root filesystem, and requires the bearer secret. The Knowledge Pack must already exist and pass the loader's integrity checks.

## Reverse proxy / remote access

Do not expose the container port directly to the public internet. Put it behind a TLS-terminating reverse proxy or private network gateway. Configure the exact proxy-facing Host values with `--allowed-hosts`; configure browser origins explicitly with `--allowed-origins` when browser clients are used. The app intentionally ignores forwarded client-IP headers. If a proxy is used, restrict direct access to the app port and apply trusted-proxy IP handling and connection limits at the proxy.

The middleware applies a per-source-IP in-memory token bucket (default 2 requests/second, burst 20), checks Host and optional Origin allowlists, requires a constant-time bearer-token comparison, and enforces a request body limit (default 1 MiB for declared Content-Length). The limiter is process-local: multiple workers/replicas require a shared gateway rate limiter. This is a shared service token, not per-user identity, delegated authorization, or an audit principal. Rotate it by updating the secret and restarting clients/service.

## Operational boundaries

- STDIO remains the recommended local desktop integration; HTTP is opt-in.
- The pack is loaded and validated at process startup. Restart after replacing a pack.
- The container does not mount the private authoring database or local source corpus.
- Do not configure model-backed tools unless the service is intentionally allowed to send retrieved published context and learner prompts to the selected model provider.
- Model API keys belong in a secret manager, not Compose literals.
- The liveness endpoint does not prove MCP readiness or educational quality.
- Backups, deployment availability, TLS, identity federation, per-user authorization, shared distributed rate limiting, structured audit retention, and incident response remain deployment-operator responsibilities.
- This deployment is a security baseline, not a completed production security certification. Conduct threat modeling and penetration testing before public exposure.
