# GoreeCloud Calendar — Planned Features

Document status: Product requirements. This is not implementation evidence.

## Target platforms

1. Self-hostable server and database with backups, health monitoring, access control and a private local-only mode.
2. Responsive browser web app with calendar editing, accessibility and local-first caching.
3. Installable Linux app with desktop notifications, local encrypted cache, offline editing and secure sync.
4. Installable Android app with notifications, widgets, native authentication, offline edits and secure sync.

## Calendar and event features

- Personal, household, family, work, school, project, group, organization, holiday, birthday and public calendars.
- Create, rename, recolor, reorder, archive, restore and delete calendars.
- Side-by-side and combined calendars; day, week, month, year, agenda, schedule and timeline views.
- Event titles, notes, descriptions, location, URL, attachment links, labels, status, organizers and participants.
- Timezone-aware start/end, all-day, multi-day, recurring and exception events.
- Recurrence by days, selected weekdays, months, nth weekdays and years with series or single occurrence updates.
- Event search, date filters, category filters and safe change-history capabilities.

## Sharing, meeting coordination and appointments

- Calendar ownership, read, read/write and free/busy-only permissions; revocation and invitations.
- Collaborative editing, controlled membership, delegates, shared activity and cross-user conflict detection.
- Meeting invitations, RSVP states, attendance, scheduling polls, available time recommendations and resources.
- Self-service appointment booking pages, staff availability, custom forms, limits, confirmations and rescheduling.
- Optional billing, SMS and video conferencing adapters.

## Tasks, collaboration and communication

- Task lists, subtasks, recurrence, due dates, priorities, completion, focus time and assignments.
- Event notes, memos, checklists, comments, reactions, meeting agendas and document attachments.
- Calendar-specific reminders, email and push notifications and locally scheduled alerts.
- No photo albums and no event photo-gallery feature.

## Import, synchronization and integration

- Import/export ICS, CalDAV interoperability, subscriptions and pluggable provider connectors.
- Optional Google Calendar, Outlook/Microsoft 365 and Nextcloud adapters when authorized by each provider.
- GoreeCloud Mesh coordination, Tasks, Contacts, Mail, and optional automation API integration.
- Reliable offline data capture, queued mutations, sync state, conflict handling and idempotency.
- Authorized webhooks and developer APIs.

## Privacy, security and intelligent features

- GoreeCloud Identity authentication/authorization, GoreeShield privacy, Wardveil security.
- Explicit consent, retention controls, local data ownership, secure storage and appropriate encryption boundaries.
- Optional local AI scheduling, meeting preparation, conflict suggestions and privacy-preserving time insights.
- GC UI design language, floating mobile navigation, light/dark/high-contrast interfaces and native-platform patterns.

## Release policy

A feature is implemented only after source, tests and its platform behavior justify that classification. Android APK and Linux installer must be built and tested independently. Self-hosted demo operation does not constitute production readiness.
