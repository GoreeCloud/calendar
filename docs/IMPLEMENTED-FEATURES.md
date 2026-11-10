# GoreeCloud Calendar — Implemented Features

Status: Repository development branch; source-implemented features awaiting independent CI/run verification.

## Backend

- Python 3.11+ standard-library HTTP service and SQLite schema.
- Locally provisioned accounts and salted scrypt password storage.
- Bearer login/logout, hashed expiring sessions, per-user ownership checks.
- Calendar CRUD with names, colors and descriptions.
- Timed event CRUD with ISO 8601 validation, UTC storage and optimistic version update checks.
- Task create/list/update/delete with optional due dates.
- Read-only ICS export for an owned calendar.
- Loopback binding default, input size checks and browser security headers.

## Browser

- Sign-in and sign-out.
- Responsive month, week, agenda, task navigation.
- Calendar visibility filters and new-calendar interface.
- Event create/edit/delete dialogs, task create/complete/delete.
- Current date navigation, event colors and selected calendar export.
- Mobile floating navigation dock; system light/dark presentation.

## Build/deployment scaffolding

- Dockerfile, compose.yaml and Python HTTP regression test suite.
- GitHub Actions workflow for Python and JS checks.

**Limitations:** This document reports source presence only. Installed and deployed runtime tests, complete visual acceptance, production security and recovery acceptance remain unverified. Android and Linux client deliverables are not implemented in this initial web/backend checkpoint.
