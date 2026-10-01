# GoreeCloud Calendar — Project Record

**Repository:** `GoreeCloud/calendar`  
**Lifecycle:** Development  
**Record purpose:** Significant project history, architecture/governance transitions, candidate-stack evidence, and migration provenance  
**Migration baseline:** `e45c7fac63b4bc61d3ac4e34ef93716d9ca66ff0`  
**Canonical path:** `docs/PROJECT-RECORD.md`  
**Canonical authority:** This file becomes the repository-local project record once accepted on the default branch.

## Project foundation

Calendar was established as GoreeCloud's user-facing calendar application over an authoritative Radicale/CalDAV data boundary. The project preserves a clear distinction between Calendar-owned event presentation/workflows and Tasks-owned task/workflow authority.

## 2026-09-09 — Verified default-branch baseline

At that historical checkpoint, authoritative `main` was `11f8b499fb297d179a77af10d780325eeaebb78e`.

The repository README describes a source foundation including timezone-safe event primitives, calendar-view projections, CalDAV transport behavior, first-party API contracts, a Glaze UI shell, Tasks integration contracts, and tests. The README explicitly states that production publication, production DAV credentials, user migration, monitoring, backup/recovery evidence, and live target-environment validation remain separate controlled work.

## 2026-09-13 to 2026-09-15 — Unmerged candidate stack

Live GitHub shows PR #22 as a non-Draft Development candidate based on the current `main`, with stacked Draft PRs #23–#28 carrying later Android, Platform Contract, security/response-acceptance, and Glaze work.

Those pull requests are candidate evidence only. They do not alter authoritative default-branch implementation state until accepted, merged, and read back.

## 2026-09-27 — Feature-state migration integrated

PR #31 merged as authoritative main `e45c7fac63b4bc61d3ac4e34ef93716d9ca66ff0`, replacing the legacy Drive-synchronized feature roadmap with repository-native `IMPLEMENTED-FEATURES.md`, `PLANNED-FEATURES.md`, and `CHANGELOGS.md`. The former `FEATURE-ROADMAP.md` was preserved under repository history and retired from the active root. This project-governance migration must not recreate that retired file or restore Google Drive synchronization authority.

## 2026-10-01 — Project governance migration reconciled

The earlier PR #29 project-governance candidate was based on pre-feature-migration main and became non-mergeable after PR #31 advanced authoritative state. The migration is therefore rebuilt from current main and placed under `docs/` to comply with the repository-root documentation standard. The current migration:
- creates `docs/PROJECT-SPECIFICATIONS.md`;
- creates `docs/PROJECT-RECORD.md`;
- updates README navigation;
- preserves the complete former Drive source below as historical/source-era evidence; and
- leaves current repository-native feature-state files and runtime source unchanged.

## 2026-09-24 — Earlier project governance migration candidate

This migration:
- creates root `PROJECT-SPECIFICATIONS.md`;
- creates root `PROJECT-RECORD.md`;
- migrates the still-applicable requirements from the Drive Calendar specification;
- preserves the complete former Drive source below as historical/candidate evidence;
- updates README navigation; and
- removes stale Drive synchronization authority from the legacy `FEATURE-ROADMAP.md` without performing the separate feature-state migration.

**Drive source:** Project Specification — Calendar.docx  
**Drive file ID:** `1_maL961cA2__L8YsYENp6vxPv7ZAa70L`  
**Drive deletion status:** Blocked until accepted/default-branch readback and all migration verification gates pass.

# Imported Drive Source Record

The full source follows for content preservation and provenance. Current-state claims inside this imported section are source-era statements; they do not override newer live GitHub state or the canonical specification above.

---

Project Specification — Calendar
Document Metadata
Document Owner: LaDamian Goree
Version: v0.1
Status: Active Development — Platform Contract v0.2 and Governed Feature Roadmap Candidates Validated; Production Acceptance Pending
Classification: Internal
Document Type: Software Project Specification and Implementation Blueprint
Project Name: GoreeCloud Calendar
Repository: GoreeCloud/goreecloud-calendar
Development Model: Original GoreeCloud-owned software development
Approved License: GNU Affero General Public License v3.0 only (AGPL-3.0-only)
Third-Party Licensing: Separately licensed dependencies and components retain their applicable licenses.
Canonical Application Address: https://calendar.goreecloud.com
Canonical CalDAV Service: https://dav.goreecloud.com
Design Language: GLAZE UI V1.3 / 1.3.0 — current Stable source target; Calendar application migration and acceptance required
Security Identity: Wardveil Security by GoreeCloud
Authoritative Record: Yes
1. Role and Purpose
I use GoreeCloud Calendar as the user-facing calendar, event, scheduling, agenda, and availability application within GoreeCloud Suite. I use it to provide a private, self-hosted calendar experience that I control while preserving standards-based interoperability and long-term data portability.
2. Authoritative Data Architecture
I preserve Radicale at https://dav.goreecloud.com as the authoritative standards-based CalDAV service for governed calendar collections. GoreeCloud Calendar is the application and presentation layer at https://calendar.goreecloud.com. I may maintain application-specific caches, indexes, derived availability data, and integration projections when technically justified, but I will not create a competing authoritative calendar store without a separately approved architecture change.
3. Product Capabilities
I intend GoreeCloud Calendar to provide day, week, month, agenda, and schedule views; event creation and editing; timed and all-day events; recurrence and exceptions; timezone-aware scheduling; calendar membership and sharing; search; reminders; availability and conflict visibility; import and export; accessible responsive interfaces; and offline-tolerant client behavior where justified.
4. GoreeCloud Tasks Integration
I integrate GoreeCloud Calendar and GoreeCloud Tasks as peer first-party applications through explicit versioned APIs. Tasks remains authoritative for task content, workflow, assignment, project membership, completion, due scheduling, recurrence, labels, comments, and task authorization. Calendar remains authoritative for native calendar events, calendar ownership and membership, event authorization, calendar-specific metadata, and busy-time context. Calendar may render authorized Tasks items only as projections and may create or reschedule Tasks work only through Tasks APIs that revalidate normal authorization. Neither application may access the other's database directly.
5. CalDAV Foundation
The source foundation merged through PR #5 adds timezone-aware event-domain primitives, busy-interval merging, HTTPS-only CalDAV configuration, cross-origin request refusal, authenticated calendar discovery, iCalendar event serialization, and ETag-protected event creation, update, and deletion. PR #6 extends that foundation with bounded CalDAV calendar-query REPORT reads, fail-closed parsing for the supported UTC VEVENT subset, deterministic month/week/day/agenda view windows, versioned event-view API payloads, privacy-minimized busy-time projections for Tasks, and a responsive Glaze UI application shell. This source state is not production acceptance and does not provision production credentials or change Radicale runtime state.
6. Glaze UI
I require the Calendar interface to use Glaze UI 1.5.0, the current Stable design-system contract, across navigation, calendar grids, event surfaces, dialogs, forms, search, settings, errors, loading states, and responsive layouts. The earlier Glaze UI 1.3 shell and source evidence remain historical migration evidence only and do not establish current conformance. Solid and Raised surfaces remain valid content layers, with material/depth roles, motion, spacing/density, interaction states, adaptive behavior, and semantic color governed by 1.5.0. Keyboard access, visible focus, reduced motion, reduced transparency, forced-colors support, touch-friendly controls, and System, Light, and Dark appearance behavior remain required. Calendar must complete application-specific 1.5.0 source, rendered, accessibility, resilience, and representative target-environment acceptance before current Glaze UI conformance or Stable qualification can be claimed.
7. Privacy and Security
I require individual attributable identities, least privilege, collection-level and object-level authorization, protected secrets, data-minimized logs, and explicit optimistic concurrency for destructive DAV mutations. PR #7 adds authorization-scoped Calendar principals, explicit read/write collection capabilities, server-side enforcement that prevents clients from self-asserting identity or permissions, and destructive-event path confinement to the authorized collection. PR #8 adds a separate trusted browser-request security boundary that requires HTTPS request context, enforces same-origin requests when Origin is present, requires matching CSRF evidence for unsafe methods, supports injectable subject-keyed rate limiting, and returns deliberately low-detail rejection responses. PR #9 adds provider-agnostic trusted session claims with audience and expiry validation, maps only validated server-derived claims into CalendarPrincipal, adds low-detail authentication failure handling before browser and API authorization, and establishes a runtime DAV credential-provider contract resolved by authenticated subject. DAV passwords are excluded from object representations, DAV endpoints must use HTTPS, and credentials may not be embedded in URLs. PR #10 adds concrete replaceable runtime adapters: HMAC-SHA256 session-token verification with runtime-injected signing material, a permission-checked file-backed DAV credential mapping whose reusable password remains process-secret injected, and structured metadata-only observability with salted pseudonymous subject references. I will not store reusable DAV passwords, bearer tokens, private event descriptions, private calendar notes, or unnecessary personal content in source control or ordinary documentation. Wardveil Security governs security presentation and controls; GoreeCloud Privacy Shield governs privacy-facing behavior and data-flow expectations.
8. Reliability and Failure Boundaries
Calendar must continue to provide its native event experience when GoreeCloud Tasks is unavailable. Tasks must remain usable when Calendar is unavailable. Integration failures must degrade safely rather than corrupting authoritative data. Application caches and projections must be rebuildable. Network, XML, JSON, schema, version, authorization, and concurrency failures must fail closed where trust cannot be established.
9. Testing Requirements
Launch-blocking validation includes timezone and interval correctness; CalDAV discovery; create, update, and delete behavior; ETag conflict handling; recurrence and exception behavior; import and export round trips; multi-user authorization; Tasks integration authorization; peer-service failure behavior; Glaze UI 1.5.0 application-specific responsive, interaction-state, material, motion, density, accessibility, and resilience acceptance; data-minimized logging; and exact-revision CI.
10. Production Readiness
Before production approval I will validate private DNS, Caddy, NetBird, TLS, firewall and port boundaries, real Radicale CalDAV behavior, production-pattern identities and secret handling, monitoring and alerting, backup and restoration, upgrade and rollback, real-browser acceptance, accessibility, responsive visual acceptance, Wardveil Security review, Privacy Shield review, and recovery evidence against the exact candidate revision.
11. Current State
The repository was initially created as a small architecture and Tasks-integration foundation. PR #5 expanded it into the first substantive Calendar product foundation. PR #6 added the initial application-facing API and Glaze UI shell, bounded CalDAV event reads, supported-subset VEVENT parsing, view-window projections, and privacy-minimized busy-time integration. PR #7 added the first authenticated runtime-service boundary with authorization-scoped principals, collection-level read/write enforcement, an injected CalendarService over the CalDAV-compatible store, and versioned JSON HTTP dispatch. PR #8 hardened that runtime boundary with trusted HTTPS request-context validation, same-origin enforcement, CSRF protection for unsafe methods, injectable subject-keyed rate limiting, and low-detail security rejection responses. PR #9 added provider-agnostic trusted session claims, opaque session authentication, session subject/audience/expiry validation, server-derived CalendarPrincipal mapping, low-detail 401 behavior, and runtime-only DAV credential-provider interfaces resolved by authenticated subject. PR #10 adds HMAC-SHA256 verification for trusted session tokens using a runtime-injected signing key, a file-backed DAV credential provider that rejects group/other-accessible mappings and resolves the actual DAV password from process secret injection, plus privacy-safe structured observability that records only request metadata and salted pseudonymous subject references. Exact PR #10 head bc2e8e3e6124133f96dc330ebd439e2617d47112 passed CI run 32460301176 before squash merge to main as c9ca07b0858fa19e4496201a27a4662ccffde2a6. This source acceptance does not approve production deployment; target-environment production-readiness gates remain outstanding.
12. Immediate Next Actions
After the concrete runtime-adapter milestone, I will perform isolated live acceptance of the session, credential, observability, Radicale, and reverse-proxy path using test-only identities and secrets before any production cutover. I will then decide whether the HMAC session provider and file/environment credential adapter remain acceptable for the initial deployment or should be substituted behind their existing contracts by GoreeCloud Identity and an approved secret backend; I will also replace or back the in-memory rate limiter with an approved production-grade shared limiter where required. I will then complete recurrence and exceptions, VTIMEZONE/TZID and all-day DATE handling, attendees and scheduling, alarms and reminders, search, import/export, Calendar-to-Tasks creation and rescheduling, canonical Calendar artwork, and the full production-readiness evidence stack.
Superseding Native-Build and Platform Integration Mandate
This specification is governed by the platform-wide requirement that this application be built natively from the ground up as original GoreeCloud-owned software. Earlier maintained-fork or upstream-product implementation language is transitional only. Narrow critical foundations may be retained only when independently replacing them would materially increase security, cryptographic, protocol, standards, codec, rendering, operating-system, runtime, or interoperability risk; WireGuard and mature cryptographic or encryption primitives are canonical examples. Such exceptions must remain limited to the minimum technical foundation and must not preserve upstream product architecture, UI, branding, workflows, or general application logic.
This application must remain current with the latest applicable Stable Glaze UI contract and the latest approved Wardveil Security, Privacy Shield, and Everkeep contracts. All four are mandatory. Missing, incomplete, superseded, outdated, unverified, or unaccepted integration with any required platform system blocks Stable qualification.
Current Development Reconciliation — September 9, 2026
This section supersedes older current-state wording in this specification where it conflicts with verified live project authority; historical implementation evidence above remains preserved. The current official shared design-system target is GLAZE UI V1.3 / `1.3.0` — Adaptive Resonance, as identified by the live GoreeCloud Glaze UI release and lifecycle registry. Earlier passages naming Glaze UI 1.5.0 as the current Stable target are stale current-state wording and must not govern new Calendar work. Calendar still requires a deliberate application-specific migration and fresh rendered, accessibility, adaptive, representative-environment, rollback, release, and production acceptance before current Glaze conformance may be claimed.
The active stacked Tasks-integration Development line is materially ahead of the PR #10 current-state summary above. Draft PR #17 (`agent/tasks-busy-api-v1`) exact head `c7e40faa1357cd6befe4c6afc2c564fa06f86724` provides the Calendar-side least-privilege read-only busy-time provider for GoreeCloud Tasks. Calendar fixes the authorized subject and calendar collection scope server-side, exposes only merged busy intervals, accepts only bounded timezone-aware query windows, and does not expose event titles, descriptions, locations, UIDs, calendar identifiers, or reusable credentials. Radicale/CalDAV remains authoritative for calendar data and Tasks remains authoritative for task data.
Stacked Draft PR #18 (`security/tasks-busy-token-file-hardening`) exact head `71858d641279b1dbbfc3d3c3253365260333415f` hardens the transitional file-backed Tasks bearer credential boundary. The loader rejects symbolic links, validates the opened file descriptor rather than trusting path metadata after open, retains regular-file and owner-only permission requirements, bounds the credential file to 4096 bytes with a bounded read, and rejects invalid UTF-8. This does not establish production GoreeCloud Identity/service delegation or an approved production secret backend.
Exact-head validation for PR #18 succeeded in Calendar CI run `34326206463` and Tasks Candidate Integration run `34326206344`. The parent PR #17 head had already passed its Calendar CI and Tasks Candidate Integration gates before PR #18 was stacked on it. Production service identity/delegation, approved secret lifecycle/rotation, distributed rate limiting, target-runtime TLS/reverse-proxy acceptance, real Radicale acceptance, recurrence/exceptions, VTIMEZONE/TZID and all-day DATE support, attendees/scheduling, alarms/reminders, search, import/export, complete Calendar-to-Tasks workflow acceptance, all seven Integral Platform System acceptance, signing/provenance, Release Candidate qualification, production approval, and Stable qualification remain open.
Platform Contract v0.2 Development Adoption
Calendar now has a stacked Development candidate for the mandatory GoreeCloud Platform Contract v0.2. Draft PR #20, exact head 38bf42460c019585f3872ed76713c810cb56c205, adds the root goreecloud.platform.yaml declaration and the reusable exact-revision Platform Contract validation workflow.
The candidate deliberately records Calendar as development, development-unversioned, and globally nonconformant because the repository has not yet established an authoritative application release version. The existing repository-local Glaze UI 1.3 source is declared as version 1.3.0 but remains applicable-migration-required pending whole-application rendered, accessibility, responsive, representative-browser/device, rollback, release, and production acceptance. GoreeCloud Manager, Privacy Shield, Wardveil Security, Everkeep, GoreeCloud Mesh, and GoreeCloud Identity remain blocked pending accepted integration and runtime evidence.
Exact-head validation for this candidate passed Platform Contract run 34540390058, Calendar CI run 34540389541, and Tasks Candidate Integration run 34540389482. These results validate the Development candidate only and do not establish Release Candidate, production, or Stable qualification.
Feature Roadmap Control Development Adoption — September 10, 2026
Draft PR #21 (`governance/calendar-feature-roadmap-control`) is stacked directly on exact-green Draft PR #20 and repairs the repository-side roadmap control required by the existing canonical Drive roadmap. Exact PR #21 head `760841fbc0de832cab6bb51eae7041007ef5913e` passed Platform Contract run `34544473668`, Calendar CI run `34544473334`, and Tasks Candidate Integration run `34544473296`.
The synchronized roadmap now records current obligations for Radicale/CalDAV source authority, standards-based event semantics, Calendar and GoreeCloud Tasks peer APIs, least-privilege busy-time projection, production Identity/service delegation and secret lifecycle, Wardveil Security, Privacy Shield, Everkeep, GLAZE UI V1.3 application acceptance, Manager/Mesh integration, Calendar user workflows, Calendar-to-Tasks UX, branding, target-runtime validation, signing/provenance, deployment/rollback, and release qualification. These roadmap states are planning and Development controls only; they do not create runtime authority or lifecycle acceptance.
The canonical `GoreeCloud/Feature Roadmap/GoreeCloud Calendar/FEATURE-ROADMAP.docx` was updated in place under its existing Drive file ID and governed Calendar roadmap folder. The final document was rendered and visually inspected across all three pages, re-fetched from Drive after replacement, and verified byte-for-byte at SHA-256 `9734c2f3bd16cabe7c004b5a155738fa310cb98e9f9c7d1cb250fac63afece51`.
Calendar remains Development / `development-unversioned` / overall `nonconformant`. Radicale remains authoritative for governed calendar data and GoreeCloud Tasks remains authoritative for task data and authorization. GLAZE UI V1.3 remains `applicable-migration-required`; Manager, Privacy Shield, Wardveil Security, Everkeep, Mesh, and Identity runtime/application acceptance remain blocked. Production service identity and secret lifecycle, target-runtime Radicale/TLS/reverse-proxy acceptance, complete Calendar event semantics and Tasks UX, representative accessibility/browser/device validation, signing, deployment, Release Candidate, production, and Stable gates remain open.

---

## Ongoing record maintenance

Update this record for significant architecture, governance, repository, security/privacy, authoritative-data, integration, production/recovery, lifecycle, migration, split/merge/rename, deprecation, or retirement events. Routine implementation chronology belongs in the repository changelog once that mandatory record exists.
