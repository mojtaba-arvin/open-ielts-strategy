import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from open_ielts_strategy.text_generation import (
    GenerationError, OpenAICompatibleTextProvider, OllamaTextProvider,
)


class FakeResponse:
    def __init__(self, value):
        self.value = json.dumps(value).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=-1):
        return self.value[:limit]


class TextGenerationProviderTests(unittest.TestCase):
    def test_remote_generation_uses_env_credential_and_structured_json_mode(self):
        provider = OpenAICompatibleTextProvider("model", api_key_env="TEST_ANSWER_KEY", max_retries=0)
        payload = {"choices": [{"finish_reason": "stop", "message": {"content": "{\"answer\":\"A grounded answer.\"}"}}]}
        with patch.dict(os.environ, {"TEST_ANSWER_KEY": "test-secret"}):
            with patch("open_ielts_strategy.text_generation.urllib.request.build_opener") as build:
                build.return_value.open.return_value = FakeResponse(payload)
                result = provider.generate("Use only the public Knowledge Pack.")
                request = build.return_value.open.call_args.args[0]
        self.assertEqual(result, "{\"answer\":\"A grounded answer.\"}")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
        self.assertNotIn("test-secret", request.data.decode())
        self.assertEqual(json.loads(request.data)["response_format"], {"type": "json_object"})

    def test_remote_generation_requires_key_and_does_not_follow_redirects(self):
        provider = OpenAICompatibleTextProvider("model", api_key_env="TEST_ANSWER_KEY", max_retries=0)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(GenerationError):
                provider.generate("Prompt.")
        with patch.dict(os.environ, {"TEST_ANSWER_KEY": "secret"}):
            with patch("open_ielts_strategy.text_generation.urllib.request.build_opener") as build:
                build.return_value.open.side_effect = HTTPError(provider.endpoint, 302, "redirect", {}, None)
                with self.assertRaisesRegex(GenerationError, "HTTP 302"):
                    provider.generate("Prompt.")

    def test_local_provider_rejects_non_loopback_endpoint(self):
        with self.assertRaises(ValueError):
            OllamaTextProvider("model", endpoint="http://192.0.2.1:11434/api/generate")


if __name__ == "__main__":
    unittest.main()
