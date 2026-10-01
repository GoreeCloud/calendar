# GoreeCloud Calendar Android Client

This directory is the dedicated native Android application line for GoreeCloud Calendar.

## Architecture authority

The shared GoreeCloud Radicale/CalDAV service remains the authoritative calendar store. The Android application must not create a second authoritative event database. Any local persistence is a bounded offline/cache representation with explicit synchronization, ETag/precondition handling, and deterministic conflict behavior.

Android's Calendar Provider is an optional device-integration bridge, not the GoreeCloud source of truth. Provider access must be separately permissioned, purpose-bound, user-controlled, and independently accepted before enablement.

## Current Development foundation

- Kotlin/Jetpack Compose application module targeting SDK 36 with minimum SDK 29 and Java 17.
- Launchable native Calendar Development surface.
- Explicit runtime capability state for Identity, CalDAV read/write, offline cache, background synchronization, and the Android Calendar Provider bridge.
- All data capabilities remain `NOT_IMPLEMENTED`; the manifest requests neither network nor Calendar Provider permissions.
- Android backup disabled.
- Unit coverage proving the shell does not advertise unavailable capability.
- Gradle caching, parallel execution, and incremental Kotlin compilation.

## Next milestones

1. Identity/session binding with no reusable credentials in source control.
2. Read-only CalDAV discovery and calendar/event listing against Development data.
3. ETag/precondition-safe event create/edit/delete and visible conflict resolution.
4. Recurrence, exceptions, VTIMEZONE/TZID, all-day events, attendees/scheduling, alarms, and extension-preserving interoperability.
5. Protected bounded offline cache and deterministic reconciliation.
6. WorkManager/background synchronization with power/network constraints.
7. Optional Android Calendar Provider bridge with explicit permissions and user controls.
8. Glaze UI V1.3 application-level migration, accessibility, form-factor, and representative-device acceptance.
9. Independent Privacy Shield, Wardveil Security, Everkeep, Manager, Mesh, Identity, signing/provenance, recovery, Release Candidate, production, and Stable gates.

A successful source build or CI run is Development evidence only and does not grant production or platform-system acceptance.
