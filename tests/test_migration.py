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

if __name__=="__main__":
    unittest.main()
