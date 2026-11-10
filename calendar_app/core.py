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

    def _owned_item(self, db, table: str, user: str, item_id: str):
        row = db.execute(
            f"SELECT item.* FROM {table} item JOIN calendars c ON item.calendar_id=c.id "
            "WHERE item.id=? AND c.owner_id=?", (item_id, user)).fetchone()
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
                return self._send(200, {"ok": True})
            if path == "/api/v1/calendars":
                if method == "GET":
                    rows = db.execute("SELECT * FROM calendars WHERE owner_id=? ORDER BY name,id", (user,))
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
                    return self._send(201, {"id": cid})
            if path.startswith("/api/v1/calendars/") and method in ("PATCH", "DELETE"):
                cid = path.rsplit("/", 1)[-1]
                old = self._owned_calendar(db, user, cid)
                if method == "DELETE":
                    db.execute("DELETE FROM calendars WHERE id=?", (cid,))
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
                        "WHERE c.owner_id=? AND e.start_at<? AND e.end_at>? ORDER BY e.start_at LIMIT 501",
                        (user, end, start)).fetchall()
                    if len(rows) > 500:
                        raise Failure(413, "Window contains too many events; narrow the date range")
                    return self._send(200, {"events": [dict(r) for r in rows]})
                if method == "POST":
                    payload = self._body()
                    cid = _text(payload.get("calendar_id"), "calendar_id", 64, True)
                    self._owned_calendar(db, user, cid)
                    title, desc, location, start, end, all_day = _event_values(payload)
                    eid = uuid.uuid4().hex
                    db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                               (eid, cid, title, desc, location, start, end, all_day, 1, now(), now()))
                    return self._send(201, {"id": eid, "version": 1})
            if path.startswith("/api/v1/events/") and method in ("PATCH", "DELETE"):
                eid = path.rsplit("/", 1)[-1]
                old = self._owned_item(db, "events", user, eid)
                if method == "DELETE":
                    db.execute("DELETE FROM events WHERE id=?", (eid,))
                    return self._send(200, {"ok": True})
                payload = self._body()
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
                self._owned_calendar(db, user, cid)
                title, desc, location, start, end, all_day = _event_values(merged)
                changed = db.execute("UPDATE events SET calendar_id=?,title=?,description=?,"
                    "location=?,start_at=?,end_at=?,all_day=?,version=version+1,updated_at=? "
                    "WHERE id=? AND version=?", (cid,title,desc,location,start,end,all_day,now(),eid,version))
                if changed.rowcount != 1:
                    raise Failure(409, "Event changed; refresh")
                return self._send(200, {"id":eid,"version":version+1})
            if path == "/api/v1/tasks":
                if method == "GET":
                    rows = db.execute("SELECT t.* FROM tasks t JOIN calendars c ON t.calendar_id=c.id "
                                      "WHERE c.owner_id=? ORDER BY t.done,t.due_at,t.created_at LIMIT 501",
                                      (user,)).fetchall()
                    if len(rows) > 500:
                        raise Failure(413, "Too many tasks")
                    return self._send(200, {"tasks": [dict(r) for r in rows]})
                if method == "POST":
                    body = self._body()
                    if not set(body) <= {"calendar_id", "title", "due_at"}:
                        raise Failure(400, "Unknown task fields")
                    cid = _text(body.get("calendar_id"), "calendar_id", 64, True)
                    self._owned_calendar(db, user, cid)
                    title = _text(body.get("title"), "title", 160, True)
                    due = _stamp(body["due_at"]) if body.get("due_at") else None
                    tid = uuid.uuid4().hex
                    db.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?)",
                               (tid,cid,title,due,0,now(),now()))
                    return self._send(201, {"id":tid})
            if path.startswith("/api/v1/tasks/") and method in ("PATCH", "DELETE"):
                tid = path.rsplit("/", 1)[-1]
                old = self._owned_item(db, "tasks", user, tid)
                if method == "DELETE":
                    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
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
                return self._send(200,{"ok":True})
            if path == "/api/v1/export.ics" and method == "GET":
                cid = parse_qs(route.query).get("calendar_id", [None])[0]
                self._owned_calendar(db, user, cid or "")
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
