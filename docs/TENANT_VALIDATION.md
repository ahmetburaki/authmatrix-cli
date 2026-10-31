# Tenant/role acceptance — 2026-10-27

## Local verification

- 37 unittest tests passed on Python 3.14.7, including all 30 existing tests.
- The explicit matrix has 21 cases: 9 positive, 10 authorization denial and
  2 anonymous denial cases. Every denial has a same-resource positive control.
- The installed CLI was exercised outside the source directory against the
  provided tenant fixture on an OS-selected IPv4 loopback port.

| Fixture mode | Pass | Fail | Error | CLI exit |
| --- | --- | --- | --- | --- |
| `none` | 21 | 0 | 0 | 0 |
| `ownership` | 19 | 2 | 0 | 1 |
| `tenant` | 15 | 6 | 0 | 1 |
| `role` | 19 | 2 | 0 | 1 |
| `all` | 11 | 10 | 0 | 1 |

The automated tests verify the exact failing case IDs for each fault. Positive
controls remain passing in every mode. Unknown, missing and incorrectly formatted
credentials remain denied even when all authorization faults are enabled.

Comparing `all` to `none` returned 10 fixed cases, no regressions and
`proof_of_fix=true`; exit 0. Comparing `all` to `ownership` returned 8 fixed cases
but `proof_of_fix=false` because two ownership violations remain; exit 1. Reverse
comparison identifies all 10 regressions. Evidence/console tests confirm that
tokens, endpoint paths and raw response fields are not retained.

## Hosted verification

[GitHub Actions run 40497841441](https://github.com/ahmetburaki/authmatrix-cli/actions/runs/40497841441)
passed all four Python 3.11–3.14 jobs for implementation/documentation commit
`5c9872891d71a4365d877592373350613da90308`. Each job installed the package, ran
all 37 tests and validated all three example matrices.
The change is proposed in [PR #5](https://github.com/ahmetburaki/authmatrix-cli/pull/5).

## Integration and limits

This change builds on the JSON assertion branch proposed in PR #4, which remains
open. Its own PR targets that branch so reviewers see only tenant/role changes.
It requires PR #4 to reach main first, followed by retargeting and verification.
No merge or release is implied by these acceptance results.

Only synthetic loopback endpoints were tested. The fixture models a declared
policy; it does not infer or exhaustively assess a real application's policy.
No authorization checks in the CLI were relaxed; runtime package code is unchanged.
