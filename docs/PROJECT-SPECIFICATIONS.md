# GoreeCloud Calendar — Project Specifications

**Repository:** `GoreeCloud/calendar`  
**Project type:** First-party self-hosted calendar application  
**Lifecycle:** Development  
**Repository visibility:** Public  
**Default branch:** `main`  
**Migration baseline:** `e45c7fac63b4bc61d3ac4e34ef93716d9ca66ff0`  
**License:** AGPL-3.0-only  
**Canonical application address:** `https://calendar.goreecloud.com`  
**Authoritative CalDAV service:** `https://dav.goreecloud.com`  
**Canonical path:** `docs/PROJECT-SPECIFICATIONS.md`  
**Canonical authority:** This file becomes the authoritative repository-local project specification once accepted on the default branch.

## Authority and migration boundary

This specification reconciles Google Drive **Project Specification — Calendar** with verified repository state.

The Drive source accumulated current-state claims from multiple Development checkpoints and includes mutually superseding Glaze UI version statements. Those statements are preserved in `PROJECT-RECORD.md` as historical/candidate evidence. They do not become current implementation truth merely by migration.

At this reconciliation baseline, authoritative `main` is `e45c7fac63b4bc61d3ac4e34ef93716d9ca66ff0`. PR #31 has merged the repository-native feature-state migration; root `IMPLEMENTED-FEATURES.md`, `PLANNED-FEATURES.md`, and `CHANGELOGS.md` now govern feature-state history and planning, while the former `FEATURE-ROADMAP.md` has been retired. PR #22 and the stacked PR #23–#28 Android/Platform/Glaze line remain unmerged candidate work. Candidate behavior remains non-authoritative for `main` until separately accepted, merged, and read back.

## Role and purpose

GoreeCloud Calendar is the user-facing calendar, event, scheduling, agenda, and availability application within GoreeCloud Suite. It is intended to provide a private, self-hosted calendar experience while preserving standards-based interoperability and long-term data portability.

## Authoritative data architecture

Radicale at `https://dav.goreecloud.com` remains authoritative for governed CalDAV calendar collections.

GoreeCloud Calendar is the application and presentation layer at `https://calendar.goreecloud.com`. Calendar may maintain rebuildable application caches, indexes, derived availability information, and integration projections when technically justified, but it must not silently become a competing authoritative calendar store.

## Product capabilities

Calendar is intended to support:
- day, week, month, agenda, and schedule views;
- event creation and editing;
- timed and all-day events;
- recurrence and exceptions;
- timezone-aware scheduling;
- calendar membership and sharing;
- search;
- reminders and alarms;
- availability and conflict visibility;
- import and export;
- accessible responsive interfaces; and
- offline-tolerant behavior where justified.

A planned capability is not an implementation claim unless accepted repository evidence proves it.

## GoreeCloud Tasks integration

Calendar and GoreeCloud Tasks are peer first-party applications connected through explicit versioned APIs.

Tasks remains authoritative for task content, workflow, assignment, project membership, completion, due scheduling, recurrence, labels, comments, and task authorization.

Calendar remains authoritative for native calendar events, calendar ownership and membership, event authorization, calendar-specific metadata, and authorized busy-time context.

Calendar may render authorized Tasks items only as projections and may create or reschedule Tasks work only through Tasks APIs that revalidate normal authorization. Neither application may read or write the other's database directly.

Calendar must continue its native event experience when Tasks is unavailable, and Tasks must remain usable when Calendar is unavailable.

## CalDAV requirements

Calendar must preserve a standards-based CalDAV boundary with:
- HTTPS-only service configuration;
- authenticated discovery;
- bounded calendar-query reads;
- safe iCalendar serialization/parsing;
- optimistic concurrency and ETag protection for destructive writes;
- recurrence and exception support;
- VTIMEZONE/TZID support;
- all-day DATE handling;
- attendees and scheduling where applicable;
- alarms/reminders;
- import/export round-trip behavior;
- extension preservation where safe and supported; and
- fail-closed handling when semantics cannot be trusted.

Unsupported or unknown semantics must not be silently rewritten into a different meaning.

## Security requirements

Calendar must use attributable identities, least privilege, explicit collection/object authorization, protected secrets, and fail-closed request/authentication boundaries.

Reusable DAV passwords, bearer tokens, private event descriptions, private calendar notes, signing material, or other secrets must not be committed to source control or ordinary documentation.

Browser/API security must include applicable HTTPS, origin/CSRF protections, bounded rate limiting, low-detail authentication failures, authorization revalidation, and path/resource confinement.

Wardveil Security governs applicable security authority and evidence. A security-related UI state must not manufacture security truth that is owned by Wardveil or another provider.

## Privacy requirements

Privacy Shield governs applicable privacy-facing behavior, minimization, disclosure, retention, sharing, and data-flow expectations.

Logs and observability must be data-minimized. Tasks busy-time projection must expose only the minimum authorized interval information and must not leak private event titles, descriptions, locations, UIDs, membership, or reusable credentials.

## Glaze UI and accessibility requirements

Calendar must use the latest accepted Stable Glaze UI contract applicable to the product at the time of candidate acceptance.

Historical Drive references to Glaze UI 1.3 and 1.5, and unmerged candidate references to later versions, are migration history rather than a permanent version pin.

Calendar-specific acceptance must cover:
- responsive/adaptive layouts;
- keyboard navigation and visible focus;
- touch-friendly controls;
- screen-reader semantics;
- scalable text;
- reduced motion and reduced transparency;
- forced/high-contrast behavior;
- System, Light, and Dark appearance behavior where applicable;
- loading, empty, error, offline, and conflict states;
- representative browser/device environments; and
- visual/Human Visual Excellence review where required.

Upstream Glaze UI Stable status does not automatically certify Calendar.

## Reliability and failure boundaries

Application caches and projections must be rebuildable.

Network, XML, JSON, schema, version, authorization, authentication, concurrency, and peer-service failures must fail closed where trust or correctness cannot be established.

Failure of Tasks, optional integrations, or derived-data pipelines must not corrupt authoritative CalDAV data.

## Testing requirements

Release-blocking validation must include, where applicable:
- timezone and interval correctness;
- CalDAV discovery, read, create, update, and delete behavior;
- ETag conflict handling;
- recurrence and exception behavior;
- import/export round trips;
- multi-user authorization;
- Tasks integration authorization and failure behavior;
- privacy-minimized projections and logging;
- Glaze UI application-specific rendered/accessibility/resilience acceptance;
- exact-candidate CI;
- real Radicale interoperability;
- browser/device validation; and
- backup/restore and rollback evidence.

## Production readiness

Before production approval, Calendar must have evidence for:
- private DNS and TLS/reverse-proxy boundaries;
- firewall and port exposure;
- production-pattern identities and secret handling;
- real Radicale behavior;
- monitoring and alerting;
- backup and restoration;
- upgrade and rollback;
- representative browser/device acceptance;
- accessibility and responsive visual acceptance;
- Wardveil Security review;
- Privacy Shield review;
- Everkeep recovery/continuity acceptance where applicable;
- applicable platform-system integrations;
- signing/provenance;
- deployment verification; and
- Release Candidate/production/Stable gates.

Green CI, source validation, or an unmerged PR does not establish production or Stable acceptance.

## Native implementation direction

Calendar must remain original GoreeCloud-owned software built from the ground up. Narrow mature technical foundations may be retained only where replacing them would materially increase security, cryptographic, protocol, standards, rendering, operating-system, runtime, or interoperability risk.

Such exceptions must remain bounded to the technical foundation and must not preserve unrelated upstream product architecture, UI, branding, workflows, or general application logic.

## Current default-branch implementation boundary

The migration baseline `main` includes the Calendar product foundation summarized in [README.md](../README.md): timezone-safe event primitives, busy-interval merging, deterministic calendar view projections, versioned first-party API contracts, a fail-closed CalDAV transport foundation, a Glaze-based web application shell, Tasks projection/integration contracts, and dependency-free unit/contract tests.

This remains source foundation evidence, not production acceptance.

## Candidate-stack boundary

PR #22 and stacked PRs #23–#28 are active Development candidates and may contain materially newer Android, Platform Contract, security, and Glaze work. Their state is tracked in GitHub.

No candidate-stack claim becomes current `main` implementation truth through this specification. Each candidate must satisfy its own exact-head validation, review, merge, and post-merge readback requirements.

## Maintenance and retirement

Significant changes to authoritative data ownership, Radicale/CalDAV architecture, Tasks integration, identity/security/privacy authority, Glaze requirements, repository ownership, deployment architecture, lifecycle state, or product retirement must update this specification and `PROJECT-RECORD.md`.

## Related repository documentation

- [README.md](../README.md)
- [PROJECT-RECORD.md](PROJECT-RECORD.md)
- [FEATURE-ROADMAP.md](FEATURE-ROADMAP.md) — legacy migration control pending separate feature-state governance migration.
- [docs/product-foundation.md](docs/product-foundation.md)
- [docs/tasks-integration-contract.md](docs/tasks-integration-contract.md)
- [LICENSE](LICENSE)
- [BRANDING.md](BRANDING.md)
