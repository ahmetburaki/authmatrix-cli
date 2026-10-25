"""Strict matrix validation, bounded HTTP checks and minimal evidence."""
import hashlib
import http.client
import ipaddress
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit


class ConfigError(ValueError):
    pass


LABEL = re.compile(r"[a-zA-Z0-9_-]{1,64}\Z")
ENV = re.compile(r"[A-Z_][A-Z0-9_]{0,127}\Z")
PRIVATE = tuple(ipaddress.ip_network(n) for n in
                ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7"))


def exact(obj, keys):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise ConfigError("Invalid object fields")


def label(value):
    if not isinstance(value, str) or not LABEL.fullmatch(value):
        raise ConfigError("IDs must be 1-64 ASCII letters, digits, underscores or hyphens")


def validate(matrix):
    exact(matrix, ("version", "environment", "base_url", "actors", "cases"))
    if type(matrix["version"]) is not int or matrix["version"] != 1:
        raise ConfigError("Unsupported matrix version")
    if matrix["environment"] not in ("local", "staging"):
        raise ConfigError("Only local and staging environments are supported")
    try:
        url = urlsplit(matrix["base_url"])
        ip = ipaddress.ip_address(url.hostname)
        port = url.port
    except (ValueError, TypeError, AttributeError):
        raise ConfigError("Target must use an explicit loopback or private IP") from None
    if (url.scheme not in ("http", "https") or url.username is not None
            or url.password is not None or url.path not in ("", "/")
            or url.query or url.fragment or port == 0):
        raise ConfigError("Invalid target origin")
    # Keep behavior stable across Python ipaddress classification changes.
    if isinstance(ip, ipaddress.IPv6Address) and (ip.ipv4_mapped or ip.scope_id):
        raise ConfigError("Mapped and scoped IPv6 targets are unsupported")
    if ip.is_loopback:
        pass
    elif matrix["environment"] != "staging" or not any(ip in net for net in PRIVATE):
        raise ConfigError("Target outside local/private staging scope")
    if matrix["environment"] == "staging" and url.scheme != "https":
        raise ConfigError("Staging requires verified HTTPS")
    actors = matrix["actors"]
    if not isinstance(actors, dict) or not 1 <= len(actors) <= 32:
        raise ConfigError("Expected 1-32 actors")
    for name, actor in actors.items():
        label(name)
        exact(actor, ("token_env",))
        env = actor["token_env"]
        if env is not None and (not isinstance(env, str) or not ENV.fullmatch(env)):
            raise ConfigError("Invalid token environment variable")
    cases = matrix["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 200:
        raise ConfigError("Expected 1-200 cases")
    ids = set()
    for case in cases:
        exact(case, ("id", "actor", "method", "path", "expect_status"))
        label(case["id"])
        if case["id"] in ids:
            raise ConfigError("Duplicate case ID")
        ids.add(case["id"])
        if not isinstance(case["actor"], str) or case["actor"] not in actors:
            raise ConfigError("Unknown actor")
        if case["method"] not in ("GET", "HEAD"):
            raise ConfigError("MVP supports GET and HEAD only")
        path = case["path"]
        if (not isinstance(path, str) or not path.startswith("/")
                or path.startswith("//") or "#" in path or "\\" in path
                or len(path) > 2048 or any(ord(c) < 33 or ord(c) > 126 for c in path)):
            raise ConfigError("Invalid request path")
        statuses = case["expect_status"]
        if (not isinstance(statuses, list) or not statuses
                or any(type(s) is not int or not 100 <= s <= 599 for s in statuses)
                or len(statuses) != len(set(statuses))):
            raise ConfigError("Expected unique HTTP status codes")
    return url


def fingerprint(matrix):
    return hashlib.sha256(json.dumps(matrix, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run(matrix):
    url = validate(matrix)
    # Resolve every credential before issuing any request; never include values in evidence.
    tokens = {}
    for name, actor in matrix["actors"].items():
        env = actor["token_env"]
        token = os.environ.get(env, "") if env else None
        if env and (not token or len(token) > 8192 or any(ord(c) < 33 or ord(c) > 126 for c in token)):
            raise ConfigError("Missing or invalid actor credential")
        tokens[name] = token
    results = []
    for case in matrix["cases"]:
        cls = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
        conn = cls(url.hostname, url.port, timeout=5)
        result = {"id": case["id"], "actor": case["actor"], "expected": case["expect_status"],
                  "actual": None, "outcome": "error"}
        try:
            token = tokens[case["actor"]]
            headers = {"Authorization": "Bearer " + token} if token else {}
            conn.request(case["method"], case["path"], headers=headers)
            response = conn.getresponse()
            result["actual"] = response.status
            result["outcome"] = "pass" if response.status in case["expect_status"] else "fail"
            # Do not read/store response bodies, cookies or headers. Never follow redirects.
        except (OSError, http.client.HTTPException, ValueError):
            result["error"] = "transport_error"
        finally:
            conn.close()
        results.append(result)
    return {"schema_version": 1, "matrix_sha256": fingerprint(matrix),
            "created_at": datetime.now(timezone.utc).isoformat(), "cases": results}


def check_report(report):
    exact(report, ("schema_version", "matrix_sha256", "created_at", "cases"))
    if type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise ConfigError("Unsupported evidence schema")
    if not isinstance(report["matrix_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", report["matrix_sha256"]):
        raise ConfigError("Invalid matrix digest")
    if not isinstance(report["created_at"], str):
        raise ConfigError("Invalid evidence timestamp")
    if not isinstance(report["cases"], list) or not 1 <= len(report["cases"]) <= 200:
        raise ConfigError("Invalid evidence cases")
    seen = set()
    for case in report["cases"]:
        fields = ("id", "actor", "expected", "actual", "outcome")
        exact(case, fields + (("error",) if case.get("outcome") == "error" else ()))
        label(case["id"])
        label(case["actor"])
        if case["id"] in seen:
            raise ConfigError("Duplicate evidence case")
        seen.add(case["id"])
        expected = case["expected"]
        if (not isinstance(expected, list) or not expected or
                any(type(s) is not int or not 100 <= s <= 599 for s in expected)):
            raise ConfigError("Invalid evidence expectation")
        actual = case["actual"]
        if case["outcome"] == "error":
            if actual is not None or case["error"] != "transport_error":
                raise ConfigError("Inconsistent transport evidence")
        elif (type(actual) is not int or not 100 <= actual <= 599 or
              case["outcome"] != ("pass" if actual in expected else "fail")):
            raise ConfigError("Inconsistent evidence outcome")
    return report


def compare(before, after):
    check_report(before)
    check_report(after)
    if before["matrix_sha256"] != after["matrix_sha256"]:
        raise ConfigError("Evidence matrices differ; comparison refused")
    old = {c["id"]: c for c in before["cases"]}
    new = {c["id"]: c for c in after["cases"]}
    if old.keys() != new.keys() or any(
        (old[k]["actor"], old[k]["expected"]) != (new[k]["actor"], new[k]["expected"]) for k in old
    ):
        raise ConfigError("Evidence case definitions differ")
    fixed = [k for k in old if old[k]["outcome"] == "fail" and new[k]["outcome"] == "pass"]
    regressions = [k for k in old if old[k]["outcome"] == "pass" and new[k]["outcome"] != "pass"]
    complete = all(c["outcome"] == "pass" for c in new.values())
    return {"fixed": fixed, "regressions": regressions,
            "proof_of_fix": bool(fixed) and complete, "all_passed": complete}
