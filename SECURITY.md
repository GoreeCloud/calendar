# GoreeCloud Calendar — Security

## Development-preview warning

Do not expose the Python HTTP listener directly to public or untrusted networks. Do not use this implementation as the only copy of valuable schedule data. This repository has not passed production security, recovery or release acceptance.

## Source controls present

- Default bind to loopback; sample Compose publishes host loopback only.
- Users must be created locally with the interactive administrative command.
- Passwords are stored as salted scrypt KDF results; bearer tokens stored as SHA-256 digests.
- API sessions expire after seven days and can be revoked.
- User ID restrictions are applied to calendar, event, task and ICS operations.
- Parameterized SQL queries, SQLite foreign keys and bounded JSON bodies.
- Events require explicit timezone-aware timestamps and consistent chronological order.
- Browser code uses textContent for dynamic event text, with restrictive Content Security Policy and no external script providers.
- No user event descriptions or authentication headers are intentionally logged by the application.

## Missing security controls

- No production ingress/TLS termination; HTTP is not safe for remote login.
- No cross-process authentication rate limiting or account lockout.
- No password reset, MFA or federated GoreeCloud Identity integration.
- No encrypted storage, end-to-end encryption, secure sharing, or external-provider consent system.
- No backup automation, integrity testing or restored-state validation.
- No comprehensive network threat model, security testing, dependency provenance/SBOM or signed releases.
- Python ThreadingHTTPServer is a development server, not a hardened internet-facing server.
- Tokens in browser sessionStorage remain susceptible to compromise if XSS or a malicious browser extension occurs.

## Recommendations before any remote deployment

Use an authenticated, reviewed HTTPS reverse proxy, nonprivileged service runtime, protected storage, firewall, ingress request limits, credential rotation, reliable backups and disaster-recovery tests. Complete Wardveil threat review and GoreeShield privacy review. Review session lifecycle, audit logging, brute-force resistance and trusted reverse-proxy handling. Validate each actual deployment, not only source-code tests.

Do not include secrets, event details, private database files or access tokens in public issues.

A manual `python -m calendar_app backup --output ...` snapshot command exists. Its output is an **unencrypted** SQLite file; safeguard it and verify recovery. Automated encrypted backup and restore acceptance are outstanding.
