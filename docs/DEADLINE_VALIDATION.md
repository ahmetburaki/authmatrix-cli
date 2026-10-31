# Deadline fix acceptance — 2026-10-31

Historical feature acceptance; original counts and run links are retained below.
The fix is now integrated into main; see [combined acceptance](INTEGRATION.md).

## Boundary and reproduction

The October 27 security review identified a low-severity availability problem:
`core.run()` relied on per-operation socket timeouts while HTTP parsing and JSON
reads could receive repeated progress from a slow selected target. The CLI saved
its evidence only after the sequential run returned.

Before the patch, a finite loopback slow-header reproduction completed after
0.666 seconds as a passing observation, exceeding the 0.2-second threshold used
to demonstrate the missing elapsed-time control. The regression suite now uses
explicit 0.15–0.25-second budgets against slow status, headers, fixed-length and
close-delimited JSON, chunk extensions/trailers and TLS handshakes. Each is bounded
and recorded as an error, not a late pass.

## Ordered verification

1. Diff/compile checks: `git diff --check` and Python compilation passed.
2. Focused security tests: all 16 deadline tests passed, including header and body
   variants, verified HTTPS, default TLS rejection, delayed TCP-to-TLS allowance,
   explicit connection cleanup and non-main-thread use.
3. Compatibility/package checks: all 53 tests passed locally on Python 3.14.7;
   wheel build/install and all three installed-CLI matrix validations passed.
   Legacy schema 1/2 reports compare with schema 3 using unchanged matrices.
4. Installed CLI ran outside the source directory against an OS-selected loopback
   port with a 0.2-second run budget. Including Python startup, completion took
   0.271 seconds, saved schema-3 evidence, exited 2 and recorded:
   `pass`, `run_timeout`, `not_run`. The last request was never sent.

Previously completed results are retained, per-request timeout permits later cases
within the run budget, and exhausted/unstarted cases cannot produce a complete
proof of fix. Existing JSON, tenant/role and status-only behavior remained passing.

One fresh read-only investigator established the boundary before implementation.
One fresh read-only bypass/regression reviewer inspected the candidate afterward
and found no concrete runtime/API bypass or regression. Its OpenSSL test-prerequisite
observation was addressed with explicit setup documentation; the CLI itself does
not execute or require the OpenSSL command. Tests generate and remove disposable
TLS key material rather than committing it.

## Hosted checks

[All eight PR jobs passed](https://github.com/ahmetburaki/authmatrix-cli/actions/runs/41235021810)
on Ubuntu and Windows using Python 3.11, 3.12, 3.13 and 3.14 for runtime revision
`64a3836953275b9492565e721171b154b4bfff3d`. The
[push run](https://github.com/ahmetburaki/authmatrix-cli/actions/runs/41235018059)
also passed. Each job installs the package, runs all 53 tests and validates all
three matrices.

The first Windows run exposed socket timers expiring just before the monotonic
clock crossed the configured limit. The implementation now retains the allowance's
limiting deadline, and a deterministic regression test covers early timer expiry
and suppression of subsequent requests after a run timeout. Ordinary inactivity
timeouts retain their existing transport-error classification.

## Changed files and verification commands

Runtime enforcement lives in `authmatrix/deadlines.py` and `core.py`; `cli.py`
exposes the limits, and `json_checks.py` propagates deadline errors. Regression
coverage is in `tests/test_deadlines.py`, with evidence-version expectations in
`test_json_checks.py` and the POSIX-only permission check in `test_core.py`.
The CI workflow adds Windows to the supported Python matrix. README, contributor
instructions and the deadline/evidence/roadmap documents describe these contracts.

The following gates passed for the 53-test feature revision. For current main,
install the test extra and follow [CI.md](CI.md); it includes the later schema tests.

```sh
git diff --check
python -m compileall -q authmatrix tests
python -m unittest discover -s tests -p test_deadlines.py -q  # 16 tests
python -m unittest discover -s tests -v                     # 53 tests
python -m pip wheel --no-deps --no-cache-dir --wheel-dir /tmp/authmatrix-wheels .
python -m pip install --no-deps --force-reinstall /tmp/authmatrix-wheels/authmatrix_cli-0.1.0-py3-none-any.whl
authmatrix validate examples/matrix.json
authmatrix validate examples/json-matrix.json
authmatrix validate examples/tenant-matrix.json
```

The actual local wheel destination was the security tool's disposable artifact
directory rather than the illustrative `/tmp/authmatrix-wheels` path. An initial
`--no-build-isolation` attempt could not import the environment's missing
setuptools; the standard isolated build above and installation both passed.
Installed-CLI validation and the loopback smoke ran outside the source directory.

## Integration and remaining limits

PR #6 was originally stacked on PR #5 and PR #4. After those predecessors merged,
it was retargeted and merged into main on October 31. The fix's original review
scope was deadlines, error/evidence compatibility, regression tests and documentation.
No release was published.

Timeouts bound network execution through absolute monotonic allowances. Local
input loading/output writing, validation/evaluation and OS scheduling are not
preempted; completion can include bounded local overhead. No production or external
API was contacted. No TLS verification, authorization or target restriction was
relaxed, and no timer/worker cancellation thread was introduced. Evidence remains
unsigned, as before. This is fix verification within the implementation workflow,
not a new repository-wide security scan or a change to the sealed October 27 report.
