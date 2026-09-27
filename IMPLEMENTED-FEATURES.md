# GoreeCloud Calendar — Implemented Features

> **Authority:** Repository-native implemented-feature record.  
> **Boundary:** The items below are verified **source foundations**, not production acceptance or Stable claims.

## Verified Development source foundations

The repository now includes:

- timezone-safe calendar event domain primitives and busy-interval merging;
- deterministic month, week, day, and agenda view-window projections;
- versioned first-party event-view and privacy-minimized busy-time API contracts;
- a fail-closed CalDAV transport foundation with HTTPS-only configuration, cross-origin refusal, authenticated discovery, bounded calendar-query reads, ETag-protected writes/deletes, and iCalendar serialization;
- a Glaze UI 1.3 application shell with responsive view switching, date navigation, event rendering, event-creation workflow, keyboard focus treatment, reduced-motion/transparency handling, and forced-colors support;
- the strict GoreeCloud Tasks projection consumer and bidirectional Tasks integration contract;
- dependency-free unit/contract tests suitable for CI.

This is a source foundation, not production acceptance. Production publication, production DAV credentials, user migration, monitoring, backup/recovery evidence, and live target-environment validation remain separate controlled work.

