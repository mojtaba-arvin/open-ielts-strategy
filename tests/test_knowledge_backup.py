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

    def test_failed_backup_removes_reserved_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid_source = root / "invalid.sqlite3"
            invalid_source.write_bytes(b"not a SQLite database")
            destination = root / "backups" / "copy.sqlite3"

            with self.assertRaises(sqlite3.DatabaseError):
                backup_database(invalid_source, destination)

            self.assertFalse(destination.exists())
            self.assertTrue(invalid_source.exists())

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

    def test_backup_captures_committed_wal_data_and_restores_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "private" / "knowledge.sqlite3"
            source.parent.mkdir()
            with sqlite3.connect(source) as connection:
                self.assertEqual(connection.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
                connection.execute("CREATE TABLE recovery_probe (value TEXT NOT NULL)")
                connection.execute("INSERT INTO recovery_probe VALUES (?)", ("committed-in-wal",))
                connection.commit()

            # The committed row is deliberately not checkpointed before backup.
            backup = root / "backups" / "wal-snapshot.sqlite3"
            result = backup_database(source, backup)
            self.assertEqual(result["integrity"], "ok")

            restored = root / "restore" / "knowledge.sqlite3"
            restore_result = restore_database(backup, restored)
            self.assertEqual(restore_result["integrity"], "ok")
            with sqlite3.connect(restored) as connection:
                self.assertEqual(
                    connection.execute("SELECT value FROM recovery_probe").fetchone()[0],
                    "committed-in-wal",
                )
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")

            # A backup is a snapshot; creating it must not mutate the live source.
            with sqlite3.connect(source) as connection:
                self.assertEqual(
                    connection.execute("SELECT value FROM recovery_probe").fetchone()[0],
                    "committed-in-wal",
                )
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")


if __name__ == "__main__":
    unittest.main()
