# GoreeCloud Calendar — Implemented source features

**Document status:** Repository development-branch inventory. Code present and CI checks are separate from production, on-device and visual acceptance.

## Backend

- Python 3.11+ HTTP API and SQLite storage.
- Locally created accounts, salted scrypt hashes, revocable bearer sessions.
- Multiple personal calendars and owner/edit/read/freebusy memberships, revocation and privacy-preserving busy interval projections.
- Event CRUD, timezone validation, all-day events, optimistic version conflicts.
- Bounded daily/weekly/monthly/yearly recurrence and timezone-aware expansion; skip/restore of exact occurrences with series version conflicts.
- Task creation, reading, completion, updates, deletion and P1–P4 priorities, with lossless schema upgrade for existing tasks.
- Permission-scoped search across event text and tasks; bounded authenticated availability API returning merged UTC intervals from events and recurrences.
- ICS import/export with IANA timezone, all-day dates, bounded recurrence, UID deduplication, EXDATE exclusions and one supported display VALARM.
- Online no-clobber SQLite snapshots, independent structural and foreign-key verification, and no-overwrite restore to a NEW database file, tested with calendar event and task recovery.
- Local-loopback server default and example Docker Compose.

## Web client

- Login/logout, month/week/agenda/tasks, calendar visibility.
- Event creation/editing, all-day and recurring series editor, reminder offsets, skipped-date manager and browser alerts while the app tab is open.
- Task management, P1–P4 priority selection and filters (open/today/overdue/completed/all), ICS import/export, text search, and a date-based private availability explorer.
- Owner-managed calendar sharing with local users, member removal and free/busy-only visibility; owner-only rename, recolor, description and deletion controls.
- Mobile calendar switcher, read-only shared-calendar presentation and responsive floating navigation dock.
- Light/dark system appearance, accessible labels and text-first dynamic rendering.

## Native client source

- Linux GTK4: login, native date picker and agenda, adjustable event start/duration, optional reminder on event creation, per-user launcher installer.
- Android Java: HTTPS login, date picker and agenda, event time picker and opt-in reminder on creation, task operations and logout.
- GitHub Actions: Python HTTP, migration, backup and browser markup contract tests, JavaScript syntax, GTK virtual display smoke, Android debug APK build/lint and Docker server readiness.

## Explicit limitations

No production deployment or reviewed release. No invitation email, sharing federation or E2EE; no offline edits, reliable background/push notifications, CalDAV, per-instance recurrence overrides, public publishing, meeting coordination or AI. Linux and Android require device testing and formal package/release acceptance. Photo albums excluded.
