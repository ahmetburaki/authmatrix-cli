"""Synthetic integration tests for same-status leaks and evidence privacy."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from authmatrix.cli import main
from authmatrix.core import ConfigError, check_report, compare, run, validate
from authmatrix.json_checks import MAX_BODY_BYTES, evaluate


class JSONAPI(BaseHTTPRequestHandler):
    def do_GET(self):
        mode = self.server.mode
        self.server.calls += 1
        private = {"private_email": "synthetic-private@example.invalid"}
        document = {"profile": {"display_name": "demo", "nullable": None}, "items": [{"tenant": "demo-a"}]}
        if self.headers.get("Authorization") == "Bearer synthetic-owner" or self.server.vulnerable:
            document["profile"].update(private)
        body = json.dumps(document).encode()
        media, encoding = "application/json; charset=utf-8", "identity"
        if mode == "invalid":
            body = b'{"secret-field":"private-value"'
        elif mode == "duplicate":
            body = b'{"profile":{"private_email":"private-value"},"profile":{}}'
        elif mode == "oversized":
            body = b'{"padding":"' + b'x' * MAX_BODY_BYTES + b'"}'
        elif mode == "boundary":
            body = b'{"profile":{}}' + b' ' * (MAX_BODY_BYTES - len(b'{"profile":{}}'))
        elif mode == "utf8":
            body = b'{"profile":"\xff"}'
        elif mode == "nan":
            body = b'{"profile":{},"x":NaN}'
        elif mode == "overflow":
            body = b'{"profile":{},"x":1e999}'
        elif mode == "deep":
            body = b'[' * 2000 + b']' * 2000
        elif mode == "wrong_shape":
            body = b'{"profile":null}'
        elif mode == "empty":
            body = b''
        elif mode == "non_json":
            media = "text/html"
        elif mode == "compressed":
            encoding = "gzip"
        elif mode == "problem_json":
            media = "application/problem+json"
        elif mode == "oversized_chunked":
            body = b' ' * (MAX_BODY_BYTES + 1)
        self.send_response(200 if mode != "wrong_status" else 403)
        self.send_header("Content-Type", media)
        self.send_header("Content-Encoding", encoding)
        if mode in ("chunked", "oversized_chunked", "truncated_chunked"):
            self.send_header("Transfer-Encoding", "chunked")
            body = f"{len(body):x}\r\n".encode() + body + b'\r\n'
            if mode != "truncated_chunked":
                body += b'0\r\n\r\n'
        elif mode != "no_length":
            self.send_header("Content-Length", str(len(body) + (10 if mode == "truncated" else 0)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class JSONChecksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), JSONAPI)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.server.vulnerable = True
        self.server.mode = "normal"
        self.server.calls = 0
        self.matrix = {"version": 1, "environment": "local",
                       "base_url": f"http://127.0.0.1:{self.server.server_port}",
                       "actors": {"owner": {"token_env": "JSON_OWNER"}, "other": {"token_env": "JSON_OTHER"}},
                       "cases": [
                           {"id": "owner", "actor": "owner", "method": "GET", "path": "/profile", "expect_status": [200],
                            "assert_json": [{"id": "own-field", "path": ["profile", "private_email"], "op": "present"}]},
                           {"id": "other", "actor": "other", "method": "GET", "path": "/profile", "expect_status": [200],
                            "assert_json": [{"id": "restricted-field", "path": ["profile", "private_email"], "op": "absent"}]}]}
        self.env = patch.dict(os.environ, {"JSON_OWNER": "synthetic-owner", "JSON_OTHER": "synthetic-other"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def other_only(self):
        self.matrix["cases"] = [self.matrix["cases"][1]]

    def test_same_status_leak_fails_then_fix_and_regression(self):
        before = run(self.matrix)
        self.server.vulnerable = False
        after = run(self.matrix)
        self.assertEqual(before["schema_version"], 3)
        self.assertEqual([c["actual"] for c in before["cases"]], [200, 200])
        self.assertEqual([c["actual"] for c in after["cases"]], [200, 200])
        self.assertEqual(before["cases"][1]["outcome"], "fail")
        self.assertEqual(compare(before, after, self.matrix)["fixed"], ["other"])
        self.assertTrue(compare(before, after, self.matrix)["proof_of_fix"])
        self.assertEqual(compare(after, before, self.matrix)["regressions"], ["other"])

    def test_missing_is_distinct_from_null_and_wrong_shape(self):
        self.assertEqual(evaluate({"x": None}, [{"id": "a", "op": "present", "path": ["x"]}])[0]["outcome"], "pass")
        self.assertEqual(evaluate({"x": None}, [{"id": "a", "op": "absent", "path": ["x"]}])[0]["outcome"], "fail")
        self.assertEqual(evaluate({}, [{"id": "a", "op": "absent", "path": ["x", "y"]}])[0]["outcome"], "pass")
        for document in ({"x": None}, {"x": []}, None):
            self.assertEqual(evaluate(document, [{"id": "a", "op": "absent", "path": ["x", "y"]}])[0]["outcome"], "fail")

    def test_arrays_and_type_strict_scalar_equality(self):
        checks = [{"id": "a", "path": ["items", 0, "tenant"], "op": "equals", "value": "demo-a"}]
        self.assertEqual(evaluate({"items": [{"tenant": "demo-a"}]}, checks)[0]["outcome"], "pass")
        for actual, expected, outcome in ((True, 1, "fail"), (1, 1.0, "fail"), (None, None, "pass"), ("a", "b", "fail")):
            check = {"id": "a", "path": ["x"], "op": "equals", "value": expected}
            self.assertEqual(evaluate({"x": actual}, [check])[0]["outcome"], outcome)
        self.assertEqual(evaluate({"items": []}, checks)[0]["outcome"], "fail")

    def test_invalid_bodies_never_pass_or_prove_fix(self):
        self.other_only()
        before = run(self.matrix)
        self.server.vulnerable = False
        for mode in ("invalid", "duplicate", "oversized", "utf8", "nan", "overflow", "deep", "empty",
                     "non_json", "compressed", "truncated", "truncated_chunked", "oversized_chunked"):
            with self.subTest(mode=mode):
                self.server.mode = mode
                report = run(self.matrix)
                self.assertEqual(report["cases"][0]["outcome"], "error")
                self.assertEqual(report["cases"][0]["error"], "response_error")
                self.assertEqual(report["cases"][0]["actual"], 200)
                check_report(report)
                self.assertFalse(compare(before, report, self.matrix)["proof_of_fix"])

    def test_boundary_missing_length_and_json_subtype(self):
        self.other_only()
        self.server.vulnerable = False
        for mode in ("boundary", "no_length", "problem_json", "chunked"):
            with self.subTest(mode=mode):
                self.server.mode = mode
                self.assertEqual(run(self.matrix)["cases"][0]["outcome"], "pass")

    def test_wrong_status_or_shape_cannot_pass(self):
        self.other_only()
        self.server.vulnerable = False
        for mode in ("wrong_status", "wrong_shape"):
            self.server.mode = mode
            report = run(self.matrix)
            self.assertEqual(report["cases"][0]["outcome"], "fail")
            check_report(report)

    def test_reads_are_bounded_and_status_only_never_reads(self):
        self.other_only()
        with patch("authmatrix.json_checks.http.client.HTTPResponse.read", return_value=b'{}') as read:
            run(self.matrix)
        read.assert_called_once_with(MAX_BODY_BYTES + 1)
        del self.matrix["cases"][0]["assert_json"]
        with patch("authmatrix.json_checks.http.client.HTTPResponse.read", side_effect=AssertionError("Unexpected body read")):
            report = run(self.matrix)
        self.assertEqual(report["schema_version"], 3)
        self.assertNotIn("assertions", report["cases"][0])

    def test_assertion_schema_rejected_before_requests(self):
        original = self.matrix["cases"][0]["assert_json"][0]
        invalid = [None, [], [original] * 2, [original] * 33,
                   [{**original, "op": "script"}], [{**original, "value": "extra"}],
                   [{**original, "path": []}], [{**original, "path": [True]}],
                   [{**original, "path": [-1]}], [{**original, "path": ["x"] * 17}],
                   [{**original, "op": "equals"}],
                   [{**original, "op": "equals", "value": {}}],
                   [{**original, "op": "equals", "value": float('nan')}]]
        for checks in invalid:
            with self.subTest(checks=checks):
                matrix = copy.deepcopy(self.matrix)
                matrix["cases"][0]["assert_json"] = checks
                with self.assertRaises(ConfigError):
                    run(matrix)
        self.matrix["cases"][0]["method"] = "HEAD"
        with self.assertRaises(ConfigError):
            validate(self.matrix)
        self.assertEqual(self.server.calls, 0)

    def test_evidence_covers_assertions_and_rejects_contradictions(self):
        before = run(self.matrix)
        self.server.vulnerable = False
        after = run(self.matrix)
        for change in ("missing", "renamed", "downgrade", "false-pass"):
            with self.subTest(change=change):
                old, new = copy.deepcopy(before), copy.deepcopy(after)
                for report in (old, new):
                    if change == "missing":
                        del report["cases"][0]["assertions"]
                    elif change == "renamed":
                        report["cases"][0]["assertions"][0]["id"] = "renamed"
                    elif change == "downgrade":
                        report["schema_version"] = 1
                    else:
                        report["cases"][1]["outcome"] = "pass"
                with self.assertRaises(ConfigError):
                    compare(old, new, self.matrix)

    def test_transport_failure_is_valid_minimal_error_evidence(self):
        with patch("authmatrix.core.http.client.HTTPConnection.request", side_effect=TimeoutError("secret")):
            report = run(self.matrix)
        check_report(report)
        self.assertFalse(compare(report, report, self.matrix)["proof_of_fix"])
        self.assertNotIn("secret", json.dumps(report))

    def test_scalar_expectation_and_observation_never_enter_evidence(self):
        self.other_only()
        self.matrix["cases"][0]["assert_json"] = [
            {"id": "value-check", "op": "equals", "path": ["profile", "private_email"],
             "value": "unique-private-expectation"}]
        report = run(self.matrix)
        self.assertEqual(report["cases"][0]["outcome"], "fail")
        check_report(report)
        serialized = json.dumps(report)
        for secret in ("unique-private-expectation", "private_email", "synthetic-private@example.invalid"):
            self.assertNotIn(secret, serialized)

    def test_compare_rejects_omitted_assertion_even_with_consistent_outcomes(self):
        self.other_only()
        self.matrix["cases"][0]["assert_json"].insert(
            0, {"id": "public-view", "path": ["profile", "display_name"], "op": "present"})
        before = run(self.matrix)
        self.server.vulnerable = False
        after = run(self.matrix)
        for report in (before, after):
            report["cases"][0]["assertions"].pop(0)
        with self.assertRaises(ConfigError):
            compare(before, after, self.matrix)

    def test_cli_roundtrip_sanitizes_fields_values_and_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            matrix, before, after = [root / name for name in ("matrix.json", "before.json", "after.json")]
            matrix.write_text(json.dumps(self.matrix))
            with contextlib.redirect_stdout(io.StringIO()) as console:
                self.assertEqual(main(["run", str(matrix), "--authorized", "--output", str(before)]), 1)
                self.server.vulnerable = False
                self.assertEqual(main(["run", str(matrix), "--authorized", "--output", str(after)]), 0)
                self.assertEqual(main(["compare", str(before), str(after), "--matrix", str(matrix)]), 0)
            combined = before.read_text() + after.read_text() + console.getvalue()
            for secret in ("private_email", "profile", "synthetic-private@example.invalid", "synthetic-owner", "/profile"):
                self.assertNotIn(secret, combined)
            # Parser diagnostics from malformed JSON must never reach stdout/evidence.
            self.server.mode = "invalid"
            with contextlib.redirect_stdout(io.StringIO()) as console:
                self.assertEqual(main(["run", str(matrix), "--authorized", "--output", str(root / 'error.json')]), 2)
            self.assertNotIn("private-value", console.getvalue() + (root / 'error.json').read_text())

    def test_cli_rejects_ambiguous_input_json(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            file = Path(temp) / 'matrix.json'
            for text in ('{"version":1,"version":1}', '{"value":NaN}', '{"value":1e999}'):
                file.write_text(text)
                self.assertEqual(main(["validate", str(file)]), 2)


if __name__ == "__main__":
    unittest.main()
