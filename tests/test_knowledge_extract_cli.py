import unittest
from scripts.knowledge_extract import build_parser


class KnowledgeExtractCliTests(unittest.TestCase):
    def test_model_and_source_are_explicit(self):
        args = build_parser().parse_args(["--source-id", "src_test", "--model", "qwen3:8b"])
        self.assertEqual(args.source_id, "src_test")
        self.assertEqual(args.model, "qwen3:8b")
        self.assertEqual(args.endpoint, "http://127.0.0.1:11434/api/generate")

    def test_endpoint_can_only_be_local_at_provider_boundary(self):
        args = build_parser().parse_args([
            "--source-id", "src_test", "--model", "qwen3:8b",
            "--endpoint", "https://remote.example/api",
        ])
        self.assertEqual(args.endpoint, "https://remote.example/api")
