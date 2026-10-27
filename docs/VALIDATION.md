# Local acceptance — 2026-10-25

Historical status-only acceptance. For the October 27 JSON assertion feature,
see [JSON acceptance](JSON_VALIDATION.md).

## Verified

- Python 3.14.7: 16 unittest integration/CLI tests passed.
- Built wheel and installed into an isolated Python 3.14 environment.
- Installed `authmatrix validate examples/matrix.json` exited 0.
- Installed CLI exercised against the provided synthetic loopback API:
  - Vulnerable baseline: owner passed, cross-owner failed, anonymous passed; exit 1.
  - Corrected API: all three cases passed; exit 0.
  - Offline comparison: `fixed=["cross-owner-denied"]`, no regressions,
    `proof_of_fix=true`; exit 0.
- Synthetic evidence saved privately under ignored `evidence/` with mode 0600.
- Tests cover output overwrite prevention, authorization confirmation, invalid
  targets/configuration, token injection/missing credentials, transport errors,
  redirect handling, evidence minimization and inconsistent comparisons.
- Source-matrix checks reject identical omissions from both reports, renamed cases,
  altered actors/expectations and a changed source matrix. Comparison runs offline
  without credentials. The installed CLI also verified the updated comparison flow.

## Hosted verification

[GitHub Actions run 40226220327](https://github.com/ahmetburaki/authmatrix-cli/actions/runs/40226220327)
passed all four jobs on Python 3.11, 3.12, 3.13 and 3.14 for commit
`2e6b358b4c655925b197e2cb5f20cf4f2bb6162e`. Each job installed the package,
ran all 16 tests and validated the example matrix using the installed CLI.

## Pending / limitations

- Verification uses only the synthetic loopback API; no external APIs were contacted.
- Exact HTTP status expectations do not detect data leaks hidden in 200 responses.
- No signed evidence, endpoint discovery, mutations or whole-run deadline yet.
- Repository `ahmetburaki/authmatrix-cli` created with two milestones and three issues.
  License remains unselected.

See ROADMAP.md for issue drafts and acceptance criteria. This is a tested local
MVP, not a published release or a claim of comprehensive API security coverage.
