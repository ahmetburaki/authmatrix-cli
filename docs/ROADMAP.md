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

## M1 — Stronger assertions (merged; milestone closed)

1. **[Issue #1: Add bounded JSON field assertions](https://github.com/ahmetburaki/authmatrix-cli/issues/1)** (`feat: assert selected JSON fields`)
   - Opt-in allowlisted assertions without storing field values.
   - Merged into `main`: same-status leak detection,
     bounded JSON reading, minimized assertion evidence and compatibility tests.
   - Local and Python 3.11–3.14 hosted acceptance passed; [PR #4](https://github.com/ahmetburaki/authmatrix-cli/pull/4)
     merged on October 31. See [JSON assertions](JSON_ASSERTIONS.md) and [validation](JSON_VALIDATION.md).
2. **[Issue #2: Define tenant and role coverage](https://github.com/ahmetburaki/authmatrix-cli/issues/2)** (`test: cover tenant and role isolation`)
   - Merged into `main`: two-tenant/two-role loopback
     fixture and 21 explicit cases, with same-resource positive controls for every denial.
   - Independent fault modes verify exact failing IDs; partial fixes cannot claim complete proof.
   - Local and Python 3.11–3.14 hosted validation passed; [PR #5](https://github.com/ahmetburaki/authmatrix-cli/pull/5)
     merged on October 31. See [guide](TENANT_ROLES.md) and [validation](TENANT_VALIDATION.md).
3. **Implemented: Validate evidence against its source matrix** (`feat: verify evidence coverage`)
   - Required `--matrix` added to offline comparison with complete matching coverage.
   - Verified: missing/renamed cases, altered actors/expectations and changed source matrices are rejected.
   - This does not replace future signing or establish independent trust.

## M2 — Operational hardening

4. **[Issue #3: Enforce wall-clock run and request deadlines](https://github.com/ahmetburaki/authmatrix-cli/issues/3)** (`feat: bound total execution time`)
   - Merged into `main`: shared monotonic request/run budgets,
     deadline-aware TCP/TLS/header/body/framing reads and truthful partial evidence.
   - All 53 tests passed locally and in Ubuntu/Windows CI on Python 3.11–3.14.
     [PR #6](https://github.com/ahmetburaki/authmatrix-cli/pull/6) merged on October 31;
     see [acceptance](DEADLINE_VALIDATION.md).
   - See [deadline contract](DEADLINES.md).
5. **Implemented: Pinned hostname staging support** (`feat: pin validated staging addresses`)
   - Merged into `main`: version-2 HTTPS hostname
     origins with explicit private/loopback pins, preserved SNI/Host and optional CA files.
   - DNS is never consulted. Validation, TLS identity, proxy/redirect, deadline,
     evidence privacy, comparison and legacy compatibility tests cover the boundary.
   - All 79 tests passed locally and on Ubuntu/Windows Python 3.11–3.14;
     cleaned-history CI and GitGuardian checks passed. Real IPv6 TLS was verified
     in every hosted platform/version. [PR #9](https://github.com/ahmetburaki/authmatrix-cli/pull/9)
     merged on November 3; see [contract](HOSTNAMES.md) and
     [acceptance](HOSTNAME_VALIDATION.md).
6. **Implemented: Publish machine-readable contracts** (`feat: export bundled JSON schemas`)
   - Merged into `main`: self-contained matrix/evidence
     JSON Schemas, offline exports and fixed legacy/current compatibility fixtures.
   - All 63 tests passed locally and in Ubuntu/Windows CI on Python 3.11–3.14;
     base-package exports work without the optional test validator.
     [PR #7](https://github.com/ahmetburaki/authmatrix-cli/pull/7) merged on October 31.
   - See [contracts](SCHEMAS.md) and [acceptance](SCHEMA_VALIDATION.md).
7. **Implemented candidate preparation: First tagged release** (`chore: prepare release artifacts`)
   - MIT selected; version metadata has one source, with README, license, changelog
     and a reproducible source archive containing the examples and test corpus.
   - Archive inspection, sdist rebuild, isolated dependency-free install, legacy
     comparison and source-archive test checks passed locally. Hosted checks and
     candidate review are pending on `chore/first-release-preparation`.
   - See [release procedure](RELEASING.md) and [acceptance](RELEASE_VALIDATION.md).
     Final changelog date, approved tag and publication remain separate steps.

## Current main and GitHub cadence

PRs #4–#9 are integrated. All 79 tests passed locally and across the eight
Ubuntu/Windows Python 3.11–3.14 jobs on the merged main revision. See
[integration acceptance](INTEGRATION.md) and the [CI contract](CI.md).

Each issue should become one focused branch/PR with a failing reproduction,
implementation, relevant tests and a short explanation of behavior and limits.
Use real completed work as the activity record. Keep credential files and local
run evidence out of commits. Use `ahmetburaki/authmatrix-cli` as the origin. Review hosted CI results for each
commit before building on it. MIT is selected. Release tags still require current
packaging checks, finalized changelog and an approved source revision.
