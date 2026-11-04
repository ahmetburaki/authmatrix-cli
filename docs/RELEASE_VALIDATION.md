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
  dirty while preparing this PR; a later build from clean candidate commit
  `977aaffc82195f1d3e88a1183e74ab938fa629a3` passed and recorded dirty=false.
- The source archive also retains `.gitignore`, preserving private-key/evidence
  ignore rules when working from the source distribution. CI requires a clean
  checkout matching its expected revision through `--require-clean`.

## Hosted candidate checks

The [first candidate run](https://github.com/ahmetburaki/authmatrix-cli/actions/runs/41528142585)
passed all eight runtime jobs plus both Ubuntu/Windows Python 3.14 distribution
jobs for candidate head `977aaffc82195f1d3e88a1183e74ab938fa629a3`. GitGuardian
also passed. Both uploaded candidates were downloaded and their checksums, MIT
metadata, version and clean-tree state independently checked.

PR artifacts record GitHub's tested merge revision in BUILD_INFO.json; that run
recorded `6640904e339b740b0f0cfaa6b097c2d3d72fb01c`. A release must instead be
built from its approved main/tag revision as described in the procedure.

Each distribution job rebuilds/installs from the sdist, runs the full suite from
it and uploads candidate files plus hashes/build information for seven days.
Uploads are CI artifacts, not published releases; permission remains contents-read.
See [PR #10 checks](https://github.com/ahmetburaki/authmatrix-cli/pull/10/checks)
for the current workflow result after the clean-revision and ignore-rule followup.
