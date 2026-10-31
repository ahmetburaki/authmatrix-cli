"""Offline schema contracts, legacy compatibility and installed package assets."""
import contextlib
import copy
import io
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from jsonschema import Draft202012Validator
from referencing import Registry

from authmatrix.cli import main
from authmatrix.contracts import get_schema
from authmatrix.core import ConfigError, check_report, compare, run, validate
from authmatrix.json_checks import strict_json


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "contracts"


def fixture(name):
    return strict_json((FIXTURES / name).read_text(encoding="utf-8"))


def edited(document, path, value):
    result = copy.deepcopy(document)
    target = result
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    return result


class ContractAPI(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{' if self.server.invalid else b'{"ok":true}'
        self.send_response(self.server.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The empty registry has no remote retrieval callback.
        cls.validators = {
            name: Draft202012Validator(get_schema(name), registry=Registry())
            for name in ("matrix", "evidence")
        }

    def test_schemas_are_valid_self_contained_and_offline(self):
        with patch.object(socket, "create_connection", side_effect=AssertionError("Network forbidden")):
            for validator in self.validators.values():
                validator.check_schema(validator.schema)
                pending = [validator.schema]
                while pending:
                    item = pending.pop()
                    if isinstance(item, dict):
                        if "$ref" in item:
                            self.assertTrue(item["$ref"].startswith("#/"))
                        pending.extend(item.values())
                    elif isinstance(item, list):
                        pending.extend(item)
            self.validators["matrix"].validate(fixture("matrix-asserted.json"))
            self.validators["evidence"].validate(fixture("report-v3-asserted.json"))

    def test_cli_exports_contracts_without_credentials_or_network(self):
        for name in self.validators:
            with self.subTest(name=name), contextlib.redirect_stdout(io.StringIO()) as console, \
                 patch.object(socket, "create_connection", side_effect=AssertionError("Network forbidden")):
                self.assertEqual(main(["schema", name]), 0)
            self.assertEqual(strict_json(console.getvalue()), get_schema(name))

    def test_installed_exports_match_source_outside_checkout(self):
        # -I and an empty working directory prevent imports from the checkout.
        with tempfile.TemporaryDirectory() as temp:
            for name in self.validators:
                result = subprocess.run(
                    [sys.executable, "-I", "-m", "authmatrix", "schema", name],
                    cwd=temp, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(strict_json(result.stdout), get_schema(name))

    def test_examples_and_fixture_matrices_match_both_validators(self):
        paths = list((ROOT / "examples").glob("*matrix.json")) + list(FIXTURES.glob("matrix-*.json"))
        self.assertEqual(len(paths), 5)
        for path in paths:
            with self.subTest(name=path.name):
                matrix = strict_json(path.read_text(encoding="utf-8"))
                self.validators["matrix"].validate(matrix)
                validate(matrix)

    def test_all_evidence_versions_and_errors_match_both_validators(self):
        paths = list(FIXTURES.glob("report-*.json"))
        self.assertEqual(len(paths), 6)
        for path in paths:
            with self.subTest(name=path.name):
                report = fixture(path.name)
                self.validators["evidence"].validate(report)
                check_report(report)
        for code in ("transport_error", "request_timeout", "run_timeout", "not_run"):
            report = edited(fixture("report-v3-timeout.json"), ("cases", 0, "error"), code)
            self.validators["evidence"].validate(report)
            check_report(report)

    def test_legacy_fixtures_still_prove_fixes_and_reverse_regressions(self):
        for before_name, after_name, matrix_name in (
                ("report-v1.json", "report-v3-status.json", "matrix-status.json"),
                ("report-v2.json", "report-v3-asserted.json", "matrix-asserted.json")):
            with self.subTest(before=before_name):
                before, after, matrix = map(fixture, (before_name, after_name, matrix_name))
                result = compare(before, after, matrix)
                self.assertTrue(result["proof_of_fix"])
                self.assertEqual(result["fixed"], ["read-resource"])
                reverse = compare(after, before, matrix)
                self.assertFalse(reverse["proof_of_fix"])
                self.assertEqual(reverse["regressions"], ["read-resource"])
        timeout = fixture("report-v3-timeout.json")
        self.assertFalse(compare(timeout, fixture("report-v3-asserted.json"),
                                 fixture("matrix-asserted.json"))["proof_of_fix"])

    def test_matrix_shape_errors_are_rejected_by_schema_and_runtime(self):
        matrix = fixture("matrix-asserted.json")
        changes = [
            (("version",), True), (("environment",), "production"),
            (("$schema",), "editor-metadata-is-not-a-matrix-field"),
            (("actors",), {}), (("actors", "anonymous", "token_env"), "1BAD"),
            (("actors", "anonymous", "token"), "synthetic"),
            (("cases",), []), (("cases",), matrix["cases"] * 201),
            (("cases", 0, "id"), "bad\n"), (("cases", 0, "id"), "x" * 65),
            (("cases", 0, "method"), "POST"), (("cases", 0, "method"), "HEAD"),
            (("cases", 0, "path"), "//outside"), (("cases", 0, "path"), "/x\n"),
            (("cases", 0, "path"), "/x#fragment"), (("cases", 0, "path"), "/x\\y"),
            (("cases", 0, "path"), "/非ASCII"), (("cases", 0, "path"), "/" * 2049),
            (("cases", 0, "expect_status"), [True]), (("cases", 0, "expect_status"), [200, 200]),
            (("cases", 0, "assert_json"), []),
            (("cases", 0, "assert_json", 0, "op"), "equals"),
            (("cases", 0, "assert_json", 0, "value"), None),
            (("cases", 0, "assert_json", 0, "path"), [True]),
            (("cases", 0, "assert_json", 0, "path"), [1000001]),
            (("cases", 0, "assert_json", 0, "path"), ["x" * 257]),
        ]
        for path, value in changes:
            with self.subTest(path=path, value=str(value)[:80]):
                invalid = edited(matrix, path, value)
                self.assertFalse(self.validators["matrix"].is_valid(invalid))
                with self.assertRaises(ConfigError):
                    validate(invalid)

    def test_evidence_shape_errors_are_rejected_by_schema_and_runtime(self):
        report = fixture("report-v3-asserted.json")
        changes = [
            (("schema_version",), 4), (("schema_version",), True),
            (("schema_version",), 2), (("raw_body",), "synthetic"),
            (("matrix_sha256",), "a" * 63 + "\n"),
            (("limits",), None), (("limits", "request_seconds"), 0),
            (("limits", "run_seconds"), True), (("limits", "run_seconds"), 3601),
            (("cases", 0, "actual"), True), (("cases", 0, "actual"), None),
            (("cases", 0, "error"), "request_timeout"),
            (("cases", 0, "assertions", 0, "outcome"), "fail"),
        ]
        for path, value in changes:
            with self.subTest(path=path):
                invalid = edited(report, path, value)
                self.assertFalse(self.validators["evidence"].is_valid(invalid))
                with self.assertRaises(ValueError):
                    check_report(invalid)
        for path, value in ((("cases", 0, "actual"), 200),
                            (("cases", 0, "error"), "unknown"),
                            (("cases", 0, "assertions", 0, "outcome"), "pass")):
            invalid = edited(fixture("report-v3-timeout.json"), path, value)
            self.assertFalse(self.validators["evidence"].is_valid(invalid))
            with self.assertRaises(ConfigError):
                check_report(invalid)
        for version in (1, 2):
            legacy_timeout = fixture("report-v3-timeout.json")
            legacy_timeout["schema_version"] = version
            del legacy_timeout["limits"]
            self.assertFalse(self.validators["evidence"].is_valid(legacy_timeout))
            with self.assertRaises(ConfigError):
                check_report(legacy_timeout)
        v1_assertions = fixture("report-v2.json")
        v1_assertions["schema_version"] = 1
        self.assertFalse(self.validators["evidence"].is_valid(v1_assertions))
        with self.assertRaises(ConfigError):
            check_report(v1_assertions)

    def test_schema_acceptance_does_not_replace_runtime_or_matrix_comparison(self):
        matrix = fixture("matrix-asserted.json")
        candidates = [
            edited(matrix, ("base_url",), "http://192.0.2.1"),
            edited(matrix, ("cases", 0, "actor"), "missing"),
            edited(matrix, ("cases",), matrix["cases"] * 2),
            edited(matrix, ("cases", 0, "assert_json"), matrix["cases"][0]["assert_json"] * 2),
            edited(matrix, ("version",), 1.0),
            edited(matrix, ("cases", 0, "assert_json", 0, "path"), [1.0]),
        ]
        for candidate in candidates:
            self.validators["matrix"].validate(candidate)
            with self.assertRaises(ConfigError):
                validate(candidate)
        contradictory = edited(fixture("report-v3-status.json"), ("cases", 0, "actual"), 403)
        self.validators["evidence"].validate(contradictory)
        with self.assertRaises(ConfigError):
            check_report(contradictory)
        for path, value in ((("matrix_sha256",), "0" * 64),
                            (("cases", 0, "id"), "renamed")):
            mismatched = edited(fixture("report-v3-status.json"), path, value)
            self.validators["evidence"].validate(mismatched)
            check_report(mismatched)
            with self.assertRaises(ConfigError):
                compare(mismatched, mismatched, fixture("matrix-status.json"))

    def test_real_run_outputs_match_schema_for_pass_fail_and_errors(self):
        with ThreadingHTTPServer(("127.0.0.1", 0), ContractAPI) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                matrix = fixture("matrix-asserted.json")
                matrix["base_url"] = f"http://127.0.0.1:{server.server_port}"
                for status, invalid, outcome, error in (
                        (200, False, "pass", None), (403, False, "fail", None),
                        (200, True, "error", "response_error")):
                    server.status, server.invalid = status, invalid
                    report = run(matrix)
                    self.validators["evidence"].validate(report)
                    check_report(report)
                    self.assertEqual(report["cases"][0]["outcome"], outcome)
                    self.assertEqual(report["cases"][0].get("error"), error)
                with patch.object(socket, "create_connection", side_effect=TimeoutError):
                    report = run(matrix)
                self.validators["evidence"].validate(report)
                check_report(report)
                self.assertEqual(report["cases"][0]["error"], "transport_error")
            finally:
                server.shutdown()
                worker.join()
