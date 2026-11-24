import unittest
from unittest.mock import patch
from open_ielts_strategy.integration_adapters_cli import inspect_adapters

class AdapterStatusTests(unittest.TestCase):
    def test_reports_all_capabilities_without_loading_provider_code(self):
        with patch("open_ielts_strategy.integration_adapters_cli.discover_adapters", return_value=()):
            result = inspect_adapters()
        self.assertFalse(result["provider_code_loaded"])
        self.assertTrue(result["capabilities"])
        self.assertTrue(all(value["status"] == "unavailable" for value in result["capabilities"].values()))
