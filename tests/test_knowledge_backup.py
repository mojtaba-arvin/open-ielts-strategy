import tempfile
import unittest
from pathlib import Path

from open_ielts_strategy.knowledge_backup import backup_database, restore_database
from open_ielts_strategy.knowledge_store import KnowledgeStore


class KnowledgeBackupTests(unittest.TestCase):
    def test_backup_and_restore_preserve_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "private" / "knowledge.sqlite3"
            with KnowledgeStore(db) as store:
                store.ingest_text("My original IELTS strategy note.", title="Private")
            backup = root / "backups" / "library.sqlite3"
            self.assertEqual(backup_database(db, backup)["integrity"], "ok")
            restored = root / "restore" / "knowledge.sqlite3"
            self.assertEqual(restore_database(backup, restored)["integrity"], "ok")
            with KnowledgeStore(restored) as store:
                self.assertEqual(store.list_sources()[0]["title"], "Private")

    def test_backup_refuses_overwrite_and_same_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "private" / "knowledge.sqlite3"
            with KnowledgeStore(db):
                pass
            backup = root / "backups" / "copy.sqlite3"
            backup_database(db, backup)
            with self.assertRaises(FileExistsError):
                backup_database(db, backup)
            with self.assertRaises(ValueError):
                backup_database(db, db)
