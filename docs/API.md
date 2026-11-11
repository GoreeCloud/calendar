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
| GET | /api/v1/sessions | Count the current user's active sessions |
| POST | /api/v1/sessions/revoke-others | Revoke all other sessions while preserving the current bearer token |
| POST | /api/v1/account/change-password | Reauthenticate and change password; revoke all sessions |
| GET | /api/v1/me | Current account |
| GET, POST | /api/v1/calendars | List owned/shared calendars; create calendar |
| PATCH, DELETE | /api/v1/calendars/{id} | Owner-only update/delete |
| GET, POST | /api/v1/calendars/{id}/members | Owner-only list and set memberships |
| DELETE | /api/v1/calendars/{id}/members/{user_id} | Owner-only revoke |
| GET, POST | /api/v1/events | Query event window; create event |
| PATCH, DELETE | /api/v1/events/{id} | Write-authorized update; version required for PATCH and DELETE |
| GET, POST | /api/v1/events/{id}/exclusions | List or skip individual dates in a recurring series (write role) |
| DELETE | /api/v1/events/{id}/exclusions?occurrence_start_at={iso}&version={n} | Restore one previously skipped occurrence |
| GET, POST | /api/v1/tasks | List and create tasks (optional priority 1–4) |
| PATCH, DELETE | /api/v1/tasks/{id} | Write-authorized task updates and deletions, requiring current task version |
| GET | /api/v1/search?q={query} | Authorized event/task text search |
| GET | /api/v1/availability?calendar_id={id}&start={iso}&end={iso} | Authenticated merged busy intervals (all sharing roles) |
| GET | /api/v1/suggestions?calendar_ids={ids}&start={iso}&end={iso} | Private 9 AM–5 PM scheduling candidates across authorized calendars |
| POST | /api/v1/import.ics | Import supported iCalendar events |
| POST | /api/v1/import-tasks.ics | Import supported iCalendar VTODO tasks into an editable calendar |
| GET | /api/v1/export-tasks.ics?calendar_id={id} | Export tasks from an authorized calendar, except freebusy |
| GET | /api/v1/export.ics?calendar_id={id} | Export an accessible calendar |
| GET | /api/v1/export.json | Export all calendars owned by the current user as a bounded JSON dataset |

Calendar roles: owner (calendar and membership control), edit (change events/tasks), read (view full event/task details and ICS export) and freebusy (view occupied timestamps only). Freebusy responses are redacted: no event IDs, titles, descriptions, locations, reminders, recurrence rules, task data or searchable details; calendar descriptions and owner metadata are not returned. Freebusy members cannot export private ICS, import, or edit. Sharing is local-account-only. Unauthorized calendar IDs are not disclosed.

## Events and recurrence

Event creation requires calendar_id, title, start_at, end_at; optional description, location, all_day, recurrence and reminder_minutes (null or integer 0–43200). Timestamps must be timezone-aware ISO 8601 and are stored as UTC. Event end must be later than start. All-day events have UTC midnight boundaries and exclusive end day.

Event updates require current integer version; stale versions return HTTP 409. Deleting an event also requires `?version=N`, verified as part of a conditional permission-checked DELETE. Missing version yields HTTP 428. Recurrence fields: freq (DAILY, WEEKLY, MONTHLY, YEARLY), interval (1–24), count (2–366), tzid (optional IANA timezone or null). Example recurrence: {"freq":"WEEKLY","interval":1,"count":8,"tzid":"America/Chicago"}. Queries for /events use start and end timestamps, with up to 370 days per request and up to 500 returned occurrences. PATCH/DELETE act on the whole recurring series. For skip/restore, POST /api/v1/events/{id}/exclusions with JSON {"occurrence_start_at":"2026-03-08T14:00:00Z","version":1}, or DELETE with both query parameters, respectively. These operations require an exact generated occurrence, a current series version and write permission; they update the parent version when changed. GET /exclusions returns skipped start instants for editors. Changing series start/end or recurrence rules clears existing exclusions. Full per-instance event overrides remain unsupported.

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

Task creation supports optional integer `priority` with values 1 (urgent), 2 (high), 3 (normal default), and 4 (low). Task updates may change `priority`. PATCH `/api/v1/tasks/{id}` requires an integer `version` in its JSON body; DELETE `/api/v1/tasks/{id}?version=N` requires the current version in the query. Every successful update increments the version and returns the new one. Both stale writes and stale deletions return HTTP 409; missing or invalid versions return HTTP 428. Boolean and out-of-range values return HTTP 400. Existing database tasks are upgraded in place with the default priority 3; the migration preserves their IDs, ownership and due dates. Task filters for open, due today, overdue and completed are currently browser-side views of accessible tasks, not additional server query parameters.

## Browser availability explorer

The web application supplies an authenticated date-and-calendar selection interface on top of `/api/v1/availability`, showing occupied time alongside unscheduled gaps. It does not store or publish these gaps, and does not treat them as confirmed appointment openings. The availability API enforces the same calendar-membership rules as other calendar reads.

## Timezone-aware all-day availability

The optional `tzid` parameter is a server-recognized IANA timezone (for example, `America/Chicago`). For all-day events stored as UTC-midnight calendar dates, the availability calculation reconstructs civil-day start and end in that timezone; this ensures that daylight-saving transitions create the correct 23- or 25-hour local day. With no `tzid`, UTC is used. The browser sends its current IANA timezone automatically. Unsupported zones return HTTP 400; timezone data must be available on the host operating system.

## Private meeting-time suggestions

GET `/api/v1/suggestions` accepts 1–5 distinct comma-separated `calendar_ids`, required timezone-aware `start` and `end` (maximum seven days), an optional IANA `tzid` (UTC by default), and optional `duration_minutes` (15–240 in 15-minute increments; 30 by default). Every calendar must be authorized to the requesting user, including free/busy-only roles. It returns up to 20 candidate half-open intervals within 09:00–17:00 **local** time, excluding busy intervals, skipped recurrence instances and all-day blocked dates. It returns no event identifiers or content. This is not a booking transaction, tentative hold, invitation, resource allocator, or guarantee against subsequent updates. The browser suggests times across the selected and currently visible calendars (maximum five).

## Private owner data export

GET `/api/v1/export.json` returns `goreecloud-calendar-data` schema version 1 with the signed-in user's **owned** calendars (metadata, event fields, recurrence rules, excluded occurrences, reminders and tasks including priority). Shared calendars not owned by the user are deliberately omitted, even when the user can read their event details. Password hashes, salts, authentication sessions, other users, membership lists and private shared-account calendars are excluded. Export is limited to 200 calendars, 5,000 combined event/task records and 5 MiB response size; oversized exports return HTTP 413. The browser offers a local plaintext JSON download after explicit confirmation. **This is a portability snapshot, not a verified restore/import mechanism, retention guarantee or encryption layer.** The file must be protected by its holder.

## Local account security controls

GET `/api/v1/sessions` reports only the number of unexpired sessions belonging to the bearer-token user. POST `/api/v1/sessions/revoke-others` deletes that user's sessions other than the invoking token. POST `/api/v1/account/change-password` requires JSON `current_password` and `new_password` (12–128 characters and different from the current password), verifies the existing password and revokes **all** sessions after changing the scrypt credential hash. The caller must sign in anew. An in-flight old-password login cannot create a new session after rotation: its credential record is rechecked under a SQLite write transaction. These are development features and do not replace production MFA, account recovery, or multi-node token revocation.

## Bounded create-request retry safety

POST `/api/v1/events` and POST `/api/v1/tasks` accept an optional `client_request_id` field of 16–80 ASCII characters from `A–Z`, `a–z`, `0–9`, `_` or `-`. A new ID is generated by the browser for each creation form and reused if that same form's network submission is retried. Request IDs are scoped to the authenticated user and resource kind. The server hashes a canonical JSON representation of the request (excluding the ID), takes a SQLite write lock, and stores the receipt in the same transaction as the new item. First creation returns 201 with `id`, `version` and `replayed:false`; an identical retry within seven days returns 200 with the original `id`, current `version` and `replayed:true`. Reusing an ID with different content or after the original resource has been deleted returns 409. Receipts older than seven days are pruned when keyed creates occur. Requests without IDs retain the original non-idempotent behavior. **This is retry protection within one SQLite instance, not full offline sync, distributed idempotency, an indefinite guarantee or a CalDAV sync-token protocol.**

## VTODO task portability — conservative subset

POST `/api/v1/import-tasks.ics` accepts JSON `{"calendar_id":"...","ics":"BEGIN:VCALENDAR..."}` using the same 64 KiB JSON body limit as other API requests. Input is capped at 55,000 characters and 100 VTODO components. It requires owner/edit permission, and the server rechecks that role after acquiring a SQLite writer lock. Imported UIDs are tracked separately from event UIDs, scoped to the calendar; repeated imports skip duplicates and return `{"imported":N,"skipped":N}` (201). Malformed files and unsupported VTODO fields are rejected with HTTP 400 before importing anything.

GET `/api/v1/export-tasks.ics?calendar_id=...` creates a separate `text/calendar` VTODO-only file for owner, edit or read members, excluding freebusy members and unknown calendars. Exports are capped at 500 tasks. Imported task UIDs are reused, while new tasks use a local stable UID. For task interoperability, `SUMMARY`, UTC or valid IANA-TZID `DUE` datetime (not `VALUE=DATE`), `STATUS:NEEDS-ACTION/COMPLETED`, `PRIORITY` and `UID` are supported; `DTSTAMP` is accepted but not preserved verbatim. The local priority tiers map P1→1, P2→3, P3→5 and P4→9 (RFC 5545 priority values); imported standard values 1–2→P1, 3–4→P2, 5–6→P3, 7–9→P4, and 0/absent→P3. Task recurrence, descriptions, attachments, attendees, alarms, DTSTART and due-date-only values are **not** silently converted—they are rejected. Export and import are **manual one-way file operations**, not CalDAV synchronization, distributed locks, or live conflict resolution.

## Import semantics and silent-loss prevention

Event `.ics` imports reject unsupported top-level scheduling `METHOD` instructions, mixed VTODO components, unsupported nested components, attendee/organizer/attachment/classification fields and unknown VEVENT properties rather than silently discarding them. `STATUS:CONFIRMED` and `TRANSP:OPAQUE` are accepted as equivalent to the local busy event model, but `STATUS:CANCELLED/TENTATIVE` and `TRANSP:TRANSPARENT` are rejected because treating them as ordinary events would misstate availability. Known VTIMEZONE containers may accompany supported IANA TZIDs, but timezone transitions are resolved using host IANA zone data rather than imported VTIMEZONE definitions. File import is not scheduling-message processing or full RFC 5545 roundtrip fidelity; use separate VEVENT and VTODO file flows.

## ICS import dry-run previews

POST `/api/v1/import.ics?dry_run=1` and POST `/api/v1/import-tasks.ics?dry_run=1` parse and validate the selected file, enforce owner/edit calendar permissions, check already imported UIDs and return HTTP 200 with `total`, `would_import`, `would_skip` and up to five `sample_titles`. They make no writes. Values other than `0` and `1` for `dry_run` are rejected. The browser asks for confirmation before an actual import. Preview results are not reserved: permissions and duplicate counts may change; the final import transaction checks both again.

**Title-minimized import preview (development):** Either endpoint also accepts `?dry_run=1&redact_titles=1`. It returns exactly the numeric `total`, `would_import`, and `would_skip` fields, with no `sample_titles`, IDs, descriptions, or ICS content reflected in the result. This is useful for permissioned Mesh/agent integrations that need counts but not personal titles; it **does not** grant permission to upload the ICS input, change the user's consent, or make the preview anonymous. Authentication and owner/edit checks are unchanged. The default `redact_titles=0` retains existing interactive preview behavior. Invalid, duplicate, or blank redaction parameter values, and `redact_titles=1` without `dry_run=1`, return HTTP 400; both endpoints remain non-mutating when previewing. This is not live GoreeCloud Mesh integration or a production deployment.
