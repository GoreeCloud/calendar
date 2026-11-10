"""Dependency-free, SQLite-backed GoreeCloud Calendar HTTP service.

No user account or calendar data leaves this process except through authenticated
HTTP responses. This is a development preview, not a public-internet deployment.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

UTC = dt.timezone.utc
MAX_JSON = 64 * 1024
STATIC = Path(__file__).resolve().parent.parent / "web"
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, salt TEXT NOT NULL,
  password_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS calendars (
  id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL, color TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY, calendar_id TEXT NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
  title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '',
  start_at TEXT NOT NULL, end_at TEXT NOT NULL, all_day INTEGER NOT NULL DEFAULT 0,
  version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_window ON events(calendar_id, start_at, end_at);
CREATE TABLE IF NOT EXISTS calendar_members (
  calendar_id TEXT NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK(role IN ('read','edit')),
  created_at TEXT NOT NULL,
  PRIMARY KEY(calendar_id,user_id)
);
CREATE INDEX IF NOT EXISTS idx_calendar_members_user ON calendar_members(user_id);
CREATE TABLE IF NOT EXISTS event_recurrence (
  event_id TEXT PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
  rule_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS imported_uids (
  calendar_id TEXT NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
  external_uid TEXT NOT NULL,
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  PRIMARY KEY (calendar_id, external_uid)
);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY, calendar_id TEXT NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
  title TEXT NOT NULL, due_at TEXT, done INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_calendar ON tasks(calendar_id);
"""

class Failure(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message

def now() -> str:
    return dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

def database(path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=10000")
    return connection

def init_database(path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with database(path) as connection:
        connection.executescript(SCHEMA)
        connection.execute("PRAGMA journal_mode=WAL")

def digest_password(password: str, salt: str) -> str:
    return hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt),
                          n=16384, r=8, p=1, dklen=32).hex()

def validate_password(password: str) -> None:
    if not 12 <= len(password) <= 128:
        raise Failure(400, "Password must contain 12–128 characters")

def create_user(path: str, email: str, password: str) -> str:
    init_database(path)
    validate_password(password)
    email = email.strip().casefold()
    if not re.fullmatch(r"[^@\s]{1,128}@[^@\s]{1,190}", email):
        raise Failure(400, "Enter a valid email address")
    uid, cid, salt = uuid.uuid4().hex, uuid.uuid4().hex, secrets.token_hex(16)
    with database(path) as connection:
        try:
            connection.execute("INSERT INTO users VALUES(?,?,?,?,?)",
                               (uid, email, salt, digest_password(password, salt), now()))
            connection.execute("INSERT INTO calendars VALUES(?,?,?,?,?,?)",
                               (cid, uid, "Personal", "#6475de", "", now()))
        except sqlite3.IntegrityError:
            raise Failure(409, "Account already exists") from None
    return uid

def _text(value: object, name: str, limit: int, required: bool = False) -> str:
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise Failure(400, f"Invalid {name}")
    return value.strip()

def _stamp(value: object) -> str:
    if not isinstance(value, str) or len(value) > 48:
        raise Failure(400, "Invalid timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone required")
        return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (ValueError, OverflowError):
        raise Failure(400, "Dates must be timezone-aware ISO 8601 timestamps") from None

def _event_values(payload: dict) -> tuple:
    allowed = {"calendar_id", "title", "description", "location", "start_at", "end_at", "all_day"}
    if not set(payload) <= allowed:
        raise Failure(400, "Unknown event fields")
    title = _text(payload.get("title"), "title", 160, True)
    description = _text(payload.get("description", ""), "description", 4000)
    location = _text(payload.get("location", ""), "location", 500)
    start, end = _stamp(payload.get("start_at")), _stamp(payload.get("end_at"))
    if end <= start:
        raise Failure(400, "Event end must follow start")
    if not isinstance(payload.get("all_day", False), bool):
        raise Failure(400, "Invalid all_day")
    if payload.get("all_day", False):
        if not start.endswith("T00:00:00Z") or not end.endswith("T00:00:00Z"):
            raise Failure(400, "All-day events require UTC midnight boundaries")
    return title, description, location, start, end, int(payload.get("all_day", False))

def _ical_text(value: str) -> str:
    return (value.replace("\\", "\\\\").replace("\r", "")
                 .replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,"))

class CalendarHandler(BaseHTTPRequestHandler):
    server_version = "GoreeCloudCalendar/0.1"
    sys_version = ""
    def log_message(self, fmt, *args):
        # Exclude URLs, headers and user-controlled event descriptions from server logs.
        pass

    def _headers(self, status: int, ctype: str, length: int):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        self.end_headers()

    def _send(self, status: int, data: object):
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(raw))
        self.wfile.write(raw)

    def _error(self, exc: Failure):
        self._send(exc.status, {"error": exc.message})

    def _body(self) -> dict:
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            raise Failure(415, "Expected application/json")
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            raise Failure(400, "Invalid Content-Length") from None
        if length < 0 or length > MAX_JSON:
            raise Failure(413, "Invalid request size")
        try:
            obj = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise Failure(400, "Invalid JSON") from None
        if not isinstance(obj, dict):
            raise Failure(400, "Expected a JSON object")
        return obj

    def _user(self, db) -> str:
        raw = self.headers.get("Authorization", "")
        if not raw.startswith("Bearer ") or len(raw) > 160:
            raise Failure(401, "Authentication required")
        token = raw[7:]
        if not re.fullmatch("[a-zA-Z0-9_-]{40,90}", token):
            raise Failure(401, "Authentication required")
        hashed = hashlib.sha256(token.encode("ascii")).hexdigest()
        row = db.execute("SELECT user_id FROM sessions WHERE token_hash=? AND expires>?",
                         (hashed, int(time.time()))).fetchone()
        if row is None:
            raise Failure(401, "Session expired or invalid")
        return row["user_id"]

    def _owned_calendar(self, db, user: str, cid: str):
        row = db.execute("SELECT * FROM calendars WHERE id=? AND owner_id=?", (cid, user)).fetchone()
        if row is None:
            raise Failure(404, "Calendar not found")
        return row

    def _accessible_calendar(self, db, user: str, cid: str, write: bool = False):
        row = db.execute(
            "SELECT c.*, CASE WHEN c.owner_id=? THEN 'owner' ELSE m.role END AS role "
            "FROM calendars c LEFT JOIN calendar_members m ON m.calendar_id=c.id AND m.user_id=? "
            "WHERE c.id=? AND (c.owner_id=? OR m.user_id=?)",
            (user,user,cid,user,user)).fetchone()
        if row is None:
            raise Failure(404, "Calendar not found")
        if write and row["role"] not in ("owner","edit"):
            raise Failure(403, "This calendar is read-only")
        return row

    def _owned_item(self, db, table: str, user: str, item_id: str):
        row = db.execute(
            f"SELECT item.* FROM {table} item JOIN calendars c ON item.calendar_id=c.id "
            "WHERE item.id=? AND (c.owner_id=? OR EXISTS "
            "(SELECT 1 FROM calendar_members m WHERE m.calendar_id=c.id "
            "AND m.user_id=? AND m.role='edit'))", (item_id, user,user)).fetchone()
        if row is None:
            raise Failure(404, "Item not found")
        return row

    def do_GET(self):
        self._dispatch("GET")
    def do_POST(self):
        self._dispatch("POST")
    def do_PATCH(self):
        self._dispatch("PATCH")
    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method: str):
        try:
            self._handle(method)
        except Failure as exc:
            self._error(exc)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self._send(500, {"error": "Internal server error"})

    def _handle(self, method: str):
        route = urlsplit(self.path)
        path = route.path
        if method == "GET" and path == "/healthz":
            return self._send(200, {"status": "ok"})
        static = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
                  "/styles.css": ("styles.css", "text/css")}
        if method == "GET" and path in static:
            name, mime = static[path]
            raw = (STATIC / name).read_bytes()
            self._headers(200, mime+"; charset=utf-8", len(raw))
            self.wfile.write(raw)
            return
        if not path.startswith("/api/v1/"):
            raise Failure(404, "Not found")
        if path == "/api/v1/login" and method == "POST":
            return self._login(self._body())
        with database(self.server.db_path) as db:
            user = self._user(db)
            if path == "/api/v1/me" and method == "GET":
                row = db.execute("SELECT id,email FROM users WHERE id=?", (user,)).fetchone()
                return self._send(200, dict(row))
            if path == "/api/v1/logout" and method == "POST":
                token = self.headers.get("Authorization", "")[7:]
                db.execute("DELETE FROM sessions WHERE token_hash=?",
                           (hashlib.sha256(token.encode("ascii")).hexdigest(),))
                db.commit()
                return self._send(200, {"ok": True})
            if path == "/api/v1/calendars":
                if method == "GET":
                    rows = db.execute("SELECT c.*, CASE WHEN c.owner_id=? THEN 'owner' "
                        "ELSE m.role END AS role FROM calendars c "
                        "LEFT JOIN calendar_members m ON m.calendar_id=c.id AND m.user_id=? "
                        "WHERE c.owner_id=? OR m.user_id=? ORDER BY c.name,c.id",
                        (user,user,user,user))
                    return self._send(200, {"calendars": [dict(r) for r in rows]})
                if method == "POST":
                    body = self._body()
                    if not set(body) <= {"name", "color", "description"}:
                        raise Failure(400, "Unknown calendar fields")
                    name = _text(body.get("name"), "name", 100, True)
                    color = body.get("color", "#6475de")
                    if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                        raise Failure(400, "Invalid color")
                    desc = _text(body.get("description", ""), "description", 500)
                    cid = uuid.uuid4().hex
                    db.execute("INSERT INTO calendars VALUES(?,?,?,?,?,?)",
                               (cid, user, name, color, desc, now()))
                    db.commit()
                    return self._send(201, {"id": cid})
            if path.startswith("/api/v1/calendars/") and "/members" in path:
                tail=path[len("/api/v1/calendars/"):].split("/")
                if len(tail) not in (2,3) or tail[1] != "members":
                    raise Failure(404, "Not found")
                cid=tail[0]
                self._owned_calendar(db, user, cid)
                if len(tail)==2 and method=="GET":
                    rows=db.execute("SELECT m.user_id,u.email,m.role FROM calendar_members m "
                        "JOIN users u ON u.id=m.user_id WHERE m.calendar_id=? ORDER BY u.email", (cid,))
                    return self._send(200, {"members":[dict(m) for m in rows]})
                if len(tail)==2 and method=="POST":
                    body=self._body()
                    if set(body)!={"email","role"}:
                        raise Failure(400,"Email and role required")
                    email=_text(body["email"],"email",320,True).casefold()
                    role=body["role"]
                    if role not in ("read","edit"):
                        raise Failure(400,"Role must be read or edit")
                    target=db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
                    if target is None:
                        raise Failure(404,"Calendar member account not found")
                    if target["id"]==user:
                        raise Failure(400,"The owner already controls the calendar")
                    db.execute("INSERT INTO calendar_members VALUES(?,?,?,?) "
                        "ON CONFLICT(calendar_id,user_id) DO UPDATE SET role=excluded.role",
                        (cid,target["id"],role,now()))
                    db.commit()
                    return self._send(200,{"ok":True})
                if len(tail)==3 and method=="DELETE":
                    target_id=tail[2]
                    db.execute("DELETE FROM calendar_members WHERE calendar_id=? AND user_id=?",
                               (cid,target_id))
                    db.commit()
                    return self._send(200,{"ok":True})
                raise Failure(404,"Not found")
            if path.startswith("/api/v1/calendars/") and method in ("PATCH", "DELETE"):
                cid = path.rsplit("/", 1)[-1]
                old = self._owned_calendar(db, user, cid)
                if method == "DELETE":
                    db.execute("DELETE FROM calendars WHERE id=?", (cid,))
                    db.commit()
                    return self._send(200, {"ok": True})
                body = self._body()
                if not body or not set(body) <= {"name", "color", "description"}:
                    raise Failure(400, "Unknown calendar fields")
                name = _text(body.get("name", old["name"]), "name", 100, True)
                color = body.get("color", old["color"])
                if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                    raise Failure(400, "Invalid color")
                desc = _text(body.get("description", old["description"]), "description", 500)
                db.execute("UPDATE calendars SET name=?,color=?,description=? WHERE id=?",
                           (name, color, desc, cid))
                db.commit()
                return self._send(200, {"ok": True})
            if path == "/api/v1/events":
                if method == "GET":
                    args = parse_qs(route.query)
                    start = _stamp(args.get("start", [now()])[0])
                    end = _stamp(args.get("end", [(dt.datetime.now(UTC)+dt.timedelta(days=90)).isoformat()])[0])
                    if end <= start or (dt.datetime.fromisoformat(end.replace("Z","+00:00")) -
                        dt.datetime.fromisoformat(start.replace("Z","+00:00"))).days > 370:
                        raise Failure(400, "Invalid query window")
                    rows = db.execute("SELECT e.* FROM events e JOIN calendars c ON e.calendar_id=c.id "
                        "LEFT JOIN event_recurrence r ON r.event_id=e.id "
                        "WHERE (c.owner_id=? OR EXISTS (SELECT 1 FROM calendar_members m "
                        "WHERE m.calendar_id=c.id AND m.user_id=?)) "
                        "AND e.start_at<? AND e.end_at>? AND r.event_id IS NULL "
                        "ORDER BY e.start_at LIMIT 501", (user, user, end, start)).fetchall()
                    events = [dict(r) for r in rows]
                    recurring = db.execute("SELECT e.*, r.rule_json FROM events e "
                        "JOIN calendars c ON e.calendar_id=c.id "
                        "JOIN event_recurrence r ON r.event_id=e.id "
                        "WHERE (c.owner_id=? OR EXISTS (SELECT 1 FROM calendar_members m "
                        "WHERE m.calendar_id=c.id AND m.user_id=?)) "
                        "AND e.start_at<? LIMIT 501", (user,user,end)).fetchall()
                    if len(recurring)>500:
                        raise Failure(413, "Too many recurring series")
                    from .recurrence import expand, RecurrenceError
                    window_start = dt.datetime.fromisoformat(start.replace("Z","+00:00"))
                    window_end = dt.datetime.fromisoformat(end.replace("Z","+00:00"))
                    for record in recurring:
                        item = dict(record)
                        rule = json.loads(item.pop("rule_json"))
                        try:
                            events.extend(expand(item,rule,window_start,window_end))
                        except RecurrenceError:
                            raise Failure(422,"Cannot expand corrupted recurrence") from None
                        if len(events)>500:
                            raise Failure(413, "Window contains too many events; narrow the date range")
                    events.sort(key=lambda e: (e["start_at"], e["id"]))
                    return self._send(200, {"events": events})
                if method == "POST":
                    payload = self._body()
                    from .recurrence import validate_rule, RecurrenceError
                    try:
                        rule=validate_rule(payload.pop("recurrence",None))
                    except RecurrenceError as error:
                        raise Failure(400,str(error)) from None
                    cid = _text(payload.get("calendar_id"), "calendar_id", 64, True)
                    self._accessible_calendar(db, user, cid, write=True)
                    title, desc, location, start, end, all_day = _event_values(payload)
                    eid = uuid.uuid4().hex
                    db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                               (eid, cid, title, desc, location, start, end, all_day, 1, now(), now()))
                    if rule is not None:
                        db.execute("INSERT INTO event_recurrence VALUES(?,?)", (eid, json.dumps(rule)))
                    db.commit()
                    return self._send(201, {"id": eid, "version": 1})
            if path.startswith("/api/v1/events/") and method in ("PATCH", "DELETE"):
                eid = path.rsplit("/", 1)[-1]
                old = self._owned_item(db, "events", user, eid)
                if method == "DELETE":
                    db.execute("DELETE FROM events WHERE id=?", (eid,))
                    db.commit()
                    return self._send(200, {"ok": True})
                payload = self._body()
                has_rule = "recurrence" in payload
                from .recurrence import validate_rule, RecurrenceError
                try:
                    rule = validate_rule(payload.pop("recurrence", None))
                except RecurrenceError as error:
                    raise Failure(400,str(error)) from None
                version = payload.pop("version", None)
                if type(version) is not int:
                    raise Failure(428, "Current event version required")
                if version != old["version"]:
                    raise Failure(409, "Event was changed on another device; refresh")
                merged = {name: old[name] for name in
                          ("calendar_id", "title", "description", "location", "start_at", "end_at", "all_day")}
                merged.update(payload)
                merged["all_day"] = bool(merged["all_day"]) if type(merged["all_day"]) is int else merged["all_day"]
                cid = _text(merged.get("calendar_id"), "calendar_id", 64, True)
                self._accessible_calendar(db, user, cid, write=True)
                title, desc, location, start, end, all_day = _event_values(merged)
                changed = db.execute("UPDATE events SET calendar_id=?,title=?,description=?,"
                    "location=?,start_at=?,end_at=?,all_day=?,version=version+1,updated_at=? "
                    "WHERE id=? AND version=?", (cid,title,desc,location,start,end,all_day,now(),eid,version))
                if changed.rowcount != 1:
                    raise Failure(409, "Event changed; refresh")
                if has_rule:
                    db.execute("DELETE FROM event_recurrence WHERE event_id=?", (eid,))
                    if rule is not None:
                        db.execute("INSERT INTO event_recurrence VALUES(?,?)", (eid,json.dumps(rule)))
                db.commit()
                return self._send(200, {"id":eid,"version":version+1})
            if path == "/api/v1/tasks":
                if method == "GET":
                    rows = db.execute("SELECT t.* FROM tasks t JOIN calendars c ON t.calendar_id=c.id "
                                      "WHERE c.owner_id=? OR EXISTS (SELECT 1 FROM calendar_members m "
                                      "WHERE m.calendar_id=c.id AND m.user_id=?) "
                                      "ORDER BY t.done,t.due_at,t.created_at LIMIT 501",
                                      (user,user)).fetchall()
                    if len(rows) > 500:
                        raise Failure(413, "Too many tasks")
                    return self._send(200, {"tasks": [dict(r) for r in rows]})
                if method == "POST":
                    body = self._body()
                    if not set(body) <= {"calendar_id", "title", "due_at"}:
                        raise Failure(400, "Unknown task fields")
                    cid = _text(body.get("calendar_id"), "calendar_id", 64, True)
                    self._accessible_calendar(db, user, cid, write=True)
                    title = _text(body.get("title"), "title", 160, True)
                    due = _stamp(body["due_at"]) if body.get("due_at") else None
                    tid = uuid.uuid4().hex
                    db.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?)",
                               (tid,cid,title,due,0,now(),now()))
                    db.commit()
                    return self._send(201, {"id":tid})
            if path.startswith("/api/v1/tasks/") and method in ("PATCH", "DELETE"):
                tid = path.rsplit("/", 1)[-1]
                old = self._owned_item(db, "tasks", user, tid)
                if method == "DELETE":
                    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
                    db.commit()
                    return self._send(200, {"ok": True})
                body = self._body()
                if not body or not set(body) <= {"title", "done", "due_at"}:
                    raise Failure(400, "Unknown task fields")
                title = _text(body.get("title",old["title"]), "title", 160, True)
                done = body.get("done", bool(old["done"]))
                if not isinstance(done,bool):
                    raise Failure(400,"Invalid done state")
                due = _stamp(body["due_at"]) if body.get("due_at") else (
                    None if "due_at" in body else old["due_at"])
                db.execute("UPDATE tasks SET title=?,done=?,due_at=?,updated_at=? WHERE id=?",
                           (title,int(done),due,now(),tid))
                db.commit()
                return self._send(200,{"ok":True})
            if path == "/api/v1/import.ics" and method == "POST":
                body = self._body()
                if set(body) != {"calendar_id", "ics"}:
                    raise Failure(400, "Calendar and ICS file content required")
                cid = _text(body["calendar_id"], "calendar_id", 64, True)
                self._accessible_calendar(db, user, cid, write=True)
                from .ical import parse_calendar, ImportErrorCalendar
                try:
                    events = parse_calendar(body["ics"])
                except ImportErrorCalendar as error:
                    raise Failure(400, str(error)) from None
                db.execute("BEGIN IMMEDIATE")
                imported, skipped = 0, 0
                for entry in events:
                    existing = db.execute("SELECT event_id FROM imported_uids "
                        "WHERE calendar_id=? AND external_uid=?", (cid, entry["uid"])).fetchone()
                    if existing is not None:
                        skipped += 1
                        continue
                    eid = uuid.uuid4().hex
                    db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        (eid, cid, entry["title"], entry["description"], entry["location"],
                         entry["start_at"], entry["end_at"], int(entry["all_day"]), 1, now(), now()))
                    db.execute("INSERT INTO imported_uids VALUES(?,?,?)", (cid, entry["uid"], eid))
                    imported += 1
                db.commit()
                return self._send(201, {"imported": imported, "skipped": skipped})
            if path == "/api/v1/export.ics" and method == "GET":
                cid = parse_qs(route.query).get("calendar_id", [None])[0]
                self._accessible_calendar(db, user, cid or "")
                entries = db.execute("SELECT * FROM events WHERE calendar_id=? ORDER BY start_at", (cid,))
                lines = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//GoreeCloud//Calendar//EN"]
                for event in entries:
                    def timefield(key):
                        return event[key].replace("-","").replace(":","").replace("Z","Z")
                    lines.extend(["BEGIN:VEVENT","UID:"+event["id"]+"@goreecloud.local",
                        "DTSTAMP:"+now().replace("-","").replace(":",""),
                        "DTSTART:"+timefield("start_at"),"DTEND:"+timefield("end_at"),
                        "SUMMARY:"+_ical_text(event["title"]),
                        "DESCRIPTION:"+_ical_text(event["description"]),
                        "LOCATION:"+_ical_text(event["location"]),"END:VEVENT"])
                lines.append("END:VCALENDAR")
                raw = ("\r\n".join(lines)+"\r\n").encode("utf-8")
                self._headers(200,"text/calendar; charset=utf-8",len(raw))
                self.wfile.write(raw)
                return
        raise Failure(404, "Not found")

    def _login(self, body):
        if set(body) != {"email","password"} or not isinstance(body["email"], str) or not isinstance(body["password"], str):
            raise Failure(400, "Email and password required")
        email = body["email"].strip().casefold()
        if len(email)>320 or len(body["password"])>128:
            raise Failure(400, "Invalid credentials")
        with database(self.server.db_path) as db:
            row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            # Run the KDF even when the account is absent to reduce user enumeration.
            salt = row["salt"] if row else "00"*16
            expected = row["password_hash"] if row else "00"*32
            computed = digest_password(body["password"], salt)
            if row is None or not hmac.compare_digest(computed, expected):
                raise Failure(401, "Invalid credentials")
            token = secrets.token_urlsafe(32)
            expiry = int(time.time()) + 7*86400
            db.execute("DELETE FROM sessions WHERE expires<=?",(int(time.time()),))
            db.execute("INSERT INTO sessions VALUES(?,?,?)",
                       (hashlib.sha256(token.encode("ascii")).hexdigest(),row["id"],expiry))
        return self._send(200,{"token":token,"expires_at":expiry,"email":email})

def make_server(db_path: str, host: str = "127.0.0.1", port: int = 8787) -> ThreadingHTTPServer:
    init_database(db_path)
    server = ThreadingHTTPServer((host,port),CalendarHandler)
    server.daemon_threads = True
    server.db_path = str(db_path)
    return server
