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

The existing five-second socket timeout is per operation. Introduce explicit
whole-request and whole-run budgets. Accept when slow-header and slow-body
fixtures terminate within the documented budget with truthful error evidence.

The source-matrix coverage feature is already implemented locally. Do not create
an open implementation issue for completed work. ROADMAP.md lists later tasks.
