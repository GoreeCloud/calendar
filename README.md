# GoreeCloud Calendar

Privacy-conscious, self-hosted calendar development preview. The repository includes a Python/SQLite backend, responsive web app, native GTK4 Linux client source and native Java Android client source. No third-party calendar account is required.

**Status: development preview — not production-ready.** Do not expose the HTTP listener to untrusted networks or store your only copy of important schedules.

## Source-implemented capabilities

- Locally provisioned accounts, salted scrypt password hashing, expiring bearer sessions, password rotation that revokes all sessions, and self-service sign-out of other sessions.
- Multiple private calendars, local user sharing and owner, edit, read and **free/busy-only** roles. Free/busy shares reveal occupied intervals without names, notes, locations, tasks or event identifiers.
- Timed, multi-day and all-day events, timezone-aware event editing, version conflict handling.
- Bounded recurrence: daily, weekly, monthly, yearly; interval 1–24, count 2–366; optional IANA timezone for local-hour preservation. Individually skip and restore occurrences with optimistic version checks.
- Tasks with due dates, completion, editable P1–P4 priorities and browser filters for open, due today, overdue, completed and all tasks.
- Permission-scoped event/task search.
- ICS import/export: all-day dates, folded text, IANA TZID, bounded RRULEs, EXDATE exclusions, display VALARM reminders and duplicate-UID protection. Unsupported complex rules are rejected.
- Responsive month, week, agenda, task views; calendar visibility and owner-only rename/recolor/description/delete controls; mobile switcher, recurring-series editing, skip/restore dialogs, optional browser reminders while the tab is open, search and sharing.
- Authenticated availability explorer and private 9 AM–5 PM local meeting-time suggestions across up to five authorized calendars, using recurrence-aware busy data without exposing event details. Unscheduled time is **not** a guaranteed bookable slot.
- Owner-only bounded JSON portability export (owned calendars, events, recurrence exceptions, reminders and tasks) without account secrets or sharing lists. The downloaded file is sensitive plaintext, not an import/restore mechanism.
- Online SQLite snapshots, read-only integrity and foreign-key checks, and a verified no-overwrite restore workflow to a NEW database path.
- Native GTK4 Linux client and Java Android client source, with adjustable event start times and opt-in 15-minute reminders on creation. Linux task creation/completion and Android task priorities/read-only controls are included in the previews. Android debug APK compilation and GTK virtual-display checks run in CI.

**Not implemented:** CalDAV, external two-way sync, single-occurrence event overrides or complete RFC recurrence, public calendar discovery, meeting invitations/RSVP, booking pages, offline edits, reliable background/push notifications, end-to-end encryption, AI scheduling, advanced analytics, signed releases or production deployment. Photo albums are explicitly excluded.

See [current feature status](docs/IMPLEMENTED-FEATURES.md), [planned features](docs/PLANNED-FEATURES.md), [HTTP API](docs/API.md), [DAV integration plan](docs/DAV-INTEROPERABILITY.md) and [security boundaries](SECURITY.md).

## Run locally

Requires Python 3.11+; no extra Python runtime packages.

    python -m calendar_app create-admin --email you@example.com
    python -m calendar_app serve

The account-creation command prompts for a password of 12 or more characters. Open http://127.0.0.1:8787/ in a browser and sign in. Default database path: ./data/calendar.sqlite3; set GC_CALENDAR_DB to override. Create other users using the same create-admin command before sharing calendars.

## Docker Compose (local-only)

    docker compose build
    docker compose run --rm calendar python -m calendar_app create-admin --email you@example.com
    docker compose up -d

The example publishes only to host loopback, 127.0.0.1:8787. It has no production HTTPS configuration. Do not bind to the public internet without independent security review and hardened ingress.

## Backup and verification

    python -m calendar_app backup --output /secure/location/calendar-snapshot.sqlite3
    python -m calendar_app verify-backup --input /secure/location/calendar-snapshot.sqlite3
    python -m calendar_app restore-backup --input /secure/location/calendar-snapshot.sqlite3 --output /secure/location/restored-calendar.sqlite3

All commands are local. Backups and restores refuse to overwrite existing files. The restore command validates a snapshot and writes a separate verified SQLite database, preserving its user accounts, calendars, events and tasks. It does **not** reconfigure or replace a running server database. Stop the server and plan a verified operator-controlled cutover separately. **Backups are not encrypted.** Protect data, manage retention and rehearse restoration on each target deployment before relying on recovery procedures.

## Development checks

    python -m unittest discover -s tests -v
    python -m compileall -q calendar_app tests linux
    node --check web/app.js

CI runs Python HTTP, SQLite upgrade and backup/restore tests; browser DOM selector checks and JavaScript syntax checks; GTK virtual-display smoke tests; Android debug compilation/lint; and Docker startup readiness checks. A passing build does not demonstrate production, visual, or real-device acceptance.

Native development instructions: [Linux GTK4](linux/README.md) and [Android](android/README.md).

## Architecture and license

- calendar_app: HTTP API, SQLite, auth, sharing, ICS, recurrence, backup.
- web: dependency-free responsive interface guided by GoreeCloud UI.
- linux: native GTK4 development client and per-user launcher.
- android: native Java/Android project.
- tests: isolated HTTP/SQLite tests.
- docs: API and feature scope documentation.

The five GoreeCloud MIPS (UI, Mesh, Identity, GoreeShield privacy and Wardveil cybersecurity) are governing integration targets, not yet verified runtime services in this implementation.

Original repository source is [MIT licensed](LICENSE). Future third-party dependencies require independent security, license and attribution review.

### Recovery caution

The `restore-backup` command is an offline, no-clobber extraction and verification tool. It cannot automatically migrate DNS, containers, application identities, attached volumes, encryption keys or reverse-proxy routes. A running deployment requires a separately reviewed cutover and rollback plan. A green CI restore test is not production disaster-recovery acceptance.
