import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class KnowledgeCliDocumentTests(unittest.TestCase):
    def test_docx_import_through_existing_ingest_command(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docx = root / "notes.docx"
            xml = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:body><w:p><w:r><w:t>IELTS Writing Task 2 plan before drafting.</w:t></w:r></w:p></w:body></w:document>"""
            with zipfile.ZipFile(docx, "w") as archive:
                archive.writestr("word/document.xml", xml)
            db = root / "private" / "knowledge.sqlite3"
            result = subprocess.run(
                [sys.executable, "scripts/knowledge.py", "--db", str(db), "ingest",
                 str(docx), "--title", "DOCX notes", "--type", "personal_notes"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["segment_count"], 1)
            listing = subprocess.run(
                [sys.executable, "scripts/knowledge.py", "--db", str(db), "sources"],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(listing.returncode, 0, listing.stderr)
            self.assertEqual(json.loads(listing.stdout)[0]["title"], "DOCX notes")

    def test_unsupported_document_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audio.mp3"
            path.write_bytes(b"not a transcript")
            result = subprocess.run(
                [sys.executable, "scripts/knowledge.py", "--db", str(Path(tmp) / "db.sqlite3"),
                 "ingest", str(path)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("supported formats", result.stderr)
