# GoreeCloud Calendar — Security status

## Preview warning

This service is not a hardened internet-facing application. Do not expose the Python ThreadingHTTPServer to public or untrusted networks, or rely on it as the sole copy of important data.

## Implemented source controls

- Local account provisioning; no open self-registration.
- Salted scrypt password hashing; random session tokens stored hashed and revoked on logout. Process-local login throttling limits repeated incorrect credentials.
- Calendar owner/edit/read/freebusy membership authorization for events, tasks, search and ICS import/export. Freebusy requests are projected to non-identifying occupied intervals; tasks, search results, event details and ICS export are withheld.
- Sharing available only to locally provisioned accounts; revocation requires calendar ownership.
- Parameterized SQL, bounded JSON, validated timestamps, ICS size/event limits and explicit rejection of complex unsupported recurrence.
- Default localhost binding; example container configuration uses a host loopback port.
- Security response headers, restrictive Content Security Policy and no external browser JavaScript.
- No mandatory telemetry or calendar provider.
- Manual no-overwrite SQLite snapshots, structural integrity checks and separate backup verification.

## Important missing controls

- No production TLS listener or hardened HTTPS reverse proxy.
- Only basic process-local, per-client-IP login throttling exists (10 attempts per five minutes); there is no shared/distributed abuse defense, MFA, password recovery, production GoreeCloud Identity integration or device control.
- Sharing is **not end-to-end encrypted**. Free/busy-only is an application-level server redaction policy, not cryptographic confidentiality; federation and cross-instance policy enforcement do not exist.
- SQLite event text and backup snapshots are **not encrypted at rest**.
- No automatic encrypted offsite backup, restore rehearsal or comprehensive disaster recovery.
- Session tokens held in web sessionStorage remain vulnerable to XSS or malicious extensions.
- No production threat-model review, attack simulation, security audit, signed release, deployment acceptance, or independent Android/Linux device security validation.
- No complete GoreeShield policy engine or Wardveil service integration. Opt-in browser alerts reveal event details to the local OS only while the tab is open; there is no background push service.

## Before remote deployment

Perform appropriate GoreeShield privacy and Wardveil security reviews. Establish HTTPS ingress, firewall boundaries, abuse protection, encryption/storage controls, backups with restore verification, monitoring, dependency provenance and signed release practices. Test access revocation under concurrent clients. Do not publish private events or credentials in issues or logs.
