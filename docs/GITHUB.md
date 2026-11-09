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

PR #8 integrated CI/documentation maintenance on November 1. PR #9 integrated
pinned hostname staging support on November 3; all 79 tests passed in main CI.
M1 and M2 are complete and closed.

Create focused PRs against main and inspect every supported CI job. Keep private
credentials and real-system evidence out of commits. Do not open implementation
issues for work already completed. Complete release checks before tagging a
release.

PRs #10–#12 integrated MIT licensing, package checks, portable checksum manifests
and final release notes. The first release,
[v0.1.0](https://github.com/ahmetburaki/authmatrix-cli/releases/tag/v0.1.0), was
published on November 4, 2026 after all ten main and tag CI jobs passed.

M3 tracks CI-ready reporting. [Issue #13](https://github.com/ahmetburaki/authmatrix-cli/issues/13)
adds offline JUnit export with shared evidence-to-matrix validation and
installed-package checks.
