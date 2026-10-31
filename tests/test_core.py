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

from authmatrix.cli import main, save
from authmatrix.core import ConfigError, compare, run, validate


class API(BaseHTTPRequestHandler):
    vulnerable = True
    calls = []

    def do_GET(self):
        self.server.calls.append(self.path)
        token = self.headers.get("Authorization")
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://192.0.2.1/secret")
        else:
            self.send_response(401 if not token else
                               200 if token == "Bearer owner-secret" or self.server.vulnerable else 403)
        self.send_header("Set-Cookie", "secret-cookie")
        self.end_headers()
        self.wfile.write(b"private-body")

    def log_message(self, *args):
        pass


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), API)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.server.vulnerable = True
        self.server.calls = []
        self.matrix = {
            "version": 1, "environment": "local",
            "base_url": f"http://127.0.0.1:{self.server.server_port}",
            "actors": {"owner": {"token_env": "OWNER"}, "other": {"token_env": "OTHER"},
                       "anonymous": {"token_env": None}},
            "cases": [
                {"id": "owner", "actor": "owner", "method": "GET", "path": "/resource", "expect_status": [200]},
                {"id": "other", "actor": "other", "method": "GET", "path": "/resource", "expect_status": [403]},
                {"id": "anon", "actor": "anonymous", "method": "GET", "path": "/resource", "expect_status": [401]}]}
        self.env = patch.dict(os.environ, {"OWNER": "owner-secret", "OTHER": "other-secret"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_fix_and_regression(self):
        before = run(self.matrix)
        self.assertEqual([c["outcome"] for c in before["cases"]], ["pass", "fail", "pass"])
        self.server.vulnerable = False
        after = run(self.matrix)
        self.assertTrue(compare(before, after, self.matrix)["proof_of_fix"])
        self.assertEqual(compare(before, after, self.matrix)["fixed"], ["other"])
        self.assertEqual(compare(after, before, self.matrix)["regressions"], ["other"])
        self.assertFalse(compare(after, after, self.matrix)["proof_of_fix"])

    def test_evidence_minimization(self):
        self.matrix["cases"][0]["path"] = "/resource?password=sensitive-query"
        serialized = json.dumps(run(self.matrix))
        for secret in ("owner-secret", "other-secret", "secret-cookie", "private-body",
                       "sensitive-query", "127.0.0.1", "Authorization", "/resource", "OWNER"):
            self.assertNotIn(secret, serialized)

    def test_redirect_not_followed(self):
        self.matrix["cases"][0]["path"] = "/redirect"
        report = run(self.matrix)
        self.assertEqual(report["cases"][0]["actual"], 302)
        self.assertEqual(len(self.server.calls), 3)

    def test_missing_credential_sends_nothing(self):
        with patch.dict(os.environ, {"OTHER": ""}):
            with self.assertRaises(ConfigError):
                run(self.matrix)
        self.assertEqual(self.server.calls, [])

    def test_header_injection_sends_nothing(self):
        with patch.dict(os.environ, {"OTHER": "bad\r\nInjected: true"}):
            with self.assertRaises(ConfigError):
                run(self.matrix)
        self.assertEqual(self.server.calls, [])

    def test_target_boundaries(self):
        for target in ("http://example.com", "http://8.8.8.8", "http://169.254.169.254",
                       "http://100.64.0.1", "http://0.0.0.0", "http://224.0.0.1",
                       "http://127.0.0.1@8.8.8.8", "http://127.0.0.1/a",
                       "http://127.0.0.1?secret=x", "ftp://127.0.0.1", "http://[::ffff:127.0.0.1]",
                       "http://127.0.0.1:0"):
            with self.subTest(target=target):
                self.matrix["base_url"] = target
                with self.assertRaises(ConfigError):
                    validate(self.matrix)

    def test_staging_scope_and_tls(self):
        self.matrix["base_url"] = "https://10.1.2.3:8443"
        with self.assertRaises(ConfigError):
            validate(self.matrix)
        self.matrix["environment"] = "staging"
        validate(self.matrix)
        self.matrix["base_url"] = "http://10.1.2.3"
        with self.assertRaises(ConfigError):
            validate(self.matrix)
        self.matrix["base_url"] = "https://[fd00::1]"
        validate(self.matrix)

    def test_schema_rejections(self):
        edits = [("method", "POST"), ("path", "//example.com"), ("path", "/a\nX: bad"),
                 ("path", "/a#fragment"), ("expect_status", []), ("expect_status", [True]),
                 ("expect_status", [200, 200]), ("actor", "missing"), ("id", "sensitive@example.com")]
        for field, value in edits:
            with self.subTest(field=field, value=value):
                matrix = copy.deepcopy(self.matrix)
                matrix["cases"][0][field] = value
                with self.assertRaises(ConfigError):
                    validate(matrix)
        self.matrix["cases"].append(self.matrix["cases"][0])
        with self.assertRaises(ConfigError):
            validate(self.matrix)

    def test_transport_error_is_not_fix(self):
        with patch("authmatrix.core.http.client.HTTPConnection.request", side_effect=TimeoutError("secret")):
            report = run(self.matrix)
        self.assertTrue(all(c["outcome"] == "error" for c in report["cases"]))
        self.assertNotIn("secret", json.dumps(report))
        self.assertFalse(compare(report, report, self.matrix)["proof_of_fix"])

    def test_compare_refuses_changed_matrix_and_tampering(self):
        before = run(self.matrix)
        after = copy.deepcopy(before)
        after["matrix_sha256"] = "0" * 64
        with self.assertRaises(ConfigError):
            compare(before, after, self.matrix)
        after = copy.deepcopy(before)
        after["cases"].pop()
        with self.assertRaises(ConfigError):
            compare(before, after, self.matrix)
        after = copy.deepcopy(before)
        after["cases"][1]["outcome"] = "pass"
        with self.assertRaises(ConfigError):
            compare(before, after, self.matrix)

    def test_cli_roundtrip_exit_codes_and_file_permissions(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp)
            matrix, before, after = (root / name for name in ("matrix.json", "before.json", "after.json"))
            matrix.write_text(json.dumps(self.matrix))
            self.assertEqual(main(["validate", str(matrix)]), 0)
            self.assertEqual(self.server.calls, [])
            self.assertEqual(main(["run", str(matrix), "--output", str(before)]), 2)
            self.assertFalse(before.exists())
            self.assertEqual(main(["run", str(matrix), "--authorized", "--output", str(before)]), 1)
            if os.name == "posix":
                self.assertEqual(before.stat().st_mode & 0o777, 0o600)
            self.server.vulnerable = False
            self.assertEqual(main(["run", str(matrix), "--authorized", "--output", str(after)]), 0)
            self.assertEqual(main(["compare", str(before), str(after), "--matrix", str(matrix)]), 0)
            self.assertEqual(main(["compare", str(after), str(after), "--matrix", str(matrix)]), 1)
            original = before.read_bytes()
            self.assertEqual(main(["run", str(matrix), "--authorized", "--output", str(before)]), 2)
            self.assertEqual(before.read_bytes(), original)

    def test_compare_rejects_same_missing_case_in_both_reports(self):
        before = run(self.matrix)
        self.server.vulnerable = False
        after = run(self.matrix)
        for report in (before, after):
            report["cases"] = [c for c in report["cases"] if c["id"] != "owner"]
        with self.assertRaises(ConfigError):
            compare(before, after, self.matrix)

    def test_compare_checks_actor_expectation_and_case_against_matrix(self):
        baseline = run(self.matrix)
        self.server.vulnerable = False
        current = run(self.matrix)
        for field, value in (("id", "renamed"), ("actor", "anonymous"), ("expected", [200, 201])):
            with self.subTest(field=field):
                before, after = copy.deepcopy(baseline), copy.deepcopy(current)
                for report in (before, after):
                    report["cases"][0][field] = value
                with self.assertRaises(ConfigError):
                    compare(before, after, self.matrix)

    def test_compare_works_offline_without_credentials(self):
        before = run(self.matrix)
        self.server.vulnerable = False
        after = run(self.matrix)
        with patch.dict(os.environ, {}, clear=True), patch(
            "authmatrix.core.http.client.HTTPConnection.request",
            side_effect=AssertionError("Comparison must not send requests"),
        ):
            self.assertTrue(compare(before, after, self.matrix)["proof_of_fix"])

    def test_compare_rejects_changed_source_matrix(self):
        report = run(self.matrix)
        changed = copy.deepcopy(self.matrix)
        changed["cases"][0]["path"] = "/different-resource"
        with self.assertRaises(ConfigError):
            compare(report, report, changed)

    def test_cli_bad_input_no_traceback_or_secret(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "input.json"
            for value in ("not-json-secret", "null", "[]", '{"base_url": "secret"}'):
                file.write_text(value)
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(main(["validate", str(file)]), 2)
                self.assertNotIn("secret", out.getvalue())


if __name__ == "__main__":
    unittest.main()
