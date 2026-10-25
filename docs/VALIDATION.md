# Local acceptance — 2026-10-25

## Verified

- Python 3.14.7: 12 unittest integration/CLI tests passed.
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

## Pending / limitations

- Hosted GitHub CI and Python 3.11–3.13 runs are configured but not executed here.
- Verification uses only the synthetic loopback API; no external APIs were contacted.
- Exact HTTP status expectations do not detect data leaks hidden in 200 responses.
- No signed evidence, endpoint discovery, mutations or whole-run deadline yet.
- Remote repository, public issues/milestones and release license remain unselected.

See ROADMAP.md for issue drafts and acceptance criteria. This is a tested local
MVP, not a published release or a claim of comprehensive API security coverage.
