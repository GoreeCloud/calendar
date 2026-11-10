# GoreeCloud Calendar — Implemented source features

**Document status:** Repository development-branch inventory. Code present and CI checks are separate from production, on-device and visual acceptance.

## Backend

- Python 3.11+ HTTP API and SQLite storage.
- Locally created accounts, salted scrypt hashes, revocable bearer sessions.
- Multiple personal calendars, owner/read/edit memberships, permissions and revocation.
- Event CRUD, timezone validation, all-day events, optimistic version conflicts.
- Bounded daily/weekly/monthly/yearly recurrence and timezone-aware expansion.
- Task creation, reading, completion, updates and deletion.
- Permission-scoped search across event text and tasks.
- ICS import/export with IANA timezone, all-day dates, bounded recurrence, UID deduplication.
- Online no-clobber SQLite snapshots and independent read-only integrity verification.
- Local-loopback server default and example Docker Compose.

## Web client

- Login/logout, month/week/agenda/tasks, calendar visibility.
- Event creation/editing, all-day and recurring series editor.
- Task management, ICS import/export, text search.
- Owner-managed calendar sharing with local users, member removal.
- Mobile calendar switcher, read-only shared-calendar presentation and responsive floating navigation dock.
- Light/dark system appearance, accessible labels and text-first dynamic rendering.

## Native client source

- Linux GTK4: login, native date picker and agenda, basic event creation, per-user launcher installer.
- Android Java: HTTPS login, date picker and agenda, basic event creation, task operations and logout.
- GitHub Actions: Python HTTP and backup tests, JavaScript syntax, GTK import, Android debug APK compilation.

## Explicit limitations

No production deployment or reviewed release. No advanced sharing (invitation email, free/busy-only, federation, E2EE), offline edits, notifications, CalDAV, complex recurrence exceptions, public publishing, meeting coordination or AI. Linux and Android require device testing and formal package/release acceptance. Photo albums excluded.
