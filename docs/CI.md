# CI contract and maintenance

The `checks` workflow runs on pull requests, pushes to main and manual dispatch.
Feature-branch pushes use the PR run, avoiding duplicate push/PR matrices. New
commits cancel obsolete runs for the same PR or branch. Main still receives its
own post-merge verification. Manual dispatch requires the workflow file to be
present in the default branch.

## Execution and permissions

All eight combinations of Ubuntu/Windows and Python 3.11–3.14 run independently;
one failure does not cancel the other matrix results. Each job has a 15-minute
outer limit and performs these checks:

1. Install the base package without runtime dependencies.
2. Export both schemas with optional validator imports blocked, using isolated
   Python imports so the installed package supplies the assets.
3. Install the test extra and run the full integration/contract suite, including
   isolated installed-module JUnit exports for legacy and current evidence.
4. Validate the status, JSON-assertion, tenant/role and pinned-hostname matrices.

Tests use synthetic loopback HTTP/TLS fixtures. OpenSSL generates disposable TLS
keys. No staging or production credentials are provided. The workflow grants only
`contents: read`, opts out of persisting checkout credentials and uses ordinary
`pull_request` events. It does not use privileged `pull_request_target` execution.

After the runtime matrix passes, two distribution jobs on Ubuntu/Windows Python
3.14 build the wheel/source archive, check metadata and contents, rebuild/install
from the source archive, export JUnit through the installed console command and
run the archive's full test suite. Their candidate artifacts
contain both packages, SHA256SUMS and BUILD_INFO.json, retained for seven days.
This adds two package checks to the eight runtime jobs and does not publish a
release. See [release gates](RELEASING.md) and [acceptance](RELEASE_VALIDATION.md).

## Pinned upstream actions

| Action | Reviewed release | Exact commit |
| --- | --- | --- |
| Checkout | [v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| Python setup | [v7.1.0](https://github.com/actions/setup-python/releases/tag/v7.1.0) | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` |
| Candidate artifact upload | [v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2) | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |

The selected [checkout](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/action.yml)
and [Python setup](https://github.com/actions/setup-python/blob/6d4fd22b20465ccc0f7354476588e8df7c9ca0e0/action.yml)
manifests and the pinned artifact-upload manifest use Node 24. Checkout/setup replace the old Node 20 action
versions that emitted deprecation annotations. Full commit pins fix the code that
runs; version comments make future updates identifiable. GitHub-hosted runners
provide the required runtime. For self-hosted use, check the upstream minimum
runner requirement (at least 2.327.1 for Node 24) before enabling the workflow.

To update an action, read its official release notes, resolve the release tag to
its commit, inspect the action manifest/runner requirements, update the commit
and version comment together, and verify all eight PR jobs. Existing historical
run links remain evidence for their original revisions; see [main integration](INTEGRATION.md).

## Local checks

```sh
python -m pip install ".[test]"
python -I tests/check_base_install.py
python -m unittest discover -s tests -v
authmatrix validate examples/matrix.json
authmatrix validate examples/json-matrix.json
authmatrix validate examples/tenant-matrix.json
authmatrix validate examples/hostname-matrix.json
git diff --check
```

The default installation is tested before installing extras in CI. See
[contributing](../CONTRIBUTING.md) for local TLS prerequisites.
