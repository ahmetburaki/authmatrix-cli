# Milestones and commit-sized backlog

Local issue drafts for a future GitHub repository. No remote issues or milestones
have been created. Build useful, reviewable changes; never manufacture activity.
No marketing, sales, revenue or outreach tasks are in this plan.

## M0 — Reproducible authorization CLI (implemented)

- [x] Strict matrix validation and explicit local/private staging target scope.
- [x] Actor environment tokens, anonymous cases, read-only request methods.
- [x] Minimized JSON evidence, exact before/after comparison and exit codes.
- [x] Synthetic vulnerable/fixed API, integration tests, docs and CI workflow.

Acceptance: local test suite passes; cross-owner failure becomes a verified
fail→pass while owner and anonymous controls stay passing. CI is configured;
GitHub execution is pending publication. No real staging API has been tested.

## M1 — Stronger assertions

1. **Issue: Add bounded JSON field assertions** (`feat: assert selected JSON fields`)
   - Opt-in allowlisted assertions without storing field values.
   - Accept when same-status data leaks are caught, large bodies are bounded,
     and sensitive values cannot reach evidence or errors.
2. **Issue: Define tenant and role coverage** (`test: cover tenant and role isolation`)
   - Extend synthetic API with two tenants and two roles; explicit matrix cases.
   - Accept when each negative has an appropriate positive control and a failing fixture.
3. **Issue: Validate evidence against its source matrix** (`feat: verify evidence coverage`)
   - Add matrix input to offline comparison and require complete matching coverage.
   - Accept when fabricated missing/renamed cases and altered expectations are rejected.
   - This does not replace future signing or establish independent trust.

## M2 — Operational hardening

4. **Issue: Enforce wall-clock run and request deadlines** (`feat: bound total execution time`)
   - Accept when slow-header fixtures terminate within the documented budget.
5. **Issue: Design hostname staging support** (`feat: pin validated staging addresses`)
   - Define explicit host allowlist, IP pinning, TLS identity and custom CA handling.
   - Accept when rebinding, redirect, proxy and metadata tests remain denied.
6. **Issue: Publish machine-readable contracts** (`docs: specify matrix and evidence schemas`)
   - Add JSON Schemas and compatibility fixtures; no runtime dependency required.
7. **Issue: Prepare first tagged release** (`chore: prepare release artifacts`)
   - Select license, verify packaging and installed CLI on clean supported Python
     versions; review evidence and document changelog. Publish only after CI passes.

## GitHub cadence

Each issue should become one focused branch/PR with a failing reproduction,
implementation, relevant tests and a short explanation of behavior and limits.
Use real completed work as the activity record. Keep credential files and local
run evidence out of commits. Select a remote repository before pushing; the current
starter is local. Keep release tags pending the M0 checks on hosted CI and license decision.
