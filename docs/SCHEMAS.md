# Matrix and evidence schemas

AuthMatrix bundles two self-contained [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/schema)
contracts. All references are local fragments, so validation needs no remote
schema retrieval. The installed CLI exports the same files shipped in the wheel:

```sh
authmatrix schema matrix > matrix-v1.schema.json
authmatrix schema evidence > evidence.schema.json
```

Both commands print only JSON, exit 0 and require no credentials, target or
network access. They use the standard library; the optional test dependency is
not needed. Schema IDs identify their repository locations on main; use the
bundled or exported files locally to keep validation independent of remote retrieval.

| Contract | Bundled file | Supported documents |
| --- | --- | --- |
| Matrix | `authmatrix/schemas/matrix-v1.schema.json` | Matrix version 1, with optional GET JSON assertions |
| Evidence | `authmatrix/schemas/evidence.schema.json` | Evidence versions 1, 2 and 3 |

The contracts describe required and unknown fields, allowed types/operations,
label/path/array limits, assertion shapes, error representations and version
differences. Schema 1 forbids assertion results; schema 2 permits them; schema 3
requires execution limits and adds deadline/not-run errors. Only an error case
may contain an error code. Timeout/transport cases require a null actual status;
response errors require assertion results and an observed status. An error case
cannot contain passing assertions.

The writer continues to emit evidence schema 3. No matrix/evidence version bump
or network behavior change is introduced by publishing these contracts. Legacy
schema-1/2 evidence still compares with schema 3 for unchanged source matrices.
The synthetic [compatibility corpus](../tests/fixtures/contracts/README.md)
exercises that behavior without storing observations from real systems.

## Editor use

Associate a file with the local schema through your editor's settings. For
example, a VS Code workspace opened at this repository can use this
[workspace association](https://code.visualstudio.com/docs/languages/json#_mapping-to-a-schema-in-the-workspace):

```json
{
  "json.schemas": [
    {
      "fileMatch": ["/examples/*matrix.json"],
      "url": "./authmatrix/schemas/matrix-v1.schema.json"
    }
  ]
}
```

Do not insert `$schema` into a matrix or report: the runtime contracts reject
unknown document fields. In another workspace, point the editor at the exported
schema file instead. File associations affect editor feedback, not execution.
VS Code documents limited 2020-12 support, so use the full validator or CLI for
acceptance rather than treating editor feedback as complete validation.

## Runtime validation remains required

Structural acceptance is an initial check. These additional rules remain in the
CLI and are deliberately tested as accepted-by-schema/rejected-by-runtime cases:

| Rule | Authoritative check |
| --- | --- |
| Literal IP, allowed scope, port/origin syntax and staging HTTPS | `authmatrix validate matrix.json` |
| Unique case/assertion IDs and actors referenced by cases | Matrix/runtime report validation |
| Strict JSON parsing, duplicate keys, finite numbers, input size and depth | CLI input loading |
| Integer representation: `1.0` is a JSON Schema integer but the runtime requires an integer token for version/status/index fields | Runtime validation |
| Observed status belongs to expected statuses and agrees with the overall outcome | Runtime report validation |
| Matrix digest, complete case/assertion coverage and actual fail-to-pass proof | `authmatrix compare before.json after.json --matrix matrix.json` |

Do not use schema acceptance as target authorization, proof of correctness or
evidence authenticity. Report timestamps remain strings for reader compatibility;
the writer emits UTC ISO 8601, but the schema does not add a date-format rejection
that the reader lacks. Evidence remains unsigned regression data.

## Optional Python validation

Contributors install the pinned validator through the test extra:

```sh
python -m pip install ".[test]"
python -m unittest discover -s tests -p test_contracts.py -v
```

An application already using the optional validator can inspect structure:

```python
from jsonschema import Draft202012Validator
from referencing import Registry
from authmatrix.contracts import get_schema
from authmatrix.json_checks import strict_json

schema = get_schema("matrix")
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, registry=Registry())
with open("matrix.json", encoding="utf-8") as source:
    validator.validate(strict_json(source.read()))
```

The empty registry has no remote retrieval callback. This example checks shape;
still run the CLI's matrix validation before execution. Validator exceptions can
contain input values; keep any diagnostic output private. The CLI's generic error
messages and minimized evidence behavior are unchanged.

For validator behavior, see the official [validation documentation](https://python-jsonschema.readthedocs.io/en/stable/validate/).
For completed checks and platform results, see [schema acceptance](SCHEMA_VALIDATION.md).
