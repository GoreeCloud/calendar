"""Test SQLite online backup correctness and no-clobber behavior."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from calendar_app.backup import backup_database
from calendar_app.core import create_user, database

class BackupTests(unittest.TestCase):
    def test_snapshot_contains_users_and_fails_closed_when_target_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            source = str(Path(folder) / "live.db")
            output = str(Path(folder) / "backup.db")
            create_user(source, "test@example.org", "long-enough-password-123")
            backup_database(source, output)
            with sqlite3.connect(output) as copy:
                user = copy.execute("SELECT email FROM users").fetchone()
                self.assertEqual(user, ("test@example.org",))
                self.assertEqual(copy.execute("PRAGMA integrity_check").fetchone(), ("ok",))
            data = Path(output).read_bytes()
            with self.assertRaises(FileExistsError):
                backup_database(source, output)
            self.assertEqual(Path(output).read_bytes(), data)

    def test_rejects_missing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                backup_database(str(Path(folder)/"missing.db"), str(Path(folder)/"backup.db"))

    def test_snapshot_includes_live_wal_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            source=str(Path(folder)/"live.db")
            output=str(Path(folder)/"backup.db")
            create_user(source,"test@example.org","long-enough-password-123")
            with database(source) as db:
                db.execute("UPDATE calendars SET name='Updated' WHERE name='Personal'")
            backup_database(source,output)
            with sqlite3.connect(output) as db:
                self.assertEqual(db.execute("SELECT name FROM calendars").fetchone()[0],"Updated")
if __name__=="__main__":
    unittest.main()
