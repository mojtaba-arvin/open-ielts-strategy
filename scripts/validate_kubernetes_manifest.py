"""Structural safety checks for the Kubernetes deployment template."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise SystemExit("Install PyYAML to validate Kubernetes manifests") from exc


def validate(path: str | Path) -> list[str]:
    documents = [item for item in yaml.safe_load_all(Path(path).read_text(encoding="utf-8")) if item]
    errors = []
    by_kind = {item.get("kind"): item for item in documents}
    expected = {"Namespace", "Deployment", "Service", "Ingress", "PodDisruptionBudget", "NetworkPolicy"}
    missing = expected - set(by_kind)
    if missing:
        errors.append(f"missing Kubernetes resource kinds: {sorted(missing)}")
    namespace = by_kind.get("Namespace", {}).get("metadata", {})
    namespace_labels = namespace.get("labels", {})
    if namespace_labels.get("pod-security.kubernetes.io/enforce") != "restricted":
        errors.append("namespace must enforce the Kubernetes restricted Pod Security Standard")
    deployment = by_kind.get("Deployment", {})
    if deployment.get("spec", {}).get("strategy", {}).get("rollingUpdate", {}).get("maxUnavailable") != 0:
        errors.append("rolling updates must preserve all currently available replicas")
    if deployment.get("spec", {}).get("replicas", 0) < 2:
        errors.append("production template must run at least two replicas")
    spec = deployment.get("spec", {}).get("template", {}).get("spec", {})
    if spec.get("automountServiceAccountToken") is not False:
        errors.append("service account token mounting must be disabled")
    security = spec.get("securityContext", {})
    if security.get("runAsNonRoot") is not True or security.get("runAsUser") != 10001:
        errors.append("pod must run as the non-root application UID")
    containers = spec.get("containers", [])
    if len(containers) != 1:
        errors.append("deployment must contain exactly one application container")
    else:
        container = containers[0]
        csecurity = container.get("securityContext", {})
        if csecurity.get("readOnlyRootFilesystem") is not True:
            errors.append("container root filesystem must be read-only")
        if csecurity.get("allowPrivilegeEscalation") is not False:
            errors.append("privilege escalation must be disabled")
        if csecurity.get("capabilities", {}).get("drop") != ["ALL"]:
            errors.append("all Linux capabilities must be dropped")
        mounts = container.get("volumeMounts", [])
        pack_mount = next((item for item in mounts if item.get("mountPath") == "/app/knowledge"), None)
        if not pack_mount or pack_mount.get("readOnly") is not True:
            errors.append("published Knowledge Pack must be mounted read-only")
        for probe_name in ("startupProbe", "readinessProbe", "livenessProbe"):
            if "exec" not in container.get(probe_name, {}):
                errors.append(f"{probe_name} must use an internal loopback probe")
        readiness = container.get("readinessProbe", {}).get("exec", {}).get("command", [])
        if not any("/readyz" in value for value in readiness):
            errors.append("readiness probe must use the dedicated /readyz endpoint")
        env = {item.get("name"): item for item in container.get("env", [])}
        token_env = env.get("IELTS_MCP_TOKENS_JSON", {})
        if "secretKeyRef" not in token_env.get("valueFrom", {}):
            errors.append("token registry must be sourced from a Kubernetes Secret")
        redis_env = env.get("IELTS_MCP_REDIS_URL", {})
        redis_ref = redis_env.get("valueFrom", {}).get("secretKeyRef", {})
        if not redis_ref or redis_ref.get("optional", False):
            errors.append("multi-replica production deployment must require a managed Redis URL from a Secret")
    service = by_kind.get("Service", {})
    if service.get("spec", {}).get("type") != "ClusterIP":
        errors.append("published MCP Service must remain ClusterIP-only")
    ingress = by_kind.get("Ingress", {})
    if not ingress.get("spec", {}).get("tls"):
        errors.append("Ingress must configure TLS")
    annotations = ingress.get("metadata", {}).get("annotations", {})
    auth_url = annotations.get("nginx.ingress.kubernetes.io/auth-url", "")
    if not auth_url.startswith("https://"):
        errors.append("Ingress must delegate authentication to an HTTPS OIDC-aware gateway")
    network_policy = by_kind.get("NetworkPolicy", {})
    if set(network_policy.get("spec", {}).get("policyTypes", [])) != {"Ingress", "Egress"}:
        errors.append("NetworkPolicy must restrict both ingress and egress")
    egress_ports = {
        port.get("port")
        for rule in network_policy.get("spec", {}).get("egress", [])
        for port in rule.get("ports", [])
    }
    if 6380 not in egress_ports:
        errors.append("NetworkPolicy must allow the configured TLS Redis port")
    if 6379 in egress_ports:
        errors.append("plaintext Redis egress must not be allowed")
    if 443 in egress_ports:
        errors.append("unrestricted outbound HTTPS must not be allowed by default")
    for rule in network_policy.get("spec", {}).get("egress", []):
        for destination in rule.get("to", []):
            cidr = destination.get("ipBlock", {}).get("cidr")
            if cidr == "0.0.0.0/0":
                errors.append("egress IP blocks must not allow every IPv4 destination")
    return errors


def main() -> int:
    errors = validate("deploy/kubernetes/published-mcp.yaml")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Kubernetes deployment template structural checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
