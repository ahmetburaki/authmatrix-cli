# AuthMatrix CLI

A dependency-free Python CLI for explicit API authorization regression checks on
owned local and private staging APIs. AuthMatrix CLI is a standalone project
with its own package, command-line interface and release roadmap. The name is
provisional.

Define actor/resource expectations, detect a mismatch, apply your API fix, rerun
and compare evidence. The MVP supports GET/HEAD, exact expected status codes
and opt-in JSON field assertions on GET responses.
It does not discover endpoints or prove the absence of authorization bugs.

## Quick start (Python 3.11+)

From the repository root, use a Python 3.11+ interpreter. On this development
machine that is `python3.14`; replace `python3` below if your default is older.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --no-deps .
python -m unittest discover -s tests -v
authmatrix validate examples/matrix.json
```

No runtime dependencies. Installation uses setuptools as the build dependency.
Alternatively use `python3 -m authmatrix` without installing.

### Reproduce a failure and validate a fix

In terminal A start the synthetic, loopback-only example:

```sh
python3 examples/local_api.py --vulnerable
```

In terminal B, from the same repository:

```sh
export AUTHMATRIX_OWNER_TOKEN=demo-owner
export AUTHMATRIX_OTHER_TOKEN=demo-other
mkdir -p evidence
python3 -m authmatrix run examples/matrix.json --authorized --output evidence/before.json
```

Expected exit 1: the other actor incorrectly receives 200 instead of 403.
Stop terminal A with Ctrl-C and restart the fixed API:

```sh
python3 examples/local_api.py
```

Then in terminal B:

```sh
python3 -m authmatrix run examples/matrix.json --authorized --output evidence/after.json
python3 -m authmatrix compare evidence/before.json evidence/after.json --matrix examples/matrix.json
```

Expected: `fixed: ["cross-owner-denied"]`, `proof_of_fix: true`, exit 0.
This validates the declared expectations for these requests only. Transport errors
never count as fixes. An unchanged passing run is not a demonstrated fix.

## Matrix contract

See [examples/matrix.json](examples/matrix.json). Schema version 1 is strict:
unknown keys and duplicate case IDs are rejected. Each case identifies its actor,
method, path and nonempty list of accepted HTTP statuses. Tokens are loaded only
from named environment variables; `null` means anonymous. All credentials are
checked before any network request. Keep labels generic and free of secrets.

Use owner, other-owner, anonymous, role and tenant cases explicitly. Include
positive controls so denial of every request cannot make the whole suite pass.
For APIs returning 200 with unauthorized fields, add [JSON assertions](docs/JSON_ASSERTIONS.md)
for field presence, absence or scalar equality; see [examples/json-matrix.json](examples/json-matrix.json).
Do not accept 200 and 403 together for a denial case.

The [tenant/role example](docs/TENANT_ROLES.md) adds a loopback API with two
tenants, two roles and 21 explicit cases. Independent ownership, tenant and role
fault modes demonstrate which cases fail, with positive controls for every denial.

## Target and execution boundary

- Only explicit IP origins: loopback for `local`; loopback or RFC1918/IPv6 ULA
  for `staging`. Hostnames, public IPs, link-local/metadata and unspecified IPs
  are rejected. Staging requires HTTPS with normal certificate validation.
  Certificates must cover the IP address; custom hostnames/CA options are deferred.
- `--authorized` confirms that you own or have permission to test the target.
  Private IPs do not establish permission. Production is outside scope; do not
  label a production service as staging. Network restrictions cannot infer this.
- GET/HEAD only, sequential requests, maximum 200 cases, five-second socket
  timeout per operation, no redirects, retries, proxy discovery or TLS bypass.
  Socket timeout is not a whole-run deadline; a slowly streaming header can extend
  execution. GET endpoints must still be reviewed for side effects.
- Tokens go directly to the specified origin. Status-only cases never read bodies.
  Asserted GET cases read at most 64 KiB plus one sentinel byte and reject invalid
  or oversized JSON. Raw bodies and response headers are never persisted. No scanning or
  automatic endpoint enumeration takes place.

## Evidence and exit codes

Evidence records only schema version, UTC time, matrix SHA-256, generic actor/case
IDs, expected and actual statuses, outcomes and generic error codes. JSON-asserted
runs use evidence schema 2 and add only generic assertion IDs and outcomes. It omits
origins, paths, queries, token values, environment variable names, response bodies,
headers and exception details. IDs are user-supplied and must not contain secrets.
A digest is for matching configurations, not anonymization or evidence signing.
Evidence is private by default, ignored by Git, created exclusively with mode 0600
(on POSIX), and never overwritten. Review even minimized evidence before sharing.

`compare` requires `--matrix` and checks both reports against its digest and full
case definitions. Missing, renamed or redefined cases are rejected even if both
reports were changed the same way. Comparison is offline and does not need tokens.
This check does not authenticate observations; unsigned files can still be forged. Proof of fix
requires at least one observed fail→pass and all current cases passing. Evidence
is unsigned local data; this is regression validation, not independent attestation.

| Command | 0 | 1 | 2 |
| --- | --- | --- | --- |
| validate | valid | — | invalid input |
| run | all passed | expectation mismatch | transport/response/config/output error |
| compare | demonstrated fix, all pass | no demonstrated complete fix | invalid/incompatible evidence |

See [roadmap](docs/ROADMAP.md), [contributing](CONTRIBUTING.md) and
[engineering decisions](docs/DECISIONS.md). Current focus: quality, reproducibility,
reviewable GitHub changes. No acquisition, revenue, marketing or outreach work.

Repository: [ahmetburaki/authmatrix-cli](https://github.com/ahmetburaki/authmatrix-cli).
See [open issues](https://github.com/ahmetburaki/authmatrix-cli/issues) and
[milestones](https://github.com/ahmetburaki/authmatrix-cli/milestones) for the next work.
