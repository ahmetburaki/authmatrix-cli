# GitHub setup and first work items

Owner: `ahmetburaki`  
Planned repository: `authmatrix-cli`  
Local branch: `main`

The local origin is `https://github.com/ahmetburaki/authmatrix-cli.git`.
That setting does not create or publish a remote repository. No authenticated
GitHub connection was available during setup, so remote creation, pushing,
hosted CI and public issues/milestones remain pending.

Create a new empty public repository under this account when authenticated.
Keep remote initialization disabled because the local history already includes
README and .gitignore. Push main and verify all four Python CI jobs. Choose a
distribution license before tagging a release. Do not publish ignored evidence.

## Milestone: M1 — Stronger assertions

### Issue: Add bounded JSON field assertions

Detect authorization failures where the HTTP status is expected but the response
contains fields that the actor must not receive. Use opt-in assertions, a response
size cap and synthetic fixtures. Keep response fields/values out of evidence.
Accept when a vulnerable fixture fails, the corrected fixture passes and oversized
or invalid JSON cannot produce a passing result.

### Issue: Define tenant and role coverage

Add a local fixture with two tenants and two roles. Declare explicit positive
and negative cases. Accept when owner/tenant/role controls distinguish a faulty
implementation from its corrected version.

## Milestone: M2 — Operational hardening

### Issue: Enforce wall-clock request and run deadlines

The existing five-second socket timeout is per operation. Introduce explicit
whole-request and whole-run budgets. Accept when slow-header and slow-body
fixtures terminate within the documented budget with truthful error evidence.

The source-matrix coverage feature is already implemented locally. Do not create
an open implementation issue for completed work. ROADMAP.md lists later tasks.
