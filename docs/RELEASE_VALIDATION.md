# First release preparation — 2026-11-03

This is acceptance for the 0.1.0 candidate, not a published release. MIT was
selected by the repository owner. No tag, GitHub release or PyPI upload has been
created by this work. See [the release procedure](RELEASING.md).

## Integrated baseline

PR #9 merged into main at `34849b478e0037354a5e05a372b756454559c91d`.
Its file tree matched the reviewed feature head exactly, and
[main CI](https://github.com/ahmetburaki/authmatrix-cli/actions/runs/41524941916)
passed all eight Ubuntu/Windows Python 3.11–3.14 runtime jobs.

## Local candidate checks

- Wheel and source archive built using PyPA build 1.6.1 and setuptools 84.2.1.
  `twine check --strict` passed for both, including the README and MIT metadata.
- The package version comes from `authmatrix.__version__`; metadata, isolated
  module invocation and the installed console script agree on 0.1.0.
- MIT license bytes, schema assets, source/test/example files and archive paths
  passed inspection. The source archive rebuilt an identical runtime payload.
- A new virtual environment installed the rebuilt wheel without dependencies.
  Outside the source tree it exported both schemas, validated all four matrices
  and completed both legacy-to-current report comparisons.
- All 79 tests passed from the extracted source archive. Existing runtime tests
  exercise only synthetic loopback APIs.
- Negative artifact checks rejected a missing schema, wrong license metadata,
  an environment file and a source archive symlink before execution/extraction.
- SHA256SUMS and BUILD_INFO.json were generated. The first local build was marked
  dirty while preparing this PR; publication requires a clean approved revision.

## Hosted candidate checks

Pending the updated workflow. It retains the eight runtime jobs and adds two
distribution jobs on Ubuntu/Windows Python 3.14. Each builds/validates the archives,
rebuilds/installs from the sdist, runs the full suite from it and uploads candidate
files plus hashes/build information for seven days. Uploads are CI artifacts,
not published releases; repository permission remains contents-read.
