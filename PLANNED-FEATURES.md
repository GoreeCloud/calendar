# GoreeCloud Calendar — Planned Features

> **Authority:** Repository-native planned-feature record. This file preserves the richer former Drive roadmap states and obligations; the Drive copy is retired after verified migration.
> **Boundary:** Partial Development foundations remain partial and do not imply production, release, or Stable acceptance.

Active roadmap control • As of September 10, 2026
Purpose
This document is the Drive-side feature roadmap control for GoreeCloud Calendar. It records current planned and recommended feature work without replacing the authoritative project record, repository implementation evidence, release gates, or GoreeCloud Tasks Management.
Current Development checkpoint: Draft PR #20 (governance/calendar-platform-contract-v0.2) exact head 38bf42460c019585f3872ed76713c810cb56c205 passed Platform Contract 34540390058, Calendar CI 34540389541, and Tasks Candidate Integration 34540389482. It adopts Platform Contract v0.2 while keeping Calendar lifecycle development, version development-unversioned, and overall conformance nonconformant. Radicale/CalDAV remains authoritative for calendar data. The current repository-local GLAZE UI V1.3 / 1.3.0 source remains applicable-migration-required; Manager, Privacy Shield, Wardveil Security, Everkeep, Mesh, and Identity remain blocked pending accepted runtime/application evidence.
Roadmap
Recommended sequencing
Keep current PR #20 Platform Contract and Tasks-boundary work as Development evidence only.
Finish production Identity/service-delegation and secret lifecycle decisions before broadening peer APIs or deployment authority.
Complete the remaining Calendar event semantics and Calendar and Tasks UI workflows without weakening source ownership or offline/failure isolation.
Finish the GLAZE UI V1.3 application migration and representative accessibility/browser/device acceptance.
Complete Everkeep, Privacy Shield, Wardveil Security, Manager/Mesh, target-runtime, signing/provenance, deployment/rollback, and explicit release gates before Release Candidate or Stable claims.
Repository-native maintenance
Google Drive roadmap synchronization is retired. Maintain this record from authoritative repository/project evidence and applicable task records.
Reconciliation rule
At each material feature change, reconcile this roadmap against the current authoritative project record, repository implementation state, applicable platform-system requirements, and GoreeCloud Tasks Management. Missing obligations, stale status, duplicated work, roadmap drift, or undocumented disposition changes are defects to correct.
Application / Service
GoreeCloud Calendar
Authoritative project record
Project Specification — Calendar
Canonical repository
GoreeCloud/goreecloud-calendar
Repository control
FEATURE-ROADMAP.md
Drive location
GoreeCloud/Feature Roadmap/GoreeCloud Calendar/FEATURE-ROADMAP.docx
ID
Feature / obligation
Priority
Current state
FR-001
Reconcile and maintain every current planned or recommended GoreeCloud Calendar feature from the authoritative project record and verified repository evidence in this roadmap.
High
Ongoing control
FR-002
Move actionable feature obligations into GoreeCloud Tasks Management when required, preserving priority, dependency, and lifecycle disposition.
High
Ongoing control
FR-003
Do not mark features implemented, complete, cancelled, or superseded without authoritative evidence and authoritative repository feature-record updates.
High
Ongoing control
FR-010
Preserve Radicale/CalDAV as the authoritative governed calendar store while Calendar remains the first-party application/presentation layer; caches, indexes, availability projections, and integration state must remain rebuildable/non-authoritative unless separately approved.
High
Active architectural control
FR-011
Complete standards-based event behavior: timezone-aware timed/all-day events, recurrence/exceptions, VTIMEZONE/TZID, attendees/scheduling, alarms/reminders, search, import/export, ETag conflict handling, and calendar membership/sharing.
High
Partial Development foundation; broader event semantics remain planned
FR-012
Complete Calendar and GoreeCloud Tasks peer integration through explicit APIs without direct cross-database access or authority transfer.
High
Development API candidates present; complete UI/runtime/integration acceptance pending
FR-013
Maintain least-privilege Tasks busy-time provider behavior: fixed server-side subject/collection scope, bounded timezone-aware windows, merged busy intervals only, no event-content disclosure, and safe peer failure behavior.
High
Development provider/hardening candidates validated; production Identity/service delegation and deployment acceptance pending
FR-014
Replace or formally accept transitional service/session and credential mechanisms behind existing contracts using production GoreeCloud Identity and an approved secret lifecycle/backend; preserve low-detail failures and explicit revocation/rotation.
High
Planned / blocked on production authority
FR-015
Complete runtime security hardening including production-grade shared rate limiting where required, TLS/reverse-proxy binding, target-environment session/credential validation, and Wardveil Security acceptance.
High
Development boundaries exist; production acceptance pending
FR-016
Complete Privacy Shield integration for Calendar data flows, Tasks projections, sharing, availability, logging/minimization, and user-facing privacy controls with accepted runtime evidence.
High
Planned — platform acceptance pending
FR-017
Complete Everkeep backup, restoration, portability, upgrade/rollback, and recovery evidence for authoritative and application-specific Calendar state.
High
Planned — recovery acceptance pending
FR-018
Complete GLAZE UI V1.3 / 1.3.0 application migration and source, rendered, accessibility, adaptive, representative browser/device, and rollback acceptance, including keyboard, visible focus, reduced motion/transparency, forced-colors, touch targets, and appearance modes.
High
applicable-migration-required; whole-application acceptance pending
FR-019
Complete applicable GoreeCloud Manager and GoreeCloud Mesh integration with explicit capability/operational boundaries and accepted evidence.
Medium
Planned — platform acceptance pending
FR-020
Complete Calendar user workflows for day/week/month/agenda/schedule views, event create/edit/delete, availability/conflict visibility, responsive behavior, offline-tolerant behavior where justified, and accessible error/loading states.
High
Partial Development foundation; complete product/runtime acceptance pending
FR-021
Complete Calendar-to-Tasks creation/rescheduling UX only through Tasks-owned authorization and revision/conflict semantics; Calendar must remain usable when Tasks is unavailable.
High
API client candidate exists; UI/end-to-end acceptance pending
FR-022
Complete canonical Calendar artwork/branding derivatives and current Glaze-aligned visual acceptance without using branding as evidence of security/privacy state.
Medium
Planned / incomplete
FR-023
Complete exact-revision production-readiness evidence: real Radicale behavior, private DNS/TLS/firewall boundaries, monitoring/alerting, backup/restore, accessibility, responsive visual review, platform-system acceptance, signing/provenance, deployment/rollback, Release Candidate, and Stable qualification.
High
Open release gate
