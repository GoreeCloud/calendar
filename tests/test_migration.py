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
                "  priority INTEGER NOT NULL DEFAULT 3 CHECK(priority BETWEEN 1 AND 4)\n"
                ");\nCREATE INDEX IF NOT EXISTS idx_tasks_calendar",
                "  created_at TEXT NOT NULL, updated_at TEXT NOT NULL\n"
                ");\nCREATE INDEX IF NOT EXISTS idx_tasks_calendar")
            self.assertNotIn("priority INTEGER",legacy)
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
                conn.execute("UPDATE tasks SET priority=1 WHERE id='task'")
                conn.commit()
            init_database(path)
            with sqlite3.connect(path) as conn:
                self.assertEqual(conn.execute(
                    "SELECT priority FROM tasks WHERE id='task'").fetchone()[0],1)
                self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")

if __name__=="__main__":
    unittest.main()
