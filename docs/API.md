# GoreeCloud Calendar — Development HTTP API

API version: v1. This is a localhost-first development API, not a production public service.

Use Authorization: Bearer TOKEN on every /api/v1 route except /login. JSON bodies require Content-Type: application/json. Session tokens expire after seven days.

## Routes

| Method | Path | Description |
| --- | --- | --- |
| GET | /healthz | Process health |
| POST | /api/v1/login | Login with email/password |
| POST | /api/v1/logout | Revoke session |
| GET | /api/v1/me | Current account |
| GET, POST | /api/v1/calendars | List owned/shared calendars; create calendar |
| PATCH, DELETE | /api/v1/calendars/{id} | Owner-only update/delete |
| GET, POST | /api/v1/calendars/{id}/members | Owner-only list and set memberships |
| DELETE | /api/v1/calendars/{id}/members/{user_id} | Owner-only revoke |
| GET, POST | /api/v1/events | Query event window; create event |
| PATCH, DELETE | /api/v1/events/{id} | Write-authorized event update/delete |
| GET, POST | /api/v1/tasks | List and create tasks |
| PATCH, DELETE | /api/v1/tasks/{id} | Write-authorized task update/delete |
| GET | /api/v1/search?q={query} | Authorized event/task text search |
| POST | /api/v1/import.ics | Import supported iCalendar events |
| GET | /api/v1/export.ics?calendar_id={id} | Export an accessible calendar |

Calendar roles: owner (full control including membership), edit (modify events/tasks), read (view events/tasks and export). Sharing is local-account-only. Unauthorized calendar IDs are not disclosed.

## Events and recurrence

Event creation requires calendar_id, title, start_at, end_at; optional description, location, all_day and recurrence. Timestamps must be timezone-aware ISO 8601 and are stored as UTC. Event end must be later than start. All-day events have UTC midnight boundaries and exclusive end day.

Event updates require current integer version; stale versions return HTTP 409. Recurrence fields: freq (DAILY, WEEKLY, MONTHLY, YEARLY), interval (1–24), count (2–366), tzid (optional IANA timezone or null). Example recurrence: {"freq":"WEEKLY","interval":1,"count":8,"tzid":"America/Chicago"}. Queries for /events use start and end timestamps, with up to 370 days per request and up to 500 returned occurrences. PATCH/DELETE act on the whole recurring series; per-instance editing is not supported.

## ICS portability

POST /api/v1/import.ics accepts JSON with calendar_id and ics string. Limit: at most 100 events, 55,000 characters of ICS content, and 64 KiB total JSON payload. Supports iCalendar folded lines, text escaping, UID deduplication, UTC timestamps, IANA TZID, all-day dates and bounded RRULEs. Unsupported recurrence constructs are rejected rather than silently discarded. Returns imported/skipped counts.

GET /api/v1/export.ics emits owned or shared calendar events, preserving imported UIDs where possible, all-day date types, IANA timezone recurrence and compatible bounded RRULEs. No VTIMEZONE definitions, meeting attendees or alarm rules yet.

## Search

GET /api/v1/search?q=TEXT uses a 2–100 character literal substring. SQL wildcard characters are escaped; result sets are permission-scoped, with up to 50 events and 50 tasks.

## Errors and boundaries

JSON errors use a human-readable error field and relevant HTTP status. This API is not yet rate limited or wrapped in a production authentication/TLS gateway. No E2EE or externally compatible CalDAV server is claimed.
