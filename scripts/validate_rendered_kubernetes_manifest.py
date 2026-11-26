"""Validate a rendered Kubernetes deployment against an operator-owned profile.

This is an artifact consistency check, not a live-cluster or CNI acceptance test.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml


PROFILE_KEYS = {
    "namespace",
    "ingress_namespace",
    "hostname",
    "oidc_auth_url",
    "redis_cidrs",
    "image_digest",
}
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(key)
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


def _valid_dns_subdomain(value):
    if not isinstance(value, str) or len(value) > 253:
        return False
    labels = value.split(".")
    return bool(labels) and all(
        1 <= len(label) <= 63
        and re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
        for label in labels
    )


def _profile_errors(profile):
    errors = []
    if not isinstance(profile, dict):
        return ["cluster profile must be a JSON object"]
    missing = PROFILE_KEYS - set(profile)
    extra = set(profile) - PROFILE_KEYS
    if missing:
        errors.append(f"cluster profile is missing keys: {sorted(missing)}")
    if extra:
        errors.append(f"cluster profile has unsupported keys: {sorted(extra)}")

    for key in ("namespace", "ingress_namespace"):
        value = profile.get(key)
        if not isinstance(value, str) or len(value) > 63 or not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", value
        ):
            errors.append(f"profile {key} must be a valid Kubernetes DNS label")
    if not _valid_dns_subdomain(profile.get("hostname")):
        errors.append("profile hostname must be a lowercase DNS subdomain")

    auth_url = profile.get("oidc_auth_url")
    try:
        parsed = urlparse(auth_url) if isinstance(auth_url, str) else None
        auth_host = parsed.hostname if parsed else None
        auth_port = parsed.port if parsed else None
    except ValueError:
        parsed, auth_host, auth_port = None, None, None
    if (
        not parsed
        or parsed.scheme != "https"
        or not _valid_dns_subdomain(auth_host)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or any(char.isspace() for char in auth_url)
        or (auth_port is not None and not 1 <= auth_port <= 65535)
    ):
        errors.append(
            "profile oidc_auth_url must be a valid HTTPS URL with a DNS host, "
            "no embedded credentials, query, or fragment"
        )

    digest = profile.get("image_digest")
    if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
        errors.append("profile image_digest must be a lowercase sha256 digest")

    cidrs = profile.get("redis_cidrs")
    if not isinstance(cidrs, list) or not cidrs or any(not isinstance(item, str) for item in cidrs):
        errors.append("profile redis_cidrs must be a non-empty list of CIDR strings")
    else:
        normalized = []
        for item in cidrs:
            try:
                network = ipaddress.ip_network(item, strict=True)
            except ValueError:
                errors.append(f"profile Redis CIDR is invalid or non-canonical: {item}")
                continue
            if network.prefixlen == 0:
                errors.append("profile Redis CIDRs must not allow every address")
            minimum_prefix = 16 if network.version == 4 else 32
            if network.prefixlen < minimum_prefix:
                errors.append("profile Redis CIDRs must be narrow (IPv4 /16 or smaller, IPv6 /32 or smaller)")
            if not network.network_address.is_private or not network.broadcast_address.is_private:
                errors.append("profile Redis CIDRs must contain only private unicast addresses")
            normalized.append(str(network))
        if len(normalized) != len(set(normalized)):
            errors.append("profile redis_cidrs must not contain duplicates")
    return errors

def validate(manifest_path: str | Path, profile_path: str | Path) -> list[str]:
    errors = []
    try:
        profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read cluster profile JSON: {exc}"]
    errors.extend(_profile_errors(profile))
    if errors:
        return errors

    try:
        documents = [
            item for item in yaml.safe_load_all(Path(manifest_path).read_text(encoding="utf-8"))
            if item is not None
        ]
    except (OSError, yaml.YAMLError) as exc:
        return [f"cannot read rendered Kubernetes manifest: {exc}"]
    if not documents or any(not isinstance(item, dict) for item in documents):
        return ["rendered manifest must contain Kubernetes object documents"]

    serialized = list(_walk_strings(documents))
    placeholder_patterns = ("REPLACE_", "example.com", "203.0.113.", "198.51.100.", "192.0.2.")
    if any(marker in value for value in serialized for marker in placeholder_patterns):
        errors.append("rendered manifest still contains an unresolved placeholder or documentation address")

    by_kind = {}
    for item in documents:
        kind = item.get("kind")
        if kind in by_kind:
            errors.append(f"rendered manifest contains duplicate {kind} resources")
        by_kind[kind] = item
    required = {"Namespace", "Deployment", "Service", "Ingress", "NetworkPolicy"}
    missing = required - set(by_kind)
    if missing:
        return errors + [f"rendered manifest is missing resources: {sorted(missing)}"]

    namespace = profile["namespace"]
    ingress_namespace = profile["ingress_namespace"]
    for kind, resource in by_kind.items():
        actual = resource.get("metadata", {}).get("namespace")
        if kind == "Namespace":
            actual = resource.get("metadata", {}).get("name")
        if actual != namespace:
            errors.append(f"{kind} must target profile namespace {namespace!r}")

    deployment = by_kind["Deployment"]
    pod_spec = deployment.get("spec", {}).get("template", {}).get("spec", {})
    containers = pod_spec.get("containers", [])
    if len(containers) != 1:
        errors.append("rendered Deployment must contain exactly one application container")
    else:
        image = containers[0].get("image", "")
        expected_suffix = "@" + profile["image_digest"]
        if not image.endswith(expected_suffix):
            errors.append("application image must be pinned to the profile's immutable digest")
        if ":" in image.rsplit("/", 1)[-1].split("@", 1)[0]:
            tag = image.rsplit("/", 1)[-1].split("@", 1)[0].rsplit(":", 1)[-1]
            if not tag:
                errors.append("application image reference is malformed")

    hostname = profile["hostname"]
    args = containers[0].get("args", []) if len(containers) == 1 else []
    if "--allowed-hosts" not in args or args[args.index("--allowed-hosts") + 1:args.index("--allowed-hosts") + 2] != [hostname]:
        errors.append("application --allowed-hosts must equal the profile hostname")
    for probe_name in ("startupProbe", "readinessProbe", "livenessProbe"):
        command = containers[0].get(probe_name, {}).get("exec", {}).get("command", []) if len(containers) == 1 else []
        if not any(hostname in value for value in command if isinstance(value, str)):
            errors.append(f"{probe_name} must send the profile hostname")

    ingress = by_kind["Ingress"]
    annotations = ingress.get("metadata", {}).get("annotations", {})
    if annotations.get("nginx.ingress.kubernetes.io/auth-url") != profile["oidc_auth_url"]:
        errors.append("Ingress OIDC auth-url must exactly match the operator profile")
    rules = ingress.get("spec", {}).get("rules", [])
    tls_hosts = {
        host for entry in ingress.get("spec", {}).get("tls", []) for host in entry.get("hosts", [])
    }
    if not rules or any(rule.get("host") != hostname for rule in rules) or tls_hosts != {hostname}:
        errors.append("Ingress rules and TLS hosts must exactly match the profile hostname")

    network_policy = by_kind["NetworkPolicy"].get("spec", {})
    ingress_namespaces = [
        peer.get("namespaceSelector", {}).get("matchLabels", {}).get("kubernetes.io/metadata.name")
        for rule in network_policy.get("ingress", [])
        for peer in rule.get("from", [])
        if "namespaceSelector" in peer
    ]
    if ingress_namespaces != [ingress_namespace]:
        errors.append("NetworkPolicy ingress namespace must exactly match the operator profile")
    redis_networks = set()
    for rule in network_policy.get("egress", []):
        ports = {port.get("port") for port in rule.get("ports", [])}
        if 6380 in ports:
            for destination in rule.get("to", []):
                cidr = destination.get("ipBlock", {}).get("cidr")
                if cidr:
                    redis_networks.add(cidr)
    if redis_networks != set(profile["redis_cidrs"]):
        errors.append("Redis TLS egress CIDRs must exactly match the operator profile")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Rendered Kubernetes YAML")
    parser.add_argument("--profile", required=True, help="Operator-owned cluster profile JSON")
    args = parser.parse_args()
    errors = validate(args.manifest, args.profile)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Rendered Kubernetes manifest matches the operator cluster profile.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
