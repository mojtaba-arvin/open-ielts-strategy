import json
import os
import tempfile
import unittest
from pathlib import Path
from open_ielts_strategy.knowledge_authoring import initialize_workspace
from open_ielts_strategy.knowledge_pack import KnowledgePackError

class KnowledgeAuthoringTests(unittest.TestCase):
    def test_creates_draft_not_published_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            result = initialize_workspace(root)
            self.assertTrue(result["created"])
            self.assertFalse(result["published_pack_created"])
            self.assertFalse((root / "manifest.json").exists())
            draft = json.loads((root / "drafts/strategy.template.json").read_text())
            self.assertEqual(draft["review"], {"content_status": "draft", "publication_status": "pending"})
            self.assertIn("CHOOSE_", draft["provenance"]["basis"])
            if os.name != "nt":
                self.assertEqual(root.stat().st_mode & 0o777, 0o700)
                self.assertEqual((root / "drafts/strategy.template.json").stat().st_mode & 0o777, 0o600)

    def test_refuses_existing_directory_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            marker = root / "keep"
            marker.write_text("keep")
            with self.assertRaisesRegex(KnowledgePackError, "already exists"):
                initialize_workspace(root)
            self.assertEqual(marker.read_text(), "keep")
