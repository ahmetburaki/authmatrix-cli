# Schema acceptance — 2026-10-31

The matrix and evidence contracts are bundled as package data and exposed by
`authmatrix schema matrix` / `authmatrix schema evidence`. Runtime input validation,
network restrictions and report comparison remain authoritative for semantic rules.

## Local verification

- `git diff --check` and Python compilation passed.
- All 10 contract tests passed, including meta-schema checking, fragment-only
  references, offline CLI exports, installed exports outside the checkout and
  all three example matrices.
- Eight synthetic compatibility fixtures passed both structural/runtime checks;
  legacy v1/v2 baselines still demonstrate fixes against unchanged-matrix v3 runs,
  and reverse comparisons identify regressions.
- Invalid shapes, version/error mismatches and inconsistent timeout assertions
  are rejected. Tests explicitly demonstrate accepted-by-schema cases that runtime
  rejects, including disallowed targets, duplicate IDs and source-matrix mismatch.
- Reports from a disposable loopback API match the evidence contract for passing,
  failing, response-error and transport-error observations.
- All 63 tests passed locally on Python 3.14.7, including existing tenant/role,
  JSON privacy and deadline regressions.
- A wheel was built and installed without dependencies in a fresh environment.
  With neither `jsonschema` nor `referencing` installed, isolated processes outside
  the checkout successfully exported both schemas, validated all three matrices
  and compared both legacy baselines with their current reports.

The optional `jsonschema==4.26.0` validator is restricted to the test extra.
The base-install smoke blocks validator imports, and the installed-export test
uses isolated Python processes outside the source directory. No production or
external API is used for tests. No real-system evidence or TLS keys are committed.

## Hosted verification

Pending Ubuntu/Windows CI on Python 3.11–3.14. Each job first installs the base
package and checks schema exports with optional validator imports blocked, then
installs test extras, runs all 63 tests and validates all three example matrices.

## Commands

```sh
python -m pip install --no-deps .
python -I tests/check_base_install.py
python -m pip install ".[test]"
python -m compileall -q authmatrix tests
python -m unittest discover -s tests -p test_contracts.py -v
python -m unittest discover -s tests -v
authmatrix validate examples/matrix.json
authmatrix validate examples/json-matrix.json
authmatrix validate examples/tenant-matrix.json
git diff --check
```

The feature branch is stacked on PR #6. Existing PRs are not merged by this change.
