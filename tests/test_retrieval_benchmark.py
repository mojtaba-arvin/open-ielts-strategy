import unittest

from open_ielts_strategy.embedding_providers import OpenAICompatibleEmbeddingProvider
from open_ielts_strategy.retrieval_benchmark import OpenAICompatibleEmbeddingProvider as BenchmarkEmbeddingProvider
from open_ielts_strategy.retrieval_benchmark import percentile


class RetrievalBenchmarkTests(unittest.TestCase):
    def test_openai_compatible_provider_is_wired(self):
        self.assertIs(BenchmarkEmbeddingProvider, OpenAICompatibleEmbeddingProvider)

    def test_percentile_uses_nearest_rank(self):
        self.assertEqual(percentile([4.0, 1.0, 3.0, 2.0], .50), 2.0)
        self.assertEqual(percentile([4.0, 1.0, 3.0, 2.0], .95), 4.0)

    def test_percentile_rejects_empty_samples_and_invalid_quantiles(self):
        with self.assertRaisesRegex(ValueError, "empty sample"):
            percentile([], .95)
        with self.assertRaisesRegex(ValueError, "quantile"):
            percentile([1.0], 0)


if __name__ == "__main__":
    unittest.main()
