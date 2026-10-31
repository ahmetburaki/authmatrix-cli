# GitHub setup and first work items

Owner: `ahmetburaki`  
Planned repository: `authmatrix-cli`  
Local branch: `main`

Repository: https://github.com/ahmetburaki/authmatrix-cli

The public remote is created and the local origin is configured. GitHub CLI is
authenticated as `ahmetburaki`; commits use the account's GitHub noreply address.
Two milestones and three implementation issues track the first development work.
Use pull requests for subsequent features and review all supported Python CI jobs.
Choose a distribution license before tagging a release. Keep ignored evidence local.

## Milestone: M1 — Stronger assertions

### [Issue #1: Add bounded JSON field assertions](https://github.com/ahmetburaki/authmatrix-cli/issues/1)

Detect authorization failures where the HTTP status is expected but the response
contains fields that the actor must not receive. Use opt-in assertions, a response
size cap and synthetic fixtures. Keep response fields/values out of evidence.
Accept when a vulnerable fixture fails, the corrected fixture passes and oversized
or invalid JSON cannot produce a passing result.

### [Issue #2: Define tenant and role coverage](https://github.com/ahmetburaki/authmatrix-cli/issues/2)

Add a local fixture with two tenants and two roles. Declare explicit positive
and negative cases. Accept when owner/tenant/role controls distinguish a faulty
implementation from its corrected version.

## Milestone: M2 — Operational hardening

### [Issue #3: Enforce wall-clock request and run deadlines](https://github.com/ahmetburaki/authmatrix-cli/issues/3)

Implemented on `fix/request-run-deadlines`: explicit whole-request and run budgets,
slow-header/body/framing/TLS regressions and truthful partial evidence. See
[deadline contract](DEADLINES.md) and [acceptance](DEADLINE_VALIDATION.md).
[PR #6](https://github.com/ahmetburaki/authmatrix-cli/pull/6) targets PR #5's branch;
review and merge in order #4, #5, #6.

The source-matrix coverage feature is already implemented locally. Do not create
an open implementation issue for completed work. ROADMAP.md lists later tasks.

## M2 — Machine-readable contracts

Implemented on `feat/json-schema-contracts`: bundled matrix/evidence JSON Schemas,
offline CLI exports and fixed legacy/current compatibility fixtures. This branch
builds on PR #6. See [contracts](SCHEMAS.md) and [acceptance](SCHEMA_VALIDATION.md).
