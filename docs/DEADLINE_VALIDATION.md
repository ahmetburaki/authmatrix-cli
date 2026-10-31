# Deadline fix acceptance — 2026-10-31

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
2. Focused security tests: all 15 deadline tests passed, including header and body
   variants, verified HTTPS, default TLS rejection, delayed TCP-to-TLS allowance,
   explicit connection cleanup and non-main-thread use.
3. Compatibility/package checks: all 52 tests passed locally on Python 3.14.7;
   wheel build/install and all three installed-CLI matrix validations passed.
   Legacy schema 1/2 reports compare with schema 3 using unchanged matrices.
4. Installed CLI ran outside the source directory against an OS-selected loopback
   port with a 0.2-second run budget. Including Python startup, completion took
   0.281 seconds, saved schema-3 evidence, exited 2 and recorded:
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

Pending the feature branch's Ubuntu/Windows jobs on Python 3.11–3.14. Each job
installs the package, runs the full suite and validates all three matrices.

## Integration and remaining limits

This fix is stacked on PR #5, which is stacked on PR #4. Its review diff is scoped
to deadlines, error/evidence compatibility, regression tests and documentation.
No merge or release is implied.

Timeouts bound network execution through absolute monotonic allowances. Local
input loading/output writing, validation/evaluation and OS scheduling are not
preempted; completion can include bounded local overhead. No production or external
API was contacted. No TLS verification, authorization or target restriction was
relaxed, and no timer/worker cancellation thread was introduced. Evidence remains
unsigned, as before. This is fix verification within the implementation workflow,
not a new repository-wide security scan or a change to the sealed October 27 report.
