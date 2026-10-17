"""Offline private-store safety and recovery rehearsal tests (no network/credentials)."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from private_storage import (
    backup_database, prepare_database, restore_rehearsal, verify_backup,
)


class PrivateStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.live = self.root / "live"
        self.live.mkdir(mode=0o700)
        self.database = self.live / "family.sqlite"
        prepare_database(str(self.database))
        with sqlite3.connect(self.database) as con:
            con.execute("CREATE TABLE learners (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
            con.execute("INSERT INTO learners(name) VALUES('Private learner')")
        self.backups = self.root / "backups"

    def tearDown(self):
        self.temp.cleanup()

    def test_database_creation_is_private(self):
        self.assertTrue(self.database.is_file())
        if os.name == "posix":
            self.assertEqual(self.database.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.live.stat().st_mode & 0o777, 0o700)

    def test_snapshot_verify_and_recover_to_new_file(self):
        snapshot = backup_database(str(self.database), str(self.backups))
        report = verify_backup(str(snapshot))
        self.assertEqual(report["filename"], snapshot.name)
        self.assertGreater(report["size"], 0)
        self.assertEqual(len(report["sha256"]), 64)
        manifest = snapshot.with_name(snapshot.name + ".json")
        self.assertNotIn("Private learner", manifest.read_text())
        restored = restore_rehearsal(str(snapshot), str(self.root / "restore" / "recovered.sqlite"))
        with sqlite3.connect(restored) as con:
            self.assertEqual(con.execute("SELECT name FROM learners").fetchone()[0], "Private learner")
        if os.name == "posix":
            self.assertEqual(snapshot.stat().st_mode & 0o777, 0o600)
            self.assertEqual(manifest.stat().st_mode & 0o777, 0o600)
            self.assertEqual(restored.stat().st_mode & 0o777, 0o600)

    def test_backup_includes_committed_wal_transactions(self):
        with sqlite3.connect(self.database) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("INSERT INTO learners(name) VALUES('Later learner')")
            writer.commit()
            snapshot = backup_database(str(self.database), str(self.backups))
        recovered = restore_rehearsal(str(snapshot), str(self.root / "restore" / "from-wal.sqlite"))
        with sqlite3.connect(recovered) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM learners").fetchone()[0], 2)

    def test_mutated_bytes_and_manifest_are_rejected(self):
        snapshot = backup_database(str(self.database), str(self.backups))
        with snapshot.open("r+b") as stream:
            stream.seek(150)
            stream.write(b"tamper")
        with self.assertRaises(ValueError):
            verify_backup(str(snapshot))
        with self.assertRaises(ValueError):
            restore_rehearsal(str(snapshot), str(self.root / "bad.sqlite"))
        self.assertFalse((self.root / "bad.sqlite").exists())

    def test_restore_must_not_overwrite_existing_database(self):
        snapshot = backup_database(str(self.database), str(self.backups))
        with self.assertRaises(FileExistsError):
            restore_rehearsal(str(snapshot), str(self.database))
        with sqlite3.connect(self.database) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM learners").fetchone()[0], 1)

    @unittest.skipUnless(os.name == "posix", "POSIX permissions only")
    def test_insecure_existing_data_is_rejected_not_silently_chmodded(self):
        self.database.chmod(0o644)
        with self.assertRaises(PermissionError):
            prepare_database(str(self.database))
        with self.assertRaises(PermissionError):
            backup_database(str(self.database), str(self.backups))
        self.database.chmod(0o600)
        self.live.chmod(0o755)
        with self.assertRaises(PermissionError):
            prepare_database(str(self.database))

    @unittest.skipUnless(os.name == "posix", "POSIX symlink checks only")
    def test_symlinked_database_and_backup_roots_are_rejected(self):
        alias = self.live / "alias.sqlite"
        alias.symlink_to(self.database)
        with self.assertRaises(ValueError):
            prepare_database(str(alias))
        with self.assertRaises(ValueError):
            backup_database(str(alias), str(self.backups))
        shortcut = self.root / "backups-link"
        self.backups.mkdir(mode=0o700)
        shortcut.symlink_to(self.backups, target_is_directory=True)
        with self.assertRaises(ValueError):
            backup_database(str(self.database), str(shortcut))

    def test_invalid_manifest_does_not_allow_recovery(self):
        snapshot = backup_database(str(self.database), str(self.backups))
        manifest = snapshot.with_name(snapshot.name + ".json")
        data = json.loads(manifest.read_text())
        data["size"] += 1
        manifest.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            verify_backup(str(snapshot))


if __name__ == "__main__":
    unittest.main()
