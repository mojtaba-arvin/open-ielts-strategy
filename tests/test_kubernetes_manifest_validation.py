import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.validate_kubernetes_manifest import validate


MANIFEST = Path(__file__).resolve().parents[1] / "deploy" / "kubernetes" / "published-mcp.yaml"


class KubernetesManifestValidationTests(unittest.TestCase):
    def setUp(self):
        self.documents = list(yaml.safe_load_all(MANIFEST.read_text(encoding="utf-8")))

    def _validate_mutation(self, mutate):
        documents = [dict(item) for item in self.documents]
        by_kind = {item["kind"]: item for item in documents}
        mutate(by_kind)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.yaml"
            path.write_text(yaml.safe_dump_all(documents), encoding="utf-8")
            return validate(path)

    def test_repository_template_passes_structural_security_validation(self):
        self.assertEqual(validate(MANIFEST), [])

    def test_host_network_is_rejected(self):
        errors = self._validate_mutation(
            lambda resources: resources["Deployment"]["spec"]["template"]["spec"].update(
                {"hostNetwork": True}
            )
        )
        self.assertIn("pod hostNetwork must be disabled", errors)

    def test_host_path_volume_is_rejected(self):
        errors = self._validate_mutation(
            lambda resources: resources["Deployment"]["spec"]["template"]["spec"]["volumes"].append(
                {"name": "host", "hostPath": {"path": "/"}}
            )
        )
        self.assertIn("hostPath volumes are not allowed", errors)

    def test_ipv6_unrestricted_egress_is_rejected(self):
        errors = self._validate_mutation(
            lambda resources: resources["NetworkPolicy"]["spec"]["egress"].append(
                {"to": [{"ipBlock": {"cidr": "::/0"}}], "ports": [{"protocol": "TCP", "port": 6380}]}
            )
        )
        self.assertIn(
            "egress IP blocks must not allow every IPv4 or IPv6 destination", errors
        )

    def test_missing_resource_limits_are_rejected(self):
        errors = self._validate_mutation(
            lambda resources: resources["Deployment"]["spec"]["template"]["spec"]["containers"][0][
                "resources"
            ].pop("limits")
        )
        self.assertIn(
            "application container must define both resource requests and limits", errors
        )

    def test_service_selector_must_match_deployment(self):
        errors = self._validate_mutation(
            lambda resources: resources["Service"]["spec"]["selector"].update(
                {"app.kubernetes.io/name": "unexpected"}
            )
        )
        self.assertIn("Service selector must match the Deployment pod selector", errors)

    def test_ingress_must_target_the_expected_service(self):
        errors = self._validate_mutation(
            lambda resources: resources["Ingress"]["spec"]["rules"][0]["http"]["paths"][0][
                "backend"
            ]["service"].update({"name": "unexpected"})
        )
        self.assertIn(
            "Ingress paths must route only to the published MCP ClusterIP Service", errors
        )

    def test_ingress_policy_must_be_limited_to_expected_controller_namespace(self):
        errors = self._validate_mutation(
            lambda resources: resources["NetworkPolicy"]["spec"]["ingress"][0]["from"][0][
                "namespaceSelector"
            ]["matchLabels"].update({"kubernetes.io/metadata.name": "default"})
        )
        self.assertIn(
            "NetworkPolicy ingress must be limited to the ingress-nginx namespace", errors
        )


if __name__ == "__main__":
    unittest.main()
