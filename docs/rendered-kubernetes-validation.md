# Validating a rendered Kubernetes deployment

The checked-in Kubernetes YAML is a template, not a deployable production artifact.
Render it with the operator's environment-specific values, then run:

```sh
python scripts/validate_rendered_kubernetes_manifest.py \
  --manifest /secure/path/published-mcp.rendered.yaml \
  --profile /secure/path/cluster-profile.json
```

The profile is a JSON object with exactly six non-secret fields:

| Field | Meaning |
| --- | --- |
| `namespace` | Application namespace |
| `ingress_namespace` | Namespace allowed by the NetworkPolicy ingress selector |
| `hostname` | Single host used by Ingress TLS/rules, app allowed-hosts, and probes |
| `oidc_auth_url` | Exact HTTPS OIDC auth subrequest URL |
| `redis_cidrs` | Exact narrow CIDR allowlist for Redis TLS egress on TCP 6380 |
| `image_digest` | Immutable `sha256:<64 lowercase hex>` image digest |

See `schemas/kubernetes-cluster-profile.schema.json` for the machine-readable field
contract. Keep the profile outside the repository. Do not include passwords, tokens,
private keys, or secret values; secret material belongs in the operator's secret manager
and Kubernetes Secret synchronization path.

The validator rejects unresolved template/documentation placeholders, invalid Kubernetes namespace labels, malformed DNS hostnames and OIDC URLs, profile drift, mutable image references, public/non-unicast Redis ranges, and Redis CIDRs broader than IPv4 /16 or IPv6 /32. It does not contact Kubernetes,
verify admission policies, prove CNI enforcement, validate certificate issuance, test
OIDC bypass resistance, or establish production acceptance. Those remain live operator
checks tracked in issue #109.
