# Main integration acceptance — 2026-10-31

PRs #4–#7 were merged in order, preserving the original feature commits. Each
dependent PR was retargeted to main after its predecessor merged, and its head
and passing checks were rechecked before merging. No force push or check bypass
was used. After each merge, main's file tree matched the corresponding validated
feature head exactly.

| PR | Feature | Merge commit |
| --- | --- | --- |
| [#4](https://github.com/ahmetburaki/authmatrix-cli/pull/4) | Bounded JSON assertions | `6d7d55e92ff58519ee24b4f9f0075c87777fd21e` |
| [#5](https://github.com/ahmetburaki/authmatrix-cli/pull/5) | Tenant/role coverage | `0d619ca4737caedfaa669c38aa42ef8433d46a1c` |
| [#6](https://github.com/ahmetburaki/authmatrix-cli/pull/6) | Request/run deadlines | `c8d028e226b07825ce66b698d873bc56e763995c` |
| [#7](https://github.com/ahmetburaki/authmatrix-cli/pull/7) | Bundled schema contracts | `9953a88983663cd51d5e85af42b53b4ea271c4ea` |

## Verified combined state

- Main revision `9953a88983663cd51d5e85af42b53b4ea271c4ea` has the same file tree
  as validated schema-feature head `7b691e1d9a1793b11ea920b44ea4c266f57d2d62`.
- `python -m unittest discover -s tests -q` passed all 63 tests locally on Python
  3.14.7 after updating the local main branch.
- [Main CI run 41237100106](https://github.com/ahmetburaki/authmatrix-cli/actions/runs/41237100106)
  passed all eight Ubuntu/Windows Python 3.11–3.14 jobs. Each job checked the base
  installation before test extras, ran all 63 tests and validated all three matrices.
- Issues #1–#3 closed through their merged PRs. M1 is closed; M2 remains open.

Historical feature reports retain their original test counts and run references.
This record covers their combined main state. Runtime authorization, TLS, target
scope, evidence minimization, legacy-report comparison and deadlines remain as
implemented and tested. No production/external API was tested and no release tag
or distribution license was created.
