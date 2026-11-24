import os
import sqlite3
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

    def test_backup_refuses_dangling_symlink_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "private" / "knowledge.sqlite3"
            with KnowledgeStore(db):
                pass
            backup_dir = root / "backups"
            backup_dir.mkdir()
            destination = backup_dir / "backup.sqlite3"
            target = root / "outside.sqlite3"
            try:
                destination.symlink_to(target)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaises(FileExistsError):
                backup_database(db, destination)
            self.assertTrue(destination.is_symlink())
            self.assertFalse(target.exists())

    def test_restore_refuses_dangling_symlink_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "private" / "knowledge.sqlite3"
            with KnowledgeStore(db):
                pass
            backup = root / "backups" / "backup.sqlite3"
            backup_database(db, backup)
            restore_dir = root / "restore"
            restore_dir.mkdir()
            destination = restore_dir / "knowledge.sqlite3"
            target = root / "outside.sqlite3"
            try:
                destination.symlink_to(target)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaises(FileExistsError):
                restore_database(backup, destination)
            self.assertTrue(destination.is_symlink())
            self.assertFalse(target.exists())

    def test_restore_removes_reserved_destination_when_backup_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid_backup = root / "invalid.sqlite3"
            invalid_backup.write_bytes(b"not a SQLite database")
            destination = root / "restore" / "knowledge.sqlite3"

            with self.assertRaises(sqlite3.DatabaseError):
                restore_database(invalid_backup, destination)

            self.assertFalse(destination.exists())
            self.assertTrue(invalid_backup.exists())


if __name__ == "__main__":
    unittest.main()
