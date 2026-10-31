"""Opt-in, bounded JSON checks. Never return field paths or response values."""
import http.client
import json
import math


MAX_BODY_BYTES = 64 * 1024
MAX_JSON_DEPTH = 64


def strict_json(text):
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError("Duplicate JSON key")
            obj[key] = value
        return obj

    def invalid_constant(_):
        raise ValueError("Non-finite JSON number")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite JSON number")
        return number

    document = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant,
                          parse_float=finite_float)
    stack = [(document, 1)]
    while stack:
        value, depth = stack.pop()
        if isinstance(value, (dict, list)):
            if depth > MAX_JSON_DEPTH:
                raise ValueError("JSON depth limit exceeded")
            children = value.values() if isinstance(value, dict) else value
            stack.extend((child, depth + 1) for child in children)
    return document


def valid_checks(checks, label_pattern):
    if not isinstance(checks, list) or not 1 <= len(checks) <= 32:
        return False
    ids = set()
    for check in checks:
        if not isinstance(check, dict):
            return False
        op = check.get("op")
        keys = {"id", "path", "op"} | ({"value"} if op == "equals" else set())
        if set(check) != keys or op not in ("equals", "present", "absent"):
            return False
        # Generic IDs use the same public label contract as cases and actors.
        name = check["id"]
        if not isinstance(name, str) or not label_pattern.fullmatch(name) or name in ids:
            return False
        ids.add(name)
        path = check["path"]
        if not isinstance(path, list) or not 1 <= len(path) <= 16:
            return False
        for part in path:
            if type(part) is int and 0 <= part <= 1_000_000:
                continue
            if isinstance(part, str) and len(part) <= 256:
                continue
            return False
        if op == "equals":
            value = check["value"]
            if value is not None and type(value) not in (str, int, float, bool):
                return False
            if isinstance(value, str) and len(value) > 4096:
                return False
            if type(value) is float and not math.isfinite(value):
                return False
    return True


def resolve(document, path):
    """Return (shape_valid, exists, value), keeping absent separate from null."""
    current = document
    for part in path:
        if isinstance(part, str) and isinstance(current, dict):
            if part not in current:
                return True, False, None
            current = current[part]
        elif type(part) is int and isinstance(current, list):
            if part >= len(current):
                return True, False, None
            current = current[part]
        else:
            return False, False, None
    return True, True, current


def evaluate(document, checks):
    results = []
    for check in checks:
        shape_valid, exists, value = resolve(document, check["path"])
        op = check["op"]
        passed = shape_valid and (
            (op == "present" and exists) or (op == "absent" and not exists) or
            (op == "equals" and exists and type(value) is type(check["value"])
             and value == check["value"])
        )
        results.append({"id": check["id"], "outcome": "pass" if passed else "fail"})
    return results


def error_results(checks):
    return [{"id": check["id"], "outcome": "error"} for check in checks]


def check_response(response, checks):
    try:
        media = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
        if (media != "application/json" and not (media.startswith("application/") and media.endswith("+json"))):
            raise ValueError("JSON media type required")
        if response.getheader("Content-Encoding", "identity").strip().lower() != "identity":
            raise ValueError("Compressed responses are unsupported")
        # Read at most the limit plus one sentinel byte, independent of declared size.
        body = response.read(MAX_BODY_BYTES + 1)
        if len(body) > MAX_BODY_BYTES:
            raise ValueError("JSON body limit exceeded")
        if response.length is not None and response.length != 0:
            raise ValueError("Truncated JSON response")
        document = strict_json(body.decode("utf-8"))
        return evaluate(document, checks)
    except (OSError, http.client.HTTPException, ValueError, RecursionError):
        # Includes malformed/truncated/oversized bodies. No exception text escapes.
        return error_results(checks)
