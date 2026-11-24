import os
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
            if os.name != "nt":
                self.assertEqual(backup.parent.stat().st_mode & 0o777, 0o700)
                self.assertEqual(restored.parent.stat().st_mode & 0o777, 0o700)
                self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
                self.assertEqual(restored.stat().st_mode & 0o777, 0o600)

    def test_backup_and_restore_do_not_change_existing_directory_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shared = root / "shared"
            shared.mkdir(mode=0o755)
            if os.name != "nt":
                shared.chmod(0o755)
            db = root / "private" / "knowledge.sqlite3"
            with KnowledgeStore(db):
                pass

            backup = shared / "backup.sqlite3"
            backup_database(db, backup)
            restored = shared / "restored.sqlite3"
            restore_database(backup, restored)

            if os.name != "nt":
                self.assertEqual(shared.stat().st_mode & 0o777, 0o755)

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


if __name__ == "__main__":
    unittest.main()
