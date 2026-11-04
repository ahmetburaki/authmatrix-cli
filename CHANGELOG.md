# Changelog

## 0.1.0 — 2026-11-04

### Added

- Read-only authorization matrices with explicit actors and expected statuses.
- Opt-in bounded JSON presence/absence and type-strict scalar assertions.
- Tenant, role, ownership and anonymous controls in synthetic local fixtures.
- Absolute request/run deadlines, partial evidence and explicit not-run outcomes.
- Matrix-v2 staging hostnames pinned to private/loopback IPs without DNS lookup;
  verified TLS identity and an optional PEM CA file.
- Minimized schema-3 evidence with legacy v1/v2 comparison compatibility and full
  source-matrix coverage checks.
- Offline bundled JSON Schema exports, version reporting and MIT licensing.
- Wheel/source-archive validation and isolated installed-CLI checks in CI.

### Scope

Python 3.11–3.14; local and authorized private staging APIs; GET/HEAD only. Evidence
is unsigned regression data and covers declared cases. Production, endpoint
discovery, mutation methods, redirects/proxies and TLS bypasses are outside scope.
Deadlines bound network execution; local work and scheduling are not preempted.
