import json
import os
import unittest
from unittest.mock import patch

from open_ielts_strategy.api_extraction import OpenAICompatibleProvider
from open_ielts_strategy.provider_registry import ProviderRegistry, build_extraction_provider
from open_ielts_strategy.semantic_extraction import ExtractionError


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=-1):
        return self.payload[:limit]


def response_for(source):
    result = {
        "summary": "Candidate note.",
        "items": [{
            "kind": "recommendation", "text": source,
            "start_char": 0, "end_char": len(source),
            "topic_tags": ["speaking"], "rationale": "Exact source span.",
        }],
    }
    return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}]}


class ExtractionProviderTests(unittest.TestCase):
    def test_registry_registers_and_constructs_providers(self):
        registry = ProviderRegistry()
        registry.register("fake", lambda value: value)
        self.assertEqual(registry.names, ("fake",))
        self.assertEqual(registry.create("fake", value=42), 42)
        with self.assertRaises(ValueError):
            registry.register("fake", lambda: None)
        with self.assertRaises(ValueError):
            registry.create("missing")
        self.assertIsInstance(build_extraction_provider("ollama", model="qwen3:8b"), object)

    def test_remote_provider_requires_explicit_https_and_env_key(self):
        with self.assertRaises(ValueError):
            OpenAICompatibleProvider("model", endpoint="http://api.example.com/v1/chat/completions")
        provider = OpenAICompatibleProvider("model", api_key_env="TEST_IOS_API_KEY", max_retries=0)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ExtractionError, "environment variable"):
                provider.extract("A source sentence.")

    def test_remote_provider_validates_exact_source_spans(self):
        source = "Use a direct answer."
        provider = OpenAICompatibleProvider("model", api_key_env="TEST_IOS_API_KEY", max_retries=0)
        with patch.dict(os.environ, {"TEST_IOS_API_KEY": "test-secret"}):
            with patch("open_ielts_strategy.api_extraction.urllib.request.urlopen",
                       return_value=FakeResponse(response_for(source))) as call:
                result = provider.extract(source)
        self.assertEqual(result["items"][0]["status"], "needs_review")
        self.assertFalse(result["claim_eligible"])
        request = call.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
        self.assertNotIn("test-secret", request.data.decode())

    def test_remote_provider_rejects_bad_source_offsets(self):
        source = "Use a direct answer."
        payload = response_for(source)
        item = json.loads(payload["choices"][0]["message"]["content"])["items"][0]
        item["start_char"] = 1
        payload["choices"][0]["message"]["content"] = json.dumps(
            json.loads(payload["choices"][0]["message"]["content"]) | {"items": [item]}
        )
        provider = OpenAICompatibleProvider("model", api_key_env="TEST_IOS_API_KEY", max_retries=0)
        with patch.dict(os.environ, {"TEST_IOS_API_KEY": "secret"}):
            with patch("open_ielts_strategy.api_extraction.urllib.request.urlopen",
                       return_value=FakeResponse(payload)):
                with self.assertRaises(ExtractionError):
                    provider.extract(source)

    def test_remote_provider_retries_transient_server_errors(self):
        source = "A source sentence."
        provider = OpenAICompatibleProvider("model", api_key_env="TEST_IOS_API_KEY", max_retries=1)
        from urllib.error import HTTPError
        error = HTTPError(provider.endpoint, 503, "unavailable", {}, None)
        with patch.dict(os.environ, {"TEST_IOS_API_KEY": "secret"}):
            with patch("open_ielts_strategy.api_extraction.urllib.request.urlopen",
                       side_effect=[error, FakeResponse(response_for(source))]) as call:
                with patch("open_ielts_strategy.api_extraction.time.sleep"):
                    result = provider.extract(source)
        self.assertEqual(result["items"][0]["text"], source)
        self.assertEqual(call.call_count, 2)


if __name__ == "__main__":
    unittest.main()
