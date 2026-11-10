# GoreeCloud Calendar — Development HTTP API

API version: v1. This is a localhost-first development API, not a production public service.

Use Authorization: Bearer TOKEN on every /api/v1 route except /login. JSON bodies require Content-Type: application/json. Session tokens expire after seven days.

## Routes

| Method | Path | Description |
| --- | --- | --- |
| GET | /healthz | Process liveness |
| GET | /readyz | Persistent database readiness |
| POST | /api/v1/login | Login with email/password |
| POST | /api/v1/logout | Revoke session |
| GET | /api/v1/me | Current account |
| GET, POST | /api/v1/calendars | List owned/shared calendars; create calendar |
| PATCH, DELETE | /api/v1/calendars/{id} | Owner-only update/delete |
| GET, POST | /api/v1/calendars/{id}/members | Owner-only list and set memberships |
| DELETE | /api/v1/calendars/{id}/members/{user_id} | Owner-only revoke |
| GET, POST | /api/v1/events | Query event window; create event |
| PATCH, DELETE | /api/v1/events/{id} | Write-authorized event update/delete |
| GET, POST | /api/v1/events/{id}/exclusions | List or skip individual dates in a recurring series (write role) |
| DELETE | /api/v1/events/{id}/exclusions?occurrence_start_at={iso}&version={n} | Restore one previously skipped occurrence |
| GET, POST | /api/v1/tasks | List and create tasks (optional priority 1–4) |
| PATCH, DELETE | /api/v1/tasks/{id} | Write-authorized task update/delete (including priority 1–4) |
| GET | /api/v1/search?q={query} | Authorized event/task text search |
| GET | /api/v1/availability?calendar_id={id}&start={iso}&end={iso} | Authenticated merged busy intervals (all sharing roles) |
| POST | /api/v1/import.ics | Import supported iCalendar events |
| GET | /api/v1/export.ics?calendar_id={id} | Export an accessible calendar |

Calendar roles: owner (calendar and membership control), edit (change events/tasks), read (view full event/task details and ICS export) and freebusy (view occupied timestamps only). Freebusy responses are redacted: no event IDs, titles, descriptions, locations, reminders, recurrence rules, task data or searchable details; calendar descriptions and owner metadata are not returned. Freebusy members cannot export private ICS, import, or edit. Sharing is local-account-only. Unauthorized calendar IDs are not disclosed.

## Events and recurrence

Event creation requires calendar_id, title, start_at, end_at; optional description, location, all_day, recurrence and reminder_minutes (null or integer 0–43200). Timestamps must be timezone-aware ISO 8601 and are stored as UTC. Event end must be later than start. All-day events have UTC midnight boundaries and exclusive end day.

Event updates require current integer version; stale versions return HTTP 409. Recurrence fields: freq (DAILY, WEEKLY, MONTHLY, YEARLY), interval (1–24), count (2–366), tzid (optional IANA timezone or null). Example recurrence: {"freq":"WEEKLY","interval":1,"count":8,"tzid":"America/Chicago"}. Queries for /events use start and end timestamps, with up to 370 days per request and up to 500 returned occurrences. PATCH/DELETE act on the whole recurring series. For skip/restore, POST /api/v1/events/{id}/exclusions with JSON {"occurrence_start_at":"2026-03-08T14:00:00Z","version":1}, or DELETE with both query parameters, respectively. These operations require an exact generated occurrence, a current series version and write permission; they update the parent version when changed. GET /exclusions returns skipped start instants for editors. Changing series start/end or recurrence rules clears existing exclusions. Full per-instance event overrides remain unsupported.

## ICS portability

POST /api/v1/import.ics accepts JSON with calendar_id and ics string. Limit: at most 100 events, 55,000 characters of ICS content, and 64 KiB total JSON payload. Supports iCalendar folded lines, text escaping, UID deduplication, UTC timestamps, IANA TZID, all-day dates and bounded RRULEs. Unsupported recurrence constructs are rejected rather than silently discarded. Supported EXDATE exception lists and display VALARM relative reminders are preserved on import. Returns imported/skipped counts.

GET /api/v1/export.ics emits owned or shared calendar events, preserving imported UIDs where possible, all-day date types, IANA timezone recurrence and compatible bounded RRULEs. Export includes EXDATE and a single display VALARM when present; VTIMEZONE definitions, meeting attendees and multiple or non-display alarm types are not supported.

## Search

GET /api/v1/search?q=TEXT uses a 2–100 character literal substring. SQL wildcard characters are escaped; result sets are permission-scoped, with up to 50 events and 50 tasks.

## Errors and boundaries

JSON errors use a human-readable error field and relevant HTTP status. Authentication has an in-memory per-IP failed-login limit (10 attempts per five minutes), but there is no distributed production throttle or validated authentication/TLS gateway. No E2EE or externally compatible CalDAV server is claimed.

## Availability

GET /api/v1/availability requires calendar_id and timezone-aware start/end strings for a window no longer than 90 days. It returns merged, sorted UTC busy intervals clipped to the requested window. Recurrences and skipped dates are honored. The route accepts any locally authorized calendar role, including freebusy, and does not reveal titles, locations, event IDs, reminders, or tasks. It does not impose working hours, calculate travel buffers, publish availability publicly, or provide a booking page.

## Task priorities

Task creation supports optional integer `priority` with values 1 (urgent), 2 (high), 3 (normal default), and 4 (low). Task updates may change `priority`. Boolean and out-of-range values return HTTP 400. Existing database tasks are upgraded in place with the default priority 3; the migration preserves their IDs, ownership and due dates. Task filters for open, due today, overdue and completed are currently browser-side views of accessible tasks, not additional server query parameters.

## Browser availability explorer

The web application supplies an authenticated date-and-calendar selection interface on top of `/api/v1/availability`, showing occupied time alongside unscheduled gaps. It does not store or publish these gaps, and does not treat them as confirmed appointment openings. The availability API enforces the same calendar-membership rules as other calendar reads.
