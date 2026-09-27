# GoreeCloud Calendar Android Client

This directory is the dedicated native Android application line for GoreeCloud Calendar.

## Architecture authority

The shared GoreeCloud Radicale/CalDAV service remains the authoritative calendar store. The Android application must not create a second authoritative event database. Any future local persistence is a bounded offline/cache representation with explicit synchronization, ETag/precondition handling, and deterministic conflict behavior.

Android's Calendar Provider is an optional device-integration bridge, not the GoreeCloud source of truth. Provider access must be separately permissioned, purpose-bound, user-controlled, and independently accepted before enablement.

## Current Development foundation

- Kotlin/Jetpack Compose application module targeting SDK 36 with minimum SDK 29 and Java 17.
- Launchable native Calendar Development surface.
- Repository-local GLAZE UI V1.6 / `1.6.0` adoption boundary pinned to Stable authority `a7180679ea851389e0f3004515f9a25f420e716d`, with V1.5.1 retained as the immediate rollback baseline and downstream conformance still `ADOPTION_IN_PROGRESS`.
- Explicit runtime capability state for Identity, CalDAV read/write, offline cache, background synchronization, and the Android Calendar Provider bridge.
- A pure Kotlin read-contract model for the existing session-authorized `/api/v1/events` and `/api/v1/busy-time` endpoints.
- Fail-closed request construction: calendar hrefs must be bounded, canonical server-relative identifiers; view modes are restricted to the server contract; busy-time windows use timezone-aware values with positive duration.
- A transport-neutral **Calendar response acceptance** contract for `goreecloud.calendar.events.v1` and the privacy-minimized `goreecloud.calendar.busy.v1` projection.
- Exact response field allowlists so future decoding rejects backend, credential, calendar-authority, or event-detail fields that are outside each accepted schema.
- Event-response checks for exact schema/version/view/timezone, positive response range, count equality, unique event identities, valid event intervals, and response-window overlap.
- Busy-response checks for exact requested range, count equality, positive clipped intervals, request-range containment, strict ordering, and non-overlap.
- Native Identity/session exchange and network transport remain blocked. The manifest still requests neither `INTERNET` nor Calendar Provider permissions.
- Android backup disabled.
- Mandatory first-use setup now persists interruption/resume state, explains current Identity/CalDAV/network/Calendar Provider boundaries, enables contextual hints by default, and provides global hint disable/re-enable, dismissed-hint reset, and voluntary setup replay controls.
- Unit coverage proving unavailable runtime capability is not advertised as accepted and source-ready request/response contracts cannot broaden origin/identity authority.
- Gradle caching, parallel execution, and incremental Kotlin compilation.

A source-ready endpoint or response contract is not a live CalDAV connection. The Android client has **no network authority** in this tranche: it does not copy browser cookies, embed reusable service credentials, invent bearer tokens, contact Radicale directly, or parse remote JSON.

Shared GLAZE UI V1.6 qualification is not Calendar-local acceptance. Repository-local optical behavior, accessibility, representative-device behavior, performance, Human Visual Excellence, rollback, and release evidence remain separate fail-closed gates.

## Calendar response acceptance boundary

The event-view contract accepts only the current server shape:

- `schema`, `version`, `view`, `timezone`, response `range`, `returned`, and `events`;
- each event: `uid`, `title`, `starts_at`, `ends_at`, `description`, `location`, `all_day`, and `etag`.

The busy-time contract is intentionally narrower. It accepts only:

- `schema`, `version`, response `range`, `returned`, and `busy`;
- each busy interval: `starts_at` and `ends_at`.

Busy-time responses therefore cannot carry event UID, title, description, location, ETag, attendee, alarm, credential, backend, or calendar-origin fields through the accepted native model. The intervals must remain within the exact requested range and strictly ordered/non-overlapping, matching the server's merged least-privilege projection.

`CalendarResponseContract` performs no HTTP, authentication, JSON parsing, storage, mutation, Calendar Provider access, or synchronization. A future exact-field decoder must reject unknown fields before handing typed values to the acceptance policy.

A successful response decision means only that already-decoded Development data conforms to the expected minimized schema. It does not authenticate the caller, prove a GoreeCloud Identity session, authorize event access, or make the response durable authority.

## Next milestones

1. Define and accept first-party GoreeCloud Identity/session exchange for native Calendar without reusable application-wide credentials.
2. Add an exact-field decoder for `goreecloud.calendar.events.v1` and `goreecloud.calendar.busy.v1`; reject unknown fields before `CalendarResponseContract` evaluation.
3. Add a bounded same-origin authenticated transport adapter and exercise read-only event listing/busy-time retrieval against non-production Development data.
4. Add calendar discovery if/when a native-safe scoped discovery contract is exposed by the Calendar service; do not bypass the service with direct Radicale discovery.
5. Add ETag/precondition-safe event create/edit/delete and visible conflict resolution.
6. Complete recurrence, exceptions, VTIMEZONE/TZID, all-day events, attendees/scheduling, alarms, and extension-preserving interoperability.
7. Add protected bounded offline cache and deterministic reconciliation.
8. Add WorkManager/background synchronization with power/network constraints.
9. Add the optional Android Calendar Provider bridge with explicit permissions and user controls.
10. Complete repository-local GLAZE UI V1.6 rendered, accessibility, form-factor, representative-device, performance, Human Visual Excellence, and rollback acceptance.
11. Complete independent Privacy Shield, Wardveil Security, Everkeep, Manager, Mesh, Identity, Sync, signing/provenance, recovery, Release Candidate, production, and Stable gates.

A successful source build or CI run is Development evidence only and does not grant production or platform-system acceptance.
