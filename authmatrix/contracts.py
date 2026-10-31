"""Bundled structural contracts; runtime validation remains authoritative."""
import json
from importlib.resources import files


SCHEMA_FILES = {"matrix": "matrix-v1.schema.json", "evidence": "evidence.schema.json"}


def get_schema(name):
    resource = files("authmatrix").joinpath("schemas", SCHEMA_FILES[name])
    return json.loads(resource.read_text(encoding="utf-8"))
