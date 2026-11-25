import json
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.validate_rendered_kubernetes_manifest import validate


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "deploy" / "kubernetes" / "published-mcp.yaml"
DIGEST = "sha256:" + "a" * 64


class RenderedKubernetesProfileTests(unittest.TestCase):
    def setUp(self):
        self.documents = list(yaml.safe_load_all(TEMPLATE.read_text(encoding="utf-8")))
        self.profile = {
            "namespace": "open-ielts",
            "ingress_namespace": "ingress-nginx",
            "hostname": "mcp.ielts.example.org",
            "oidc_auth_url": "https://auth.ielts.example.org/oauth2/auth",
            "redis_cidrs": ["10.40.2.0/24"],
            "image_digest": DIGEST,
        }
        by_kind = {item["kind"]: item for item in self.documents}
        deployment = by_kind["Deployment"]["spec"]["template"]["spec"]["containers"][0]
        deployment["image"] = "ghcr.io/mojtaba-arvin/open-ielts-strategy/published-mcp@" + DIGEST
        args = deployment["args"]
        args[args.index("published-mcp.example.com")] = self.profile["hostname"]
        args[args.index("https://client.example.com")] = "https://client.ielts.example.org"
        for probe in ("startupProbe", "readinessProbe", "livenessProbe"):
            command = deployment[probe]["exec"]["command"]
            command[-1] = command[-1].replace("published-mcp.example.com", self.profile["hostname"])
        ingress = by_kind["Ingress"]
        ingress["metadata"]["annotations"]["cert-manager.io/cluster-issuer"] = "letsencrypt-prod"
        ingress["metadata"]["annotations"]["nginx.ingress.kubernetes.io/auth-url"] = self.profile["oidc_auth_url"]
        ingress["spec"]["tls"][0]["hosts"] = [self.profile["hostname"]]
        ingress["spec"]["rules"][0]["host"] = self.profile["hostname"]
        policy = by_kind["NetworkPolicy"]["spec"]
        policy["egress"][-1]["to"][0]["ipBlock"]["cidr"] = self.profile["redis_cidrs"][0]

    def _validate(self, mutate=None, profile_mutate=None):
        documents = [dict(item) for item in self.documents]
        if mutate:
            mutate({item["kind"]: item for item in documents})
        profile = dict(self.profile)
        if profile_mutate:
            profile_mutate(profile)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "rendered.yaml"
            profile_path = root / "profile.json"
            manifest_path.write_text(yaml.safe_dump_all(documents), encoding="utf-8")
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            return validate(manifest_path, profile_path)

    def test_rendered_manifest_matching_operator_profile_passes(self):
        self.assertEqual(self._validate(), [])

    def test_hostname_mismatch_is_rejected(self):
        errors = self._validate(profile_mutate=lambda profile: profile.update({"hostname": "other.example.org"}))
        self.assertIn("application --allowed-hosts must equal the profile hostname", errors)

    def test_redis_cidr_mismatch_is_rejected(self):
        errors = self._validate(profile_mutate=lambda profile: profile.update({"redis_cidrs": ["10.41.0.0/16"]}))
        self.assertIn("Redis TLS egress CIDRs must exactly match the operator profile", errors)

    def test_mutable_or_unpinned_image_is_rejected(self):
        errors = self._validate(
            mutate=lambda resources: resources["Deployment"]["spec"]["template"]["spec"]["containers"][0].update(
                {"image": "ghcr.io/example/published-mcp:latest"}
            )
        )
        self.assertIn("application image must be pinned to the profile's immutable digest", errors)

    def test_unresolved_template_placeholders_are_rejected(self):
        errors = self._validate(
            mutate=lambda resources: resources["Ingress"]["spec"]["rules"][0].update(
                {"host": "published-mcp.example.com"}
            )
        )
        self.assertIn("rendered manifest still contains an unresolved placeholder or documentation address", errors)

    def test_profile_rejects_open_redis_cidr(self):
        errors = self._validate(profile_mutate=lambda profile: profile.update({"redis_cidrs": ["0.0.0.0/0"]}))
        self.assertTrue(any("must not allow every address" in error for error in errors))

    def test_profile_rejects_unknown_fields(self):
        errors = self._validate(profile_mutate=lambda profile: profile.update({"redis_password": "never-store-here"}))
        self.assertTrue(any("unsupported keys" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
