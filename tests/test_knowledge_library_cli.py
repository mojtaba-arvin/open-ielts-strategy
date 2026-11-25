import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from open_ielts_strategy.knowledge_library_cli import main


class KnowledgeLibraryCliTests(unittest.TestCase):
    def test_private_ingest_and_search_use_the_selected_local_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "private" / "knowledge.sqlite3"
            output = io.StringIO()
            with patch("sys.stdin", io.StringIO("A useful speaking answer starts with a direct response.")):
                with redirect_stdout(output):
                    self.assertEqual(main([
                        "--db", str(database), "ingest", "-",
                        "--title", "Speaking notes",
                        "--type", "personal_notes",
                        "--rights-status", "self_authored",
                    ]), 0)

            imported = json.loads(output.getvalue())
            self.assertTrue(imported["source_id"].startswith("src_"))
            self.assertTrue(database.is_file())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([
                    "--db", str(database), "search", "direct response",
                ]), 0)

            results = json.loads(output.getvalue())
            self.assertTrue(results)
            self.assertIn("direct response", results[0]["text"].casefold())


if __name__ == "__main__":
    unittest.main()
