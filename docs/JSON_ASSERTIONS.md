# JSON response assertions

Opt in per GET case with `assert_json`. Matrix files remain version 1. Status-only
cases do not read response bodies; new evidence uses schema 3 with deadline metadata.
Both status and every configured assertion must pass for an asserted case to pass.

```json
{
  "id": "public-profile",
  "actor": "other",
  "method": "GET",
  "path": "/profiles/1",
  "expect_status": [200],
  "assert_json": [
    {"id": "public-name", "path": ["display_name"], "op": "equals", "value": "demo"},
    {"id": "restricted-field", "path": ["private_email"], "op": "absent"}
  ]
}
```

## Operations and paths

| Operation | Required fields | Meaning |
| --- | --- | --- |
| `present` | `id`, `path`, `op` | Field exists; JSON null counts as present. |
| `absent` | `id`, `path`, `op` | Field is missing; null does not count as missing. |
| `equals` | `id`, `path`, `op`, `value` | Field exists and exactly matches a scalar value and its type. |

Paths are explicit lists of object keys (strings) and array indices (nonnegative
integers). For example, `["items", 0, "tenant"]` selects the first item's tenant.
Keys containing periods or slashes are literal keys. No wildcards, scripts,
regular expressions or recursive searches are supported.

If a key/index is missing on a well-typed traversal, `absent` passes and the other
operations fail. A wrong container type fails every operation: `{"profile":null}`
does not satisfy an assertion that `profile.private_email` is absent. An absent
ancestor counts as absence, so pair negative checks with a positive assertion for
the public response shape. `equals` accepts strings, finite numbers, booleans and
null; it rejects object/array expectations. Comparison is type-strict: `true`, `1`
and `1.0` are distinct. Values in a matrix are local configuration and may be
sensitive; prefer synthetic identifiers and keep real private matrices outside Git.

Limits: 1–32 assertions per case, unique generic IDs, 1–16 path segments, at most
256 characters per string segment, array index at most 1,000,000, and expected
string at most 4096 characters. HEAD cases cannot assert a JSON body.

## Reading and failure behavior

Asserted responses must use UTF-8 JSON with `application/json` or an
`application/*+json` media type. Parameters are permitted; UTF-8 is always used.
Content encodings other than identity are rejected; there is no decompression.
The reader requests at most 65,537 body bytes: 64 KiB plus one sentinel byte.
Larger bodies become errors. Chunk framing and headers are handled separately by
Python's HTTP client; the limit is on body bytes, not total network bytes.

Malformed, empty, truncated, duplicate-key, non-finite and excessively nested JSON
become `response_error`. Maximum JSON container depth is 64; malformed inputs
may also hit the interpreter's parser limit sooner. No body content or exception
text is printed. Errors exit 2 and cannot count as a demonstrated fix. A valid
JSON response with a wrong expected field or status exits 1.

Request/run deadlines now bound network execution in addition to the five-second
socket inactivity limit; see [deadline behavior](DEADLINES.md). Field assertions only
cover the declared paths, not every possible leak. Large responses require a
smaller fixture/endpoint or future supported limits; do not silently skip checks.

## Evidence compatibility

New runs emit evidence schema 3. Legacy JSON-asserted runs used schema 2. Each asserted case adds
`assertions`, a list of `{id, outcome}` objects; field paths, expected values and
observed values are omitted. Generic assertion IDs are persisted, so they must
not contain secrets. Status-only cases in a mixed run have no `assertions` field.
A response error retains the observed HTTP status and uses the generic
`response_error` code. A connection error uses `transport_error` and null status.

Offline comparison verifies both reports against the complete source matrix and
its assertion IDs. It rejects missing/redefined checks, schema downgrades and
contradictory outcomes. Existing status-only schema-1 reports remain comparable
with their unchanged matrices. Unsigned evidence can still be fabricated; this
is not independent attestation.

## Reproduce a same-status leak

Use the README's environment variables and local example server. With the server
started using `--vulnerable`, run:

```sh
python3 -m authmatrix run examples/json-matrix.json --authorized --output evidence/json-before.json
```

Expected exit 1: owner sees its field, anonymous is denied, and the other actor
incorrectly sees the restricted field. Both authenticated requests return 200.
Stop the example server, restart without `--vulnerable`, then run:

```sh
python3 -m authmatrix run examples/json-matrix.json --authorized --output evidence/json-after.json
python3 -m authmatrix compare evidence/json-before.json evidence/json-after.json --matrix examples/json-matrix.json
```

Expected: `fixed=["other-public-view"]`, no regressions, `proof_of_fix=true`, exit 0.
The owner still receives its field; the other actor receives only the public view.
