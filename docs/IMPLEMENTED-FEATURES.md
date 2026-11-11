# GoreeCloud Calendar — Implemented source features

**Document status:** Repository development-branch inventory. Code present and CI checks are separate from production, on-device and visual acceptance.

## Backend

- Python 3.11+ HTTP API and SQLite storage.
- Locally created accounts, salted scrypt hashes, revocable bearer sessions, self-service password rotation, active session counts and revoke-other-sessions action. A concurrent-login regression checks rotation invalidation.
- Multiple personal calendars and owner/edit/read/freebusy memberships, revocation and privacy-preserving busy interval projections.
- Event CRUD, timezone validation, all-day events, optimistic version checks for edits/deletion and atomic write-permission rechecks.
- Bounded daily/weekly/monthly/yearly recurrence and timezone-aware expansion; skip/restore of exact occurrences with series version conflicts.
- Task creation, reading, completion, updates, deletion and P1–P4 priorities, with lossless schema upgrade for existing tasks and task version columns. Optimistic write checks detect conflicting updates/deletions from concurrent clients.
- Permission-scoped search across event text and tasks; bounded authenticated availability API returning merged UTC intervals from events and recurrences; private meeting-time suggestions across up to five accessible calendars.
- Event ICS import/export with IANA timezone, all-day dates, bounded recurrence, UID deduplication, EXDATE exclusions and one supported display VALARM. **Separate conservative VTODO task ICS import/export** supports due times, completion, priority and UID-based duplicate prevention; rejects unsupported fields. Bounded owner-only JSON portability exports include tasks and exclude account/session secrets.
- Online no-clobber SQLite snapshots, independent structural and foreign-key verification, and no-overwrite restore to a NEW database file, tested with calendar event and task recovery.
- Local-loopback server default and example Docker Compose.
- Seven-day deduplication for optionally keyed task/event POST requests; private SQLite request receipt table and same-transaction concurrency guard. No durable offline queue.
- Context-managed SQLite connections explicitly close after commit or rollback.

## Web client

- Login/logout, month/week/agenda/tasks, calendar visibility.
- Event creation/editing, all-day and recurring series editor, reminder offsets, skipped-date manager and browser alerts while the app tab is open.
- Task management, P1–P4 priority selection and filters (open/today/overdue/completed/all), version-aware edits/deletions, stable per-form create request IDs for retries, separate event and task ICS import/export actions, private JSON downloads, text search, date-based availability exploration, and private meeting-time suggestions.
- Owner-managed calendar sharing with local users, member removal and free/busy-only visibility; owner-only rename, recolor, description and deletion controls.
- Mobile calendar switcher, read-only shared-calendar presentation and responsive floating navigation dock.
- Light/dark system appearance, accessible labels and text-first dynamic rendering.

## Native client source

- Linux GTK4: login, native date picker and agenda, adjustable event start/duration, optional reminder on event creation, task list/completion and priority-based task creation, per-user launcher installer.
- Android Java: HTTPS login, date picker and agenda, event time picker and opt-in reminder on creation, task list/completion with read-only restrictions, priority on creation and logout.
- GitHub Actions: Python HTTP, migration, backup and browser markup contract tests, JavaScript syntax, GTK virtual display smoke, Android debug APK build/lint and Docker server readiness.

## Explicit limitations

No production deployment or reviewed release. No invitation email, sharing federation or E2EE; no offline edits, reliable background/push notifications, CalDAV, per-instance recurrence overrides, public publishing, meeting coordination or AI. Linux and Android require device testing and formal package/release acceptance. Photo albums excluded.
