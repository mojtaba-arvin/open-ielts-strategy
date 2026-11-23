import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from open_ielts_strategy.embedding_providers import OpenAICompatibleEmbeddingProvider


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def read(self, limit):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.request = None
        self.timeout = None

    def open(self, request, timeout):
        self.request = request
        self.timeout = timeout
        if self.error:
            raise self.error
        return FakeResponse(self.payload)


class RemoteEmbeddingProviderTests(unittest.TestCase):
    def test_https_provider_orders_vectors_and_uses_environment_secret(self):
        opener = FakeOpener({"data": [
            {"index": 1, "embedding": [0.0, 1.0]},
            {"index": 0, "embedding": [1.0, 0.0]},
        ]})
        with patch.dict(os.environ, {"TEST_EMBEDDING_KEY": "secret-value"}):
            provider = OpenAICompatibleEmbeddingProvider(
                model="embedding-model-v1", api_key_env="TEST_EMBEDDING_KEY",
                opener=opener, sleeper=lambda _: None,
            )
        vectors = provider.encode(["first text", "second text"])
        self.assertEqual(vectors, [[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(opener.request.get_header("Authorization"), "Bearer secret-value")
        self.assertEqual(opener.timeout, 20.0)

    def test_provider_rejects_insecure_endpoint_and_missing_secret(self):
        with patch.dict(os.environ, {"TEST_EMBEDDING_KEY": "secret-value"}):
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                OpenAICompatibleEmbeddingProvider(
                    model="m", endpoint="http://example.com/embeddings",
                    api_key_env="TEST_EMBEDDING_KEY",
                )
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "TEST_EMBEDDING_KEY"):
                OpenAICompatibleEmbeddingProvider(model="m", api_key_env="TEST_EMBEDDING_KEY")

    def test_provider_does_not_follow_redirects(self):
        opener = FakeOpener(error=HTTPError("https://example.com", 302, "redirect", {}, None))
        with patch.dict(os.environ, {"TEST_EMBEDDING_KEY": "secret-value"}):
            provider = OpenAICompatibleEmbeddingProvider(
                model="m", api_key_env="TEST_EMBEDDING_KEY", opener=opener,
                max_retries=3, sleeper=lambda _: None,
            )
        with self.assertRaisesRegex(ValueError, "HTTP 302"):
            provider.encode(["text"])

    def test_provider_rejects_unbounded_or_malformed_vectors(self):
        with patch.dict(os.environ, {"TEST_EMBEDDING_KEY": "secret-value"}):
            provider = OpenAICompatibleEmbeddingProvider(
                model="m", api_key_env="TEST_EMBEDDING_KEY",
                opener=FakeOpener({"data": [{"index": 0, "embedding": [1.0]}]}),
            )
        with self.assertRaisesRegex(ValueError, "1..64"):
            provider.encode([])
        with self.assertRaisesRegex(ValueError, "10000"):
            provider.encode(["x" * 10001])
        bad = FakeOpener({"data": [{"index": 0, "embedding": [float("nan")]}]})
        provider._opener = bad
        with self.assertRaisesRegex(ValueError, "non-finite"):
            provider.encode(["valid input"])


if __name__ == "__main__":
    unittest.main()
