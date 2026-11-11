"""Regression coverage for upgrades from the original two-role sharing schema."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from calendar_app.core import SCHEMA, init_database

class LegacyMembershipMigrationTests(unittest.TestCase):
    def test_old_memberships_are_preserved_and_freebusy_role_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/"old.sqlite3")
            legacy=SCHEMA.replace(
                "CHECK(role IN ('read','edit','freebusy'))",
                "CHECK(role IN ('read','edit'))")
            with sqlite3.connect(path) as conn:
                conn.executescript(legacy)
                conn.execute("INSERT INTO users VALUES(?,?,?,?,?)",
                             ("owner","owner@example.test","salt","hash","2026-11-10T00:00:00Z"))
                conn.execute("INSERT INTO users VALUES(?,?,?,?,?)",
                             ("member","member@example.test","salt","hash","2026-11-10T00:00:00Z"))
                conn.execute("INSERT INTO calendars VALUES(?,?,?,?,?,?)",
                             ("cal","owner","Personal","#6475de","","2026-11-10T00:00:00Z"))
                conn.execute("INSERT INTO calendar_members VALUES(?,?,?,?)",
                             ("cal","member","read","2026-11-10T00:00:00Z"))
            init_database(path)
            with sqlite3.connect(path) as conn:
                self.assertEqual(conn.execute("SELECT role FROM calendar_members").fetchone()[0],"read")
                conn.execute("UPDATE calendar_members SET role='freebusy' WHERE user_id='member'")
                conn.commit()
            init_database(path)
            with sqlite3.connect(path) as conn:
                self.assertEqual(conn.execute("SELECT role FROM calendar_members").fetchone()[0],"freebusy")
                self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")
                self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(),[])

    def test_legacy_task_priority_migration_preserves_tasks(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/"old-tasks.sqlite3")
            legacy=SCHEMA.replace(
                "  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,\n"
                "  priority INTEGER NOT NULL DEFAULT 3 CHECK(priority BETWEEN 1 AND 4),\n"
                "  version INTEGER NOT NULL DEFAULT 1 CHECK(version >= 1)\n"
                ");\nCREATE INDEX IF NOT EXISTS idx_tasks_calendar",
                "  created_at TEXT NOT NULL, updated_at TEXT NOT NULL\n"
                ");\nCREATE INDEX IF NOT EXISTS idx_tasks_calendar")
            old_task_ddl=legacy.split("CREATE TABLE IF NOT EXISTS tasks (",1)[1].split(");",1)[0]
            self.assertNotIn("priority INTEGER",old_task_ddl)
            self.assertNotIn("version INTEGER",old_task_ddl)
            with sqlite3.connect(path) as conn:
                conn.executescript(legacy)
                conn.execute("INSERT INTO users VALUES(?,?,?,?,?)",
                             ("owner","owner@example.test","salt","hash","2026-11-10T00:00:00Z"))
                conn.execute("INSERT INTO calendars VALUES(?,?,?,?,?,?)",
                             ("cal","owner","Personal","#6475de","","2026-11-10T00:00:00Z"))
                conn.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?)",
                             ("task","cal","Legacy task",None,0,"2026-11-10T00:00:00Z",
                              "2026-11-10T00:00:00Z"))
            init_database(path)
            with sqlite3.connect(path) as conn:
                saved=conn.execute("SELECT title,priority FROM tasks WHERE id='task'").fetchone()
                self.assertEqual(saved,("Legacy task",3))
                self.assertEqual(conn.execute(
                    "SELECT version FROM tasks WHERE id='task'").fetchone()[0],1)
                conn.execute("UPDATE tasks SET priority=1 WHERE id='task'")
                conn.commit()
            init_database(path)
            with sqlite3.connect(path) as conn:
                self.assertEqual(conn.execute(
                    "SELECT priority FROM tasks WHERE id='task'").fetchone()[0],1)
                self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")
                self.assertEqual(conn.execute(
                    "SELECT version FROM tasks WHERE id='task'").fetchone()[0],1)

    def test_pre_vtodo_database_creates_uid_ledger_without_data_loss(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/"old-before-vtodo.sqlite3")
            legacy=SCHEMA.split("CREATE TABLE IF NOT EXISTS imported_task_uids (",1)[0]
            self.assertNotIn("imported_task_uids",legacy)
            with sqlite3.connect(path) as db:
                db.executescript(legacy)
                db.execute("INSERT INTO users VALUES(?,?,?,?,?)",
                    ("owner","owner@example.test","salt","hash","2026-11-10T00:00:00Z"))
                db.execute("INSERT INTO calendars VALUES(?,?,?,?,?,?)",
                    ("cal","owner","Personal","#6475de","","2026-11-10T00:00:00Z"))
                db.execute("INSERT INTO tasks "
                    "(id,calendar_id,title,due_at,done,created_at,updated_at,priority,version) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    ("task","cal","Keep my old task",None,0,
                     "2026-11-10T00:00:00Z","2026-11-10T00:00:00Z",3,1))
            init_database(path)
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute(
                    "SELECT title FROM tasks WHERE id='task'").fetchone()[0],
                    "Keep my old task")
                db.execute("INSERT INTO imported_task_uids VALUES(?,?,?)",
                           ("cal","example-task@example.test","task"))
                db.commit()
            init_database(path)
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT task_id FROM imported_task_uids "
                    "WHERE external_uid='example-task@example.test'").fetchone()[0],"task")
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(),[])
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0],"ok")

if __name__=="__main__":
    unittest.main()
