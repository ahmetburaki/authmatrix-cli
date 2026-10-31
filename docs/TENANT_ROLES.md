# Tenant and role isolation example

The loopback-only [tenant API](../examples/tenant_api.py) and explicit
[21-case matrix](../examples/tenant-matrix.json) exercise the existing CLI against
two tenants (`a`, `b`) and two roles (`member`, `admin`). All identities, tokens
and resources are synthetic. The API is a test fixture, not a server framework or
a recommended production authentication implementation.

## Policy and controls

- A member can read its own documents; another member's documents are denied.
- An admin can read documents within its own tenant.
- Members and admins can read their own tenant's summary.
- Only a tenant's own admin can read its admin report.
- A role never grants access across tenants.
- Missing/unknown credentials are denied even when a synthetic fault is enabled.

The matrix has 9 positive cases, 10 authorization denials and 2 anonymous denials.
Every denial has a positive case for the same resource. Positive JSON assertions
verify both the returned tenant and document/view, so a bare HTTP 200 is insufficient.

| Boundary | Denied requests | Positive controls on the same resources |
| --- | --- | --- |
| Ownership | A owner reads peer document; A peer reads owner document | Each member reads its own document |
| Tenant summary | A member reads B summary; B member reads A summary | Each member reads its own tenant summary |
| Tenant document | A admin reads B document; B admin reads A document | Each admin reads its own tenant document |
| Role | A/B member reads own tenant admin report | A/B admin reads own tenant report |
| Tenant report | A/B admin reads the other tenant report | A/B admin reads own tenant report |
| Anonymous | Anonymous reads document or admin report | Owner document access and admin report access |

## Independent fault modes

Only the selected policy gate is disabled; authentication remains enforced.
`all` disables the three authorization gates together. These modes deliberately
model unsafe behavior only in this synthetic server, bound to `127.0.0.1:8766`.
There is no configurable bind address, external target, stored credential or data.

| `--fault` | Expected passing cases | Expected failing cases | What the matrix demonstrates |
| --- | --- | --- | --- |
| `none` (default) | 21 | 0 | Declared policy holds for all cases |
| `ownership` | 19 | 2 | Same-tenant cross-owner access is detected |
| `tenant` | 15 | 6 | Cross-tenant access is detected for members and admins |
| `role` | 19 | 2 | Member-to-admin escalation is detected |
| `all` | 11 | 10 | All declared authorization denials fail; positives/authentication stay passing |

These are expected matrix outcomes against the deliberately faulty fixtures,
not failed unit tests. The automated suite verifies the exact failing IDs for
each mode, not only totals. Restoring just part of the policy does not produce
`proof_of_fix=true` while other cases remain failing.

## Reproduce the full fix

Use Python 3.11+ from the repository root. In terminal A:

```sh
python3 examples/tenant_api.py --fault all
```

In terminal B:

```sh
export AUTHMATRIX_A_OWNER_TOKEN=demo-a-owner
export AUTHMATRIX_A_PEER_TOKEN=demo-a-peer
export AUTHMATRIX_A_ADMIN_TOKEN=demo-a-admin
export AUTHMATRIX_B_OWNER_TOKEN=demo-b-owner
export AUTHMATRIX_B_ADMIN_TOKEN=demo-b-admin
mkdir -p evidence
python3 -m authmatrix validate examples/tenant-matrix.json
python3 -m authmatrix run examples/tenant-matrix.json --authorized --output evidence/tenant-before.json
```

Expected: 11 pass, 10 fail, 0 error; exit 1. Stop terminal A with Ctrl-C and
restart it without a fault:

```sh
python3 examples/tenant_api.py
```

Then in terminal B:

```sh
python3 -m authmatrix run examples/tenant-matrix.json --authorized --output evidence/tenant-after.json
python3 -m authmatrix compare evidence/tenant-before.json evidence/tenant-after.json --matrix examples/tenant-matrix.json
```

Expected: 21 passing cases; comparison reports 10 fixed cases, no regressions and
`proof_of_fix=true`. Choose new output filenames on repeat runs. The matrix and
tokens are unchanged between baseline and rerun; only fixture policy changes.

Tests allocate an OS-selected loopback port and clean up the server. They do not
need the fixed demonstration port. Evidence retains generic case/actor/assertion
IDs and outcomes, not tokens, response payloads or endpoint paths.

This matrix demonstrates the declared policy on the fixture. It does not infer
an application's authorization model or establish comprehensive tenant coverage.
