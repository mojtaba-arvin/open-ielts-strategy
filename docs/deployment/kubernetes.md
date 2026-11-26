# Kubernetes deployment template

A hardened Kubernetes manifest template is provided at `deploy/kubernetes/published-mcp.yaml`. It is a deployment starting point, not an applied cluster release.

## Prerequisites

Before applying the template, provision:

1. An immutable published MCP image reference and registry pull credentials, if needed.
2. Namespace-scoped Secret `published-mcp-secrets` with required `tokens-json` and `redis-url`; `openai-api-key` is optional and only needed when remote generation/embedding is explicitly approved.
3. A read-only mountable PVC named `published-knowledge-pack` containing a verified Knowledge Pack.
4. An ingress controller in the `ingress-nginx` namespace (or adjust the NetworkPolicy selector).
5. A cert-manager ClusterIssuer (or replace the Ingress annotation with your certificate workflow).

Do not commit real Secret manifests, token values, Redis credentials, or API keys. Use an external secret manager or sealed/external-secrets workflow.

## Required substitutions

Replace:
- `ghcr.io/REPLACE_OWNER/open-ielts-strategy/published-mcp:REPLACE_IMMUTABLE_TAG` with an immutable image digest/tag.
- `published-mcp.example.com` and `https://client.example.com` with the actual service Host and allowed browser Origin.
- `REPLACE_WITH_CLUSTER_ISSUER` with the certificate issuer.
- `published-knowledge-pack` with the provisioned read-only PVC name if different.

The pod runs as UID/GID 10001, disables service-account token mounting, uses a read-only root filesystem, drops all Linux capabilities, enables RuntimeDefault seccomp, mounts the Knowledge Pack read-only, and defines startup/readiness/liveness probes, resource limits, a PDB, and an ingress/egress NetworkPolicy. The Service is ClusterIP; external traffic enters only through the TLS Ingress.

## Distributed rate limiting and egress

The image includes the Redis client, and the multi-replica production template requires the Secret key `redis-url` to point to an authenticated `rediss://` endpoint for shared per-subject rate limiting across replicas. Redis failures are fail-closed (HTTP 503); do not deploy the production template without managed Redis TLS/ACL. The sample NetworkPolicy permits same-namespace Redis pods on 6379 and outbound HTTPS for explicitly configured API providers. Adjust egress rules for a managed Redis endpoint, private DNS, or private model gateway; do not broaden egress without review.

Structured audit events are written to container stdout without request/response bodies or credentials. Configure your platform log collector for durable retention, access controls, and tamper-resistant storage. The template does not configure OIDC, workload identity, external secret synchronization, backup policy, autoscaling, or incident response.

## Apply and verify

After substitutions and provisioning:

```bash
kubectl apply -f deploy/kubernetes/published-mcp.yaml
kubectl -n open-ielts get deployment,pods,service,ingress,networkpolicy,pdb
kubectl -n open-ielts rollout status deployment/published-mcp
```

Validate TLS, Host/Origin policy, MCP authentication, per-subject limits, Redis fail-closed behavior, audit forwarding, and pack integrity from inside the intended network before enabling external clients. No live cluster deployment or penetration test is claimed by this repository change.
