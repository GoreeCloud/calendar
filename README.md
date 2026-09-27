# GoreeCloud Calendar

Privacy-first, self-hosted calendar application for the GoreeCloud Suite.

## Role

GoreeCloud Calendar is the user-facing application for calendars, events, scheduling, agenda and availability workflows. Its canonical application address is `https://calendar.goreecloud.com`.

The shared Radicale service at `https://dav.goreecloud.com` remains the authoritative CalDAV service. Calendar is an application and presentation layer over that standards-based data boundary rather than a second authoritative calendar store.

## Current foundation

The repository now includes:

- timezone-safe calendar event domain primitives and busy-interval merging;
- deterministic month, week, day, and agenda view-window projections;
- versioned first-party event-view and privacy-minimized busy-time API contracts;
- a fail-closed CalDAV transport foundation with HTTPS-only configuration, cross-origin refusal, authenticated discovery, bounded calendar-query reads, ETag-protected writes/deletes, and iCalendar serialization;
- a Glaze UI V1.4 / `1.5.1` application source target for the native Android line, pinned to current Stable authority while downstream application acceptance remains in progress;
- a dedicated first-party Kotlin/Jetpack Compose Android Development client whose Radicale/CalDAV authority, GoreeCloud Identity prerequisite, read-contract boundary, optional Calendar Provider bridge, and blocked transport/synchronization states are documented independently;
- the strict GoreeCloud Tasks projection consumer and bidirectional Tasks integration contract;
- dependency-free unit/contract tests suitable for CI.

The web/server source and the native Android Development client are distinct runtime surfaces over the same Calendar authority model. The Android client does not contact Radicale directly, copy browser cookies, or create a second authoritative event database. Its future network, offline, background-sync, mutation, and Calendar Provider capabilities remain separately gated.

This is a source foundation, not production acceptance. Production publication, production DAV credentials, user migration, monitoring, backup/recovery evidence, live target-environment validation, GLAZE UI V1.6 / 1.6.0 application acceptance, and production Android signing remain separate controlled work.

## CalDAV compatibility boundary

The initial read parser intentionally accepts the UTC VEVENT subset the GoreeCloud Calendar serializer emits. Full third-party CalDAV compatibility still requires recurrence and exceptions, VTIMEZONE/TZID handling, attendees and scheduling, alarms, all-day DATE values, arbitrary extension preservation, and broader RFC interoperability tests. Unsupported semantics must fail closed or remain opaque rather than being silently rewritten.

## First-party Tasks integration

GoreeCloud Calendar and GoreeCloud Tasks are peer first-party applications. Calendar remains authoritative for native event semantics and authorized busy-time context; Tasks remains authoritative for task content, workflow, completion, assignment, and recurrence.

Integration uses versioned application APIs. Neither application may read or write the other's database directly or broaden a user's permissions through a service credential. The Calendar busy-time contract exposes only occupied intervals; it does not expose event titles, descriptions, locations, or calendar membership to Tasks. See `docs/tasks-integration-contract.md`.

## Integral Platform Systems boundary

Calendar uses Platform Contract `0.3` to declare all eight Integral Platform Systems explicitly: Manager, Privacy Shield, Wardveil Security, Everkeep, GLAZE UI, Mesh, Identity, and Sync.

These declarations are fail-closed Development truth. In particular, GoreeCloud Sync remains separate from CalDAV authority, the optional Android Calendar Provider bridge, and Everkeep backup/recovery. No Platform Contract declaration converts a source contract into runtime acceptance or production authority.

## Architecture and readiness

See `docs/product-foundation.md` for product scope, DAV boundaries, Glaze UI expectations, security/privacy requirements, and production-readiness gates. See `clients/android/README.md` for the dedicated native Android architecture and capability boundaries.

## Development

Run the dependency-free test suite with:

```bash
python -m unittest discover -s tests -v
```

## License

GoreeCloud Calendar is licensed under the GNU Affero General Public License, version 3 only (`AGPL-3.0-only`). See `LICENSE`.