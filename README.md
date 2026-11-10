# GoreeCloud Calendar

A **self-hostable, open-source calendar development preview** with a Python/SQLite service and responsive web interface. The calendar backend is independent of Google, Outlook, TimeTree, Proton and Tuta. **Not production-ready.**

## Current functionality (source implemented; verify the current CI status)

- Local interactive account creation and scrypt password hashing.
- Authenticated, revocable seven-day bearer sessions stored as hashed tokens.
- Private per-user calendars with create, view, edit and delete operations.
- Create, view, edit and delete timed events using ISO-8601 UTC timestamps; optimistic event version checks.
- Create, complete and delete tasks.
- Responsive web month, week, agenda and task views with event editing.
- Calendar display toggles, native-browser ICS calendar export, sign-in and sign-out.
- Local SQLite storage, parameterized SQL, bounded JSON input and no third-party browser scripts.
- Container configuration bound to localhost and an HTTP integration test suite.

**Not yet implemented or verified:** sharing, recurrence, all-day event UI, importing ICS, CalDAV, external synchronization, encrypted sharing, offline editing, reminders, notifications, appointment booking, public calendars, analytics and AI. Linux and Android apps still require verified installable deliverables. Photo albums are excluded.

## Local run — Python 3.11+

There are no additional Python runtime dependencies.

    python -m calendar_app create-admin --email you@example.com
    python -m calendar_app serve

The account-creation command requests your password interactively (minimum twelve characters). Open http://127.0.0.1:8787/ and sign in. By default, data is stored under ./data/calendar.sqlite3. Override the path with GC_CALENDAR_DB.

## Docker Compose (local-only example)

    docker compose build
    docker compose run --rm calendar python -m calendar_app create-admin --email you@example.com
    docker compose up -d

The Compose file binds **host loopback** 127.0.0.1:8787. Do not expose the Python HTTP server to the internet. Only configure remote access after a threat review and HTTPS reverse proxy, network protections and security testing. Container deployment has not been runtime tested in this conversation.

## Test locally

    python -m unittest discover -s tests -v
    python -m compileall -q calendar_app tests
    node --check web/app.js

## Project structure

- calendar_app — Python HTTP API, SQLite schema, local administrator CLI.
- web — no-framework responsive web client and GC UI–guided semantic styling.
- tests — SQLite-backed HTTP integration tests.
- compose.yaml and Dockerfile — example local container deployment.
- docs — planned feature boundaries, architecture and status.
- .github/workflows — source checks.

## Security

This project is an early preview, **not an audited calendar vault**. There is no TLS listener, login abuse-rate protection, encryption at rest, backup verification, identity federation, or multi-user calendar sharing. The web client uses sessionStorage for its bearer token. See SECURITY.md. No production deployment is claimed.

## License

MIT — see LICENSE. Third-party components, when later imported, require separate licensing and attribution review. No external calendar APIs are required by the present backend.
