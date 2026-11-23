import unittest

from open_ielts_strategy.semantic_extraction import (
    ExtractionError, OllamaLocalProvider, validate_extraction,
)


class SemanticExtractionTests(unittest.TestCase):
    def setUp(self):
        self.source = "For IELTS Writing Task 2, plan before drafting."

    def item(self, kind="recommendation"):
        return {
            "kind": kind, "text": self.source, "start_char": 0,
            "end_char": len(self.source), "topic_tags": ["writing_task_2"],
            "rationale": "The source directly recommends planning.",
        }

    def test_exact_source_span_is_required(self):
        result = validate_extraction({"summary": "A planning tip.", "items": [self.item()]}, self.source)
        self.assertEqual(result["items"][0]["status"], "needs_review")
        self.assertFalse(result["claim_eligible"])

    def test_wrong_offset_and_wrong_quote_are_rejected(self):
        item = self.item()
        item["start_char"] = 1
        with self.assertRaises(ExtractionError):
            validate_extraction({"summary": "", "items": [item]}, self.source)

    def test_unknown_kind_and_extra_fields_are_rejected(self):
        item = self.item("official_band")
        with self.assertRaises(ExtractionError):
            validate_extraction({"summary": "", "items": [item]}, self.source)
        item = self.item()
        item["verified"] = True
        with self.assertRaises(ExtractionError):
            validate_extraction({"summary": "", "items": [item]}, self.source)

    def test_non_string_kind_is_rejected_cleanly(self):
        item = self.item()
        item["kind"] = []
        with self.assertRaises(ExtractionError):
            validate_extraction({"summary": "", "items": [item]}, self.source)

    def test_provider_refuses_remote_endpoints(self):
        with self.assertRaises(ValueError):
            OllamaLocalProvider("qwen", "https://example.com/api")
        with self.assertRaises(ValueError):
            OllamaLocalProvider("qwen", "http://192.168.1.10:11434/api/generate")

    def test_local_http_redirects_are_not_followed(self):
        from open_ielts_strategy.semantic_extraction import _NoRedirect
        handler = _NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "Found", {}, "https://remote.example"))

    def test_empty_or_oversized_output_is_rejected(self):
        with self.assertRaises(ExtractionError):
            validate_extraction({"summary": "", "items": []}, "")
        with self.assertRaises(ExtractionError):
            validate_extraction({"summary": "", "items": "not-list"}, self.source)
