# Repository status and work tracking

Repository: [ahmetburaki/authmatrix-cli](https://github.com/ahmetburaki/authmatrix-cli)
Default branch: `main`.

PRs #4–#7 were merged into main in dependency order on October 31, 2026. The
combined tree passed all 63 tests locally and all eight Ubuntu/Windows Python
3.11–3.14 jobs. See [integration acceptance](INTEGRATION.md).

| Work | Integrated PR | Tracking status |
| --- | --- | --- |
| Bounded JSON assertions | [#4](https://github.com/ahmetburaki/authmatrix-cli/pull/4) | [Issue #1](https://github.com/ahmetburaki/authmatrix-cli/issues/1) closed |
| Tenant, role and ownership coverage | [#5](https://github.com/ahmetburaki/authmatrix-cli/pull/5) | [Issue #2](https://github.com/ahmetburaki/authmatrix-cli/issues/2) closed |
| Request/run deadlines | [#6](https://github.com/ahmetburaki/authmatrix-cli/pull/6) | [Issue #3](https://github.com/ahmetburaki/authmatrix-cli/issues/3) closed |
| Offline JSON Schema contracts | [#7](https://github.com/ahmetburaki/authmatrix-cli/pull/7) | Implemented on main |

M1 is complete and closed. M2 remains open for the remaining operational work,
including hostname staging design and first-release preparation. See the
[roadmap](ROADMAP.md) for acceptance criteria and commit-sized tasks.

Create focused PRs against main and inspect every supported CI job. Keep private
credentials and real-system evidence out of commits. Do not open implementation
issues for work already completed. Choose a distribution license and complete
release checks before tagging a release. No release was published by integration.
