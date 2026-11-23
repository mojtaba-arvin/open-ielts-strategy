import unittest
from open_ielts_strategy.knowledge_web import make_handler


class KnowledgeWebTests(unittest.TestCase):
    def test_handler_is_constructible_without_starting_a_server(self):
        handler = make_handler(":memory:")
        self.assertTrue(hasattr(handler, "do_GET"))
        self.assertTrue(hasattr(handler, "do_POST"))

    def test_ui_module_exposes_loopback_server_only(self):
        from open_ielts_strategy.knowledge_web import serve
        with self.assertRaises(ValueError):
            serve(":memory:", host="0.0.0.0", port=0)
