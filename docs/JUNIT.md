# Offline JUnit reporting

The development branch adds `authmatrix junit` for CI test-result reports.
Install the current source checkout to use it. The stable v0.1.0 release predates
this command.

From the repository root, export a completed run against its original matrix.
Use the [local quick start](../README.md#reproduce-a-failure-and-validate-a-fix)
to create synthetic before/after evidence.

```sh
authmatrix junit evidence/after.json --matrix examples/matrix.json --output evidence/after.xml
```

The command validates the source matrix, evidence structure and outcomes, matrix
digest, full case definitions and JSON-assertion coverage before creating XML.
It accepts matching evidence schemas 1, 2 and 3. All work is offline and uses the
Python standard library.

## Case mapping and exit codes

The XML contains one `testsuites` root and one `testsuite` named `authmatrix`.
Each evidence case becomes a `testcase`. Its name is the case ID, and its
classname is `authmatrix.ACTOR_ID`. Counts describe cases, including cases with
multiple JSON assertions.

| Evidence outcome | XML result | Command exit |
| --- | --- | --- |
| All cases pass | Test cases with no failure/error children | 0 |
| At least one mismatch, with all other cases passing or failing | A failure child for each mismatch | 1 |
| Any execution error | An error child for each affected case | 2 |
| Invalid input or output creation failure | Generic console error | 2 |

Transport errors, response errors, request/run timeouts and `not_run` each produce
an error child with the corresponding generic error code. A valid report
containing errors still produces XML. Invalid input is rejected before output
creation. Errors take precedence over failures for the command exit code.

Failure details contain the expected/observed HTTP statuses and failed
JSON-assertion IDs. Output is limited to generic case/actor/assertion labels,
status codes and error codes. Operators should keep those labels free of
sensitive information. The output file is created exclusively with owner-only
permissions on POSIX. Choose a new path for each export.

Evidence supplies case outcomes. The source matrix supplies validation, while
the exporter renders the minimized observations. The XML retains the trust
properties of unsigned evidence. Per-case timing would require additional
measurements in the evidence contract.

## CI collection

Run the export step after the API check, including when that check returns a
nonzero status. Retain the original run status as a job gate, and collect the
XML artifact even when the exporter returns 1 or 2. If input validation fails,
the command returns 2 before creating a report.

GitLab reads testcase names/classnames and failure/error children, and accepts
XML paths under `artifacts:reports:junit`. Use `artifacts:when: always` when
collecting reports from unsuccessful jobs. This implementation follows that
documented XML subset. [GitLab unit test reports](https://docs.gitlab.com/ci/testing/unit_test_reports/)

The repository tests parse exported XML, exercise the local before/after CLI
flow, verify legacy/current inputs from an installed package and check the
dependency-free console command from rebuilt archives on Ubuntu and Windows.

## Hosted GitHub Actions acceptance

The `junit-report` job installs the base package and runs
`tools/check_junit_ci.py`. It starts the bundled loopback API, runs the installed
CLI against the vulnerable and fixed modes, exports both reports and verifies
the expected fix through comparison. Stored synthetic timeout and `not_run`
evidence also passes through the installed exporter.

The checker parses the XML, checks every actor/case outcome and suite count
against the fixture expectations, and writes a Markdown table to
`GITHUB_STEP_SUMMARY`. GitHub displays this table on the workflow run summary.
[GitHub job summaries](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#adding-a-job-summary)

The vulnerable scenario has one expected failure, while the fixed scenario has
three passing cases. Each stored execution-error scenario has one expected
error. The acceptance job succeeds when all four scenarios match those
expectations and comparison confirms the cross-owner fix. Any unexpected exit
code, XML outcome or count fails the job.

The job uploads the four XML files, comparison result and summary with seven-day
retention. Its upload step also runs after a failed acceptance check, so partial
outputs can be inspected. Artifacts contain synthetic data from this fixture.

To reproduce the acceptance locally after installing the package, choose a new
output directory.

```sh
python tools/check_junit_ci.py --output evidence/junit-ci
```

The output's `summary.md` contains the same table used by GitHub.
