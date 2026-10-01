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
- a Glaze UI 1.3 application shell with responsive view switching, date navigation, event rendering, event-creation workflow, keyboard focus treatment, reduced-motion/transparency handling, and forced-colors support;
- the strict GoreeCloud Tasks projection consumer and bidirectional Tasks integration contract;
- dependency-free unit/contract tests suitable for CI.

This is a source foundation, not production acceptance. Production publication, production DAV credentials, user migration, monitoring, backup/recovery evidence, and live target-environment validation remain separate controlled work.

## CalDAV compatibility boundary

The initial read parser intentionally accepts the UTC VEVENT subset the GoreeCloud Calendar serializer emits. Full third-party CalDAV compatibility still requires recurrence and exceptions, VTIMEZONE/TZID handling, attendees and scheduling, alarms, all-day DATE values, arbitrary extension preservation, and broader RFC interoperability tests. Unsupported semantics must fail closed or remain opaque rather than being silently rewritten.

## First-party Tasks integration

GoreeCloud Calendar and GoreeCloud Tasks are peer first-party applications. Calendar remains authoritative for native event semantics and authorized busy-time context; Tasks remains authoritative for task content, workflow, completion, assignment, and recurrence.

Integration uses versioned application APIs. Neither application may read or write the other's database directly or broaden a user's permissions through a service credential. The Calendar busy-time contract exposes only occupied intervals; it does not expose event titles, descriptions, locations, or calendar membership to Tasks. See `docs/tasks-integration-contract.md`.

## Architecture and readiness

See `docs/product-foundation.md` for product scope, DAV boundaries, Glaze UI expectations, security/privacy requirements, and production-readiness gates.

## Development

Run the dependency-free test suite with:

```bash
python -m unittest discover -s tests -v
```

## License

GoreeCloud Calendar is licensed under the GNU Affero General Public License, version 3 only (`AGPL-3.0-only`). See `LICENSE`.


## Project governance

- [Project specifications](docs/PROJECT-SPECIFICATIONS.md) — authoritative project scope, requirements, data-authority boundaries, privacy/security requirements, and acceptance gates once this migration is accepted on `main`.
- [Project record](docs/PROJECT-RECORD.md) — significant project history, candidate-stack context, governance transitions, and migration evidence.

Repository-native feature state is maintained in `IMPLEMENTED-FEATURES.md`, `PLANNED-FEATURES.md`, and `CHANGELOGS.md`. The retired `FEATURE-ROADMAP.md` and its former Google Drive synchronization model must not be recreated as competing authority.
