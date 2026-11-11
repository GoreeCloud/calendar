# GoreeCloud Calendar ↔ GoreeCloud DAV interoperability plan

**Status:** Engineering contract and proposed integration sequence. It does not implement, deploy, or verify live CalDAV synchronization.

## Verified source boundary (November 10, 2026)

- Calendar is a self-hosted Python/SQLite development preview with its own local bearer sessions, event/task models, ICS import/export, user-managed owner/read/edit/freebusy permissions and no live DAV client or server.
- The separate **GoreeCloud DAV** development branch \`feat/goreecloud-dav-foundation-20261105\` (draft PR #1) already implements an experimental SabreDAV-based CalDAV/CardDAV/WebDAV server. Its source describes discovery at \`/.well-known/caldav\`, principal and calendar-home-set PROPFIND, and user calendars under \`/calendars/{username}/default/\`. It uses account-specific Argon2id Basic authentication and separate per-account stores. Independent vdirsyncer synthetic interoperability tests exist, but they have not exercised the Calendar application.
- These two applications currently have different account credentials, repositories, stores, lifecycles and privacy authorizations. **Do not treat matching email addresses or usernames as verified identity federation.**

Primary references: [GoreeCloud DAV development branch](https://github.com/GoreeCloud/DAV/tree/feat/goreecloud-dav-foundation-20261105) and its \`docs/CLIENT-INTEGRATION.md\`, \`docs/ARCHITECTURE.md\`, and \`docs/SECURITY.md\`.

## Recommended architecture — reuse, do not duplicate

1. Decide which system owns canonical calendar objects *before* writing synchronization. Prefer a single canonical DAV collection with stable principal identity and distinct Calendar UI/API application logic. Do not silently dual-write the Calendar and DAV SQLite databases.
2. Define a verified identity translation policy. Calendar's bearer sessions cannot be passed off as DAV Basic credentials. For a transitional integration, use a server-side, explicitly provisioned and scoped client credential under verified HTTPS; **never embed a DAV password in JavaScript, local storage, Android settings or committed configuration**. App-specific token support in DAV is pending.
3. Keep Calendar role checks and GoreeShield policies enforceable at the integration boundary. A Calendar freebusy reader must not receive full DAV resources, even if generic DAV ACLs allow collection reads. Deny by default until DAV policy mapping is tested.
4. Preserve stable \`UID\`, \`ETag\`, and \`sync-token\` semantics; use conditional HTTP writes and handle 409/412/423/507 without data-loss retries. Idempotent mapping of recurrence masters, exceptions and deleted UIDs requires a versioned migration ledger and tested conflict recovery.
5. Preserve iCalendar \`TZID\`, \`VTIMEZONE\`, \`RRULE\`, \`EXDATE\`, \`RECURRENCE-ID\`, and \`VALARM\` details without lossy projection. Calendar currently supports a bounded RRULE/EXDATE/VALARM subset and does **not** export complete VTIMEZONE definitions or per-occurrence overrides. Do not claim full fidelity; detect, reject or retain unsupported elements as appropriate.
6. Tasks now have a **separate bounded VTODO-only .ics import/export subset** in Calendar for manual portability. It covers UID, SUMMARY, due datetime, completion status and mapped priorities, but not task recurrence, attendee fields, alarms, attachment data or all-day DUE values. The event ICS export still does not include tasks. The DAV backend has VTODO-oriented tests, but **no end-to-end exchange between these applications has been performed**; native task operations are not two-way synchronized.
7. Test with disposable, least-privilege two-account server instances. Include principal discovery, strict TLS/redirect handling, ETag create/update/delete, incremental REPORT pagination, reset/expired sync tokens, recurrence/DST, read-only/freebusy isolation, task round-trips, network retries and reversibility.
8. Complete GoreeCloud Identity, GoreeCloud Mesh, GoreeShield and Wardveil integration reviews before any production credential binding, URL exposure, migration or automatic background sync.

## Current practical workflow

For development-only manual exchange, Calendar supports separate authenticated event VEVENT and task VTODO ICS exports/imports, and DAV accepts iCalendar resources. **No end-to-end exchange between these two repositories has been executed or validated by this document.** Its purpose is to prevent duplicate protocol implementations and define the conditions for a controlled, tested bridge.

No public booking links, push notifications, cross-service credentials, live DAV endpoints, new deployment, or data migration were created by this plan.
