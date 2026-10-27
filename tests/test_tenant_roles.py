"""Run the published tenant matrix against independent synthetic fault modes."""
import contextlib
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from authmatrix.cli import main
from authmatrix.core import check_report, compare, run


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tenant_example", ROOT / "examples/tenant_api.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

# Independent expectations: removing one fixture gate must affect only its cases.
OWNERSHIP_FAILURES = {"a-owner-other", "a-peer-other"}
TENANT_FAILURES = {"a-member-cross-summary", "b-member-cross-summary",
                   "a-admin-cross-document", "b-admin-cross-document",
                   "a-admin-cross-report", "b-admin-cross-report"}
ROLE_FAILURES = {"a-member-admin-denied", "b-member-admin-denied"}
ALL_FAILURES = OWNERSHIP_FAILURES | TENANT_FAILURES | ROLE_FAILURES
FAULT_FAILURES = {"none": set(), "ownership": OWNERSHIP_FAILURES,
                  "tenant": TENANT_FAILURES, "role": ROLE_FAILURES, "all": ALL_FAILURES}
ENV = {"AUTHMATRIX_A_OWNER_TOKEN": "demo-a-owner", "AUTHMATRIX_A_PEER_TOKEN": "demo-a-peer",
       "AUTHMATRIX_A_ADMIN_TOKEN": "demo-a-admin", "AUTHMATRIX_B_OWNER_TOKEN": "demo-b-owner",
       "AUTHMATRIX_B_ADMIN_TOKEN": "demo-b-admin"}


class TenantRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = fixture.make_server(port=0)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def setUp(self):
        self.server.fault = "none"
        self.matrix = json.loads((ROOT / "examples/tenant-matrix.json").read_text())
        self.matrix["base_url"] = f"http://127.0.0.1:{self.server.server_port}"
        self.env = patch.dict(os.environ, ENV)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_fixed_matrix_has_21_passing_cases(self):
        report = run(self.matrix)
        check_report(report)
        self.assertEqual(len(report["cases"]), 21)
        self.assertTrue(all(c["outcome"] == "pass" for c in report["cases"]))
        self.assertEqual(sum(c["actual"] == 200 for c in report["cases"]), 9)
        self.assertEqual(sum(c["actual"] == 403 for c in report["cases"]), 10)
        self.assertEqual(sum(c["actual"] == 401 for c in report["cases"]), 2)

    def test_each_fault_fails_exactly_its_own_cases(self):
        for fault, expected in FAULT_FAILURES.items():
            with self.subTest(fault=fault):
                self.server.fault = fault
                report = run(self.matrix)
                check_report(report)
                failed = {c["id"] for c in report["cases"] if c["outcome"] == "fail"}
                self.assertEqual(failed, expected)
                self.assertFalse(any(c["outcome"] == "error" for c in report["cases"]))
                self.assertTrue(all(c["actual"] == 200 for c in report["cases"] if c["id"] in expected))
                self.assertTrue(all(c["outcome"] == "pass" for c in report["cases"] if c["expected"] == [200]))
                self.assertTrue(all(c["actual"] == 401 for c in report["cases"] if c["actor"] == "anonymous"))

    def test_full_fix_and_reverse_regression(self):
        self.server.fault = "all"
        before = run(self.matrix)
        self.server.fault = "none"
        after = run(self.matrix)
        result = compare(before, after, self.matrix)
        self.assertTrue(result["proof_of_fix"])
        self.assertTrue(result["all_passed"])
        self.assertEqual(set(result["fixed"]), ALL_FAILURES)
        self.assertEqual(result["regressions"], [])
        reverse = compare(after, before, self.matrix)
        self.assertEqual(set(reverse["regressions"]), ALL_FAILURES)
        self.assertFalse(reverse["proof_of_fix"])

    def test_partial_fix_cannot_claim_complete_proof(self):
        self.server.fault = "all"
        before = run(self.matrix)
        self.server.fault = "ownership"
        after = run(self.matrix)
        result = compare(before, after, self.matrix)
        self.assertEqual(set(result["fixed"]), TENANT_FAILURES | ROLE_FAILURES)
        self.assertFalse(result["all_passed"])
        self.assertFalse(result["proof_of_fix"])

    def test_every_denial_has_a_same_resource_positive_control(self):
        definitions = {c["id"]: c for c in self.matrix["cases"]}
        pairs = {
            "a-owner-other": "a-peer-own", "a-peer-other": "a-owner-own",
            "a-member-cross-summary": "b-owner-summary", "b-member-cross-summary": "a-owner-summary",
            "a-admin-cross-document": "b-admin-document", "b-admin-cross-document": "a-admin-document",
            "a-member-admin-denied": "a-admin-report", "b-member-admin-denied": "b-admin-report",
            "a-admin-cross-report": "b-admin-report", "b-admin-cross-report": "a-admin-report",
            "anonymous-document": "a-owner-own", "anonymous-admin": "a-admin-report",
        }
        self.assertEqual(set(pairs), {c["id"] for c in self.matrix["cases"] if c["expect_status"] != [200]})
        for negative, positive in pairs.items():
            with self.subTest(case=negative):
                self.assertEqual(definitions[negative]["path"], definitions[positive]["path"])
                self.assertEqual(definitions[positive]["expect_status"], [200])
                self.assertNotEqual(definitions[negative]["actor"], definitions[positive]["actor"])

    def test_example_is_loopback_only_and_faults_do_not_disable_authentication(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        with self.assertRaises(ValueError):
            fixture.make_server(port=0, fault="unknown")
        self.server.fault = "all"
        for token in (None, "demo-a-owner", "Bearer missing-demo-user", "Basic demo-a-owner"):
            with self.subTest(token=token):
                conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
                try:
                    conn.request("GET", "/documents/a-1", headers={"Authorization": token} if token else {})
                    response = conn.getresponse()
                    self.assertEqual(response.status, 401)
                    response.read()
                finally:
                    conn.close()

    def test_cli_flow_keeps_tokens_and_response_fields_out_of_evidence(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()) as console:
            root = Path(temp)
            source, before, after = [root / (name + '.json') for name in ("matrix", "before", "after")]
            source.write_text(json.dumps(self.matrix))
            self.server.fault = "all"
            self.assertEqual(main(["run", str(source), "--authorized", "--output", str(before)]), 1)
            self.server.fault = "none"
            self.assertEqual(main(["run", str(source), "--authorized", "--output", str(after)]), 0)
            self.assertEqual(main(["compare", str(before), str(after), "--matrix", str(source)]), 0)
            combined = before.read_text() + after.read_text() + console.getvalue()
            for secret in list(ENV.values()) + ["/documents/", "/tenants/", '"tenant":', '"owner":', '"value":']:
                self.assertNotIn(secret, combined)


if __name__ == "__main__":
    unittest.main()
