# Production readiness and operations

This runbook defines the production deployment contract for the published-only MCP service. The repository supplies a hardened deployment baseline; it does not claim that a live cluster, identity provider, managed Redis, secret manager, backup target, or penetration test exists. A release is not production-ready until an operator has completed and recorded every environment-specific gate below.

## Supported production topology

- TLS ingress/reverse proxy in front of the ClusterIP service; never publish the pod port directly.
- External OIDC-aware identity gateway or API gateway at the edge. The gateway must authenticate users, enforce audience/issuer/expiry and MFA policy where required, and restrict access to the MCP path. The application bearer token remains a second, read-only service credential; it is not OIDC and must not be presented as federated identity.
- At least two application replicas, rolling updates with zero unavailable replicas, PodDisruptionBudget, topology spread, restricted Pod Security Standard, non-root UID, read-only root filesystem, dropped Linux capabilities, seccomp RuntimeDefault, resource bounds, and a read-only Knowledge Pack mount.
- Managed Redis using TLS (rediss URL) for shared per-subject rate limiting. The multi-replica Kubernetes template requires this secret; the application fails closed if the limiter is unavailable.
- A versioned, immutable Knowledge Pack artifact mounted read-only. The pack manifest digest and container image digest must be recorded together for every deployment.
- Central collection of structured audit events from stdout, with retention, access controls, integrity protection, and alerting configured outside the application.

## Required environment configuration

Create secrets using the cluster's external secret manager; do not commit Kubernetes Secret values or paste credentials into manifests.

| Secret key | Requirement |
|---|---|
| tokens-json | Required registry with unique random tokens (at least 32 characters), stable subjects, and only knowledge:read scope |
| redis-url | Required rediss URL to managed Redis on the approved TLS port; use certificate verification and a dedicated ACL identity |
| openai-api-key | Omit unless the operator explicitly enables remote generation/embedding and has approved the data-egress boundary |

The HTTP service has no built-in OIDC implementation. Configure OIDC at a trusted gateway and ensure it cannot be bypassed through a direct Service, NodePort, LoadBalancer, pod IP, or alternate ingress. Keep the application Service as ClusterIP. The Kubernetes NetworkPolicy allows ingress only from the ingress-controller namespace and Redis egress only on the TLS Redis port plus cluster DNS. Replace the documentation-only Redis CIDR with the exact managed Redis destination range(s); adapt DNS labels and destination policy to the selected CNI/cloud provider, without adding unrestricted egress.

The supplied Kubernetes file intentionally contains example image, hostname, certificate issuer, OIDC auth endpoint, and Redis egress CIDR (203.0.113.0/24 is documentation-only TEST-NET space). Replace these values with an immutable image digest, the real OIDC auth endpoint, the managed Redis destination CIDR(s), and real cluster values before applying. Do not deploy the template unchanged.

## Deployment sequence

1. Build and scan the image in CI; pin the final deployment to its immutable digest, never a mutable latest tag.
2. Build the Knowledge Pack through the private approval and leakage gates. Independently inspect the full candidate diff and obtain the required rights/legal sign-off. Publish the exact manifest digest as a versioned artifact.
3. Provision the namespace with restricted Pod Security enforcement, ingress controller, TLS certificate automation, external OIDC gateway, managed Redis ACL/TLS, external secret synchronization, storage for the immutable pack, audit export, and NetworkPolicy enforcement.
4. Populate the required secrets from the secret manager. Confirm that Redis TLS certificate validation is enabled and that the URL uses rediss.
5. Mount the approved Knowledge Pack read-only. Record pack version, manifest SHA-256, image digest, source commit, and deployment change ID.
6. Apply the Kubernetes manifest after replacing every example value. Validate the rendered resources with the cluster's admission policy and kubectl diff before apply.
7. Wait for startup, readiness, and rollout completion. /healthz is liveness only; /readyz is returned by the app after the pack has been loaded and integrity-checked during app construction. Neither endpoint measures educational quality.
8. From an authorized external client, verify OIDC enforcement, bearer-token scope, token revocation, Host/Origin rejection, request-size rejection, rate limiting across replicas, Redis outage fail-closed behavior, and audit event delivery.
9. Run the rollback drill against a prior immutable image and prior approved pack digest. Do not rewrite Git history; restore by deploying the previous immutable pair.
10. Record operator, timestamps, evidence links, exceptions, and sign-off in the deployment record.

## Operational monitoring and response

Collect metrics at the ingress, application process, Redis, and cluster layers. At minimum alert on:
- 5xx and 429 rates, p50/p95/p99 latency, request volume, active connections, and rejected Host/Origin/authentication requests;
- readiness failures, restarts, OOM kills, CPU/memory saturation, rollout stalls, and replica availability;
- Redis connection/command failures and rate-limit fail-closed responses;
- missing/stale audit delivery, unexpected subjects/scopes, token registry changes, and deployment digest drift;
- Knowledge Pack load/integrity failures and image/pack digest mismatch.

Do not log bearer tokens, learner prompts, retrieved content, model responses, or private source material. Audit logs are metadata, not a transcript of user activity. Configure append-only or tamper-evident retention in the external log platform, least-privilege access, retention expiry, and alerting for delivery gaps.

For an incident: block ingress or revoke affected tokens; preserve minimal metadata; rotate credentials in the secret manager; inspect ingress, application, Redis, and deployment audit records; restore the last known-good image/pack digest pair; document impact and remediation. Treat any accidental source-content or credential exposure as a security incident.

## Backup, recovery, and continuity

The published Knowledge Pack is immutable and should be reproducible from its reviewed Git revision and release artifact. Retain the exact artifact and checksum used by each deployment. Redis rate-limit state is ephemeral and must not contain learner or knowledge content. Retain infrastructure configuration and secret references, not secret values, in backup records. Test restoration of the prior pack/image pair and secret rotation on a schedule set by the operator.

## Production acceptance gates

A deployment may be called production-ready only when all of the following have evidence:
- OIDC gateway deployed and bypass paths blocked;
- TLS and certificate renewal verified;
- external secret synchronization and rotation tested;
- managed Redis TLS, ACL, multi-replica rate limiting, and outage behavior tested;
- NetworkPolicy enforced by the actual cluster CNI and egress verified;
- image and pack immutable digests recorded;
- audit events exported to tamper-evident retention with alerting;
- backup/restore and rollback drills passed;
- load, soak, and failure-injection tests meet pre-registered service objectives;
- independent threat model and penetration test findings triaged, with no unresolved critical/high findings;
- on-call ownership, incident response, and data-retention policies approved.

The code and deployment-template controls are testable in CI. The environment-specific gates above require an actual operator-controlled cluster and external services; repository CI cannot honestly mark them complete.
