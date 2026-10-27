# JSON assertion acceptance — 2026-10-27

## Local results

- 30 unittest tests passed on Python 3.14.7, including all 16 original tests.
- Wheel built and installed into an isolated environment with no runtime dependencies.
- Both example matrices validated with the installed CLI.
- Installed CLI executed outside the source directory against the provided example
  API bound to a loopback port chosen by the OS.
- Original status-only example: failing baseline exit 1, corrected run exit 0,
  comparison exit 0 and `fixed=["cross-owner-denied"]`.
- JSON example: failing baseline exit 1, corrected run exit 0, comparison exit 0
  and `fixed=["other-public-view"]`. Both authenticated responses stayed HTTP 200;
  owner visibility and anonymous denial passed before and after the correction.
- No regressions in either comparison. Both returned `proof_of_fix=true`.

New tests cover exact read limits, chunked and lengthless responses, truncation,
malformed/empty/duplicate-key/non-finite/deep JSON, content type/encoding rejection,
array traversal, null versus missing fields, type-strict scalar matching, sensitive
field/value omission, schema downgrades and omitted assertion evidence. A Python
parser depth difference was caught locally; an explicit depth limit now keeps the
contract consistent across supported versions.

## Hosted checks

Pending the feature branch's GitHub Actions run. CI tests Python 3.11–3.14 and
validates both example matrices with the installed CLI.

## Limits

Only synthetic local endpoints were contacted. Assertions cover explicit fields,
not every possible leak. The body cap does not impose a whole-request deadline;
issue #3 tracks wall-clock budgets. Evidence remains unsigned. This feature does
not publish a release tag or select a distribution license.
