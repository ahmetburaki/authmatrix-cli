"""Run with python -I after a base install, before installing test extras."""
import contextlib
import io
import json
import sys

# Fail if a runtime path starts importing the optional contract validators.
sys.modules.update({"jsonschema": None, "referencing": None})

from authmatrix.cli import main


for kind in ("matrix", "evidence"):
    with contextlib.redirect_stdout(io.StringIO()) as console:
        assert main(["schema", kind]) == 0
    document = json.loads(console.getvalue())
    assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert document["type"] == "object"
    assert document["additionalProperties"] is False

print("Base-install schema exports passed without optional validator imports")
