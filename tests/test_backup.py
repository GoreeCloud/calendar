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

    def test_independent_backup_verification(self):
        from calendar_app.backup import verify_backup
        with tempfile.TemporaryDirectory() as folder:
            source=str(Path(folder)/"live.db")
            good=str(Path(folder)/"good.db")
            create_user(source,"secure@example.org","a-long-secure-password-123")
            backup_database(source,good)
            self.assertTrue(verify_backup(good))
            bad=Path(folder)/"corrupted.db"
            bad.write_bytes(b"not a sqlite file")
            with self.assertRaises(ValueError):
                verify_backup(str(bad))
            with self.assertRaises(ValueError):
                verify_backup(str(Path(folder)/"missing.db"))


    def test_restore_to_new_database_preserves_calendar_and_tasks(self):
        from calendar_app.backup import restore_database,verify_backup
        from calendar_app.core import now
        with tempfile.TemporaryDirectory() as folder:
            source=str(Path(folder)/"live.db")
            snapshot=str(Path(folder)/"snapshot.db")
            restored=str(Path(folder)/"restored.db")
            create_user(source,"restore@example.test","long-enough-password-123")
            with database(source) as db:
                cid=db.execute("SELECT id FROM calendars LIMIT 1").fetchone()[0]
                db.execute("INSERT INTO events "
                           "(id,calendar_id,title,description,location,start_at,end_at,all_day,"
                           "version,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           ("e",cid,"Recovered appointment","","","2026-11-10T12:00:00Z",
                            "2026-11-10T13:00:00Z",0,1,now(),now()))
                db.execute("INSERT INTO tasks "
                           "(id,calendar_id,title,due_at,done,created_at,updated_at,priority) "
                           "VALUES(?,?,?,?,?,?,?,?)",
                           ("t",cid,"Recovered task",None,0,now(),now(),1))
                db.execute("INSERT INTO imported_task_uids VALUES(?,?,?)",
                           (cid,"restored-task@example.test","t"))
            backup_database(source,snapshot)
            restore_database(snapshot,restored)
            self.assertTrue(verify_backup(restored))
            with sqlite3.connect(restored) as db:
                self.assertEqual(db.execute("SELECT title FROM events").fetchone()[0],
                                 "Recovered appointment")
                self.assertEqual(db.execute("SELECT title,priority FROM tasks").fetchone(),
                                 ("Recovered task",1))
                self.assertEqual(db.execute(
                    "SELECT external_uid FROM imported_task_uids WHERE task_id='t'").fetchone()[0],
                    "restored-task@example.test")
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(),[])
            old=Path(restored).read_bytes()
            with self.assertRaises(FileExistsError):
                restore_database(snapshot,restored)
            self.assertEqual(old,Path(restored).read_bytes())
            self.assertTrue(Path(source).is_file())
            self.assertTrue(Path(snapshot).is_file())

    def test_restore_rejects_corrupt_snapshot_without_publishing(self):
        from calendar_app.backup import restore_database
        with tempfile.TemporaryDirectory() as folder:
            broken=Path(folder)/"corrupt.db"
            broken.write_bytes(b"not sqlite")
            dest=Path(folder)/"destination.db"
            with self.assertRaises(ValueError):
                restore_database(str(broken),str(dest))
            self.assertFalse(dest.exists())
            source=Path(folder)/"symlink.db"
            source.symlink_to(broken)
            with self.assertRaises(ValueError):
                restore_database(str(source),str(dest))

    def test_rejects_missing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                backup_database(str(Path(folder)/"missing.db"), str(Path(folder)/"backup.db"))

    def test_backup_rejects_broken_foreign_key_references(self):
        from calendar_app.backup import verify_backup,restore_database
        with tempfile.TemporaryDirectory() as folder:
            broken=str(Path(folder)/"broken-relations.db")
            create_user(broken,"foreign-key@example.test","long-enough-password-123")
            with sqlite3.connect(broken) as db:
                db.execute("PRAGMA foreign_keys=OFF")
                db.execute("DELETE FROM users")
                db.commit()
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0],"ok")
                self.assertNotEqual(db.execute("PRAGMA foreign_key_check").fetchone(),None)
            with self.assertRaises(ValueError):
                verify_backup(broken)
            destination=str(Path(folder)/"recover.db")
            with self.assertRaises(ValueError):
                restore_database(broken,destination)
            self.assertFalse(Path(destination).exists())

    def test_database_context_closes_and_rolls_back_on_error(self):
        from calendar_app.core import database
        with tempfile.TemporaryDirectory() as folder:
            source=str(Path(folder)/"rollback.db")
            create_user(source,"db-close@example.test","long-enough-password-123")
            with database(source) as conn:
                conn.execute("UPDATE calendars SET name='Committed'")
            with self.assertRaises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")
            with self.assertRaises(RuntimeError):
                with database(source) as transaction:
                    transaction.execute("UPDATE calendars SET name='Rolled back'")
                    raise RuntimeError("Abort transaction")
            with self.assertRaises(sqlite3.ProgrammingError):
                transaction.execute("SELECT 1")
            with database(source) as check:
                self.assertEqual(check.execute("SELECT name FROM calendars").fetchone()[0],
                                 "Committed")

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
