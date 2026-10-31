# Milestones and commit-sized backlog

Work is tracked in [GitHub issues](https://github.com/ahmetburaki/authmatrix-cli/issues)
and [milestones](https://github.com/ahmetburaki/authmatrix-cli/milestones). Build useful, reviewable changes; never manufacture activity.
No marketing, sales, revenue or outreach tasks are in this plan.

## M0 — Reproducible authorization CLI (implemented)

- [x] Strict matrix validation and explicit local/private staging target scope.
- [x] Actor environment tokens, anonymous cases, read-only request methods.
- [x] Minimized JSON evidence, exact before/after comparison and exit codes.
- [x] Synthetic vulnerable/fixed API, integration tests, docs and CI workflow.

Acceptance: local test suite passes; cross-owner failure becomes a verified
fail→pass while owner and anonymous controls stay passing. Hosted CI passed on
Python 3.11–3.14; see [validation](VALIDATION.md). No real staging API has been tested.

## M1 — Stronger assertions

1. **[Issue #1: Add bounded JSON field assertions](https://github.com/ahmetburaki/authmatrix-cli/issues/1)** (`feat: assert selected JSON fields`)
   - Opt-in allowlisted assertions without storing field values.
   - Implemented on `feat/bounded-json-assertions`: same-status leak detection,
     bounded JSON reading, minimized schema-2 evidence and compatibility tests.
   - Local and Python 3.11–3.14 hosted acceptance passed; [PR #4](https://github.com/ahmetburaki/authmatrix-cli/pull/4)
     is ready for review. See [JSON assertions](JSON_ASSERTIONS.md) and [validation](JSON_VALIDATION.md).
2. **[Issue #2: Define tenant and role coverage](https://github.com/ahmetburaki/authmatrix-cli/issues/2)** (`test: cover tenant and role isolation`)
   - Implemented on `test/tenant-role-isolation`: two-tenant/two-role loopback
     fixture and 21 explicit cases, with same-resource positive controls for every denial.
   - Independent fault modes verify exact failing IDs; partial fixes cannot claim complete proof.
   - Local and Python 3.11–3.14 hosted validation passed; [PR #5](https://github.com/ahmetburaki/authmatrix-cli/pull/5)
     is ready for review. See [guide](TENANT_ROLES.md) and [validation](TENANT_VALIDATION.md).
   - Built on PR #4 while its JSON assertion changes await merge.
3. **Implemented: Validate evidence against its source matrix** (`feat: verify evidence coverage`)
   - Required `--matrix` added to offline comparison with complete matching coverage.
   - Verified: missing/renamed cases, altered actors/expectations and changed source matrices are rejected.
   - This does not replace future signing or establish independent trust.

## M2 — Operational hardening

4. **[Issue #3: Enforce wall-clock run and request deadlines](https://github.com/ahmetburaki/authmatrix-cli/issues/3)** (`feat: bound total execution time`)
   - Implemented on `fix/request-run-deadlines`: shared monotonic request/run budgets,
     deadline-aware TCP/TLS/header/body/framing reads and truthful partial evidence.
   - All 53 tests passed locally and in Ubuntu/Windows CI on Python 3.11–3.14.
     [PR #6](https://github.com/ahmetburaki/authmatrix-cli/pull/6) is ready for review;
     see [acceptance](DEADLINE_VALIDATION.md).
   - Built on PR #5; see [deadline contract](DEADLINES.md).
5. **Issue: Design hostname staging support** (`feat: pin validated staging addresses`)
   - Define explicit host allowlist, IP pinning, TLS identity and custom CA handling.
   - Accept when rebinding, redirect, proxy and metadata tests remain denied.
6. **Implemented: Publish machine-readable contracts** (`feat: export bundled JSON schemas`)
   - Implemented on `feat/json-schema-contracts`: self-contained matrix/evidence
     JSON Schemas, offline exports and fixed legacy/current compatibility fixtures.
   - All 63 tests passed locally; base-package exports work without the optional
     test validator. Hosted validation and review are pending.
   - Built on PR #6; see [contracts](SCHEMAS.md) and [acceptance](SCHEMA_VALIDATION.md).
7. **Issue: Prepare first tagged release** (`chore: prepare release artifacts`)
   - Select license, verify packaging and installed CLI on clean supported Python
     versions; review evidence and document changelog. Publish only after CI passes.

## GitHub cadence

Each issue should become one focused branch/PR with a failing reproduction,
implementation, relevant tests and a short explanation of behavior and limits.
Use real completed work as the activity record. Keep credential files and local
run evidence out of commits. Use `ahmetburaki/authmatrix-cli` as the origin. Review hosted CI results for each
commit before building on it. Keep release tags pending the M0 checks on hosted CI and license decision.
