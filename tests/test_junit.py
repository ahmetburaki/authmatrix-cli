"""Offline JUnit export with strict evidence coverage and private output."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import xml.etree.ElementTree as ET

from authmatrix.cli import main
from authmatrix.core import ConfigError, fingerprint
from authmatrix.junit import junit_xml


FIXTURES = Path(__file__).parent / "fixtures" / "contracts"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class JUnitTests(unittest.TestCase):
    def test_legacy_and_current_reports(self):
        for name, matrix, failures, errors in (
                ("report-v1.json", "matrix-status.json", 1, 0),
                ("report-v2.json", "matrix-asserted.json", 1, 0),
                ("report-v3-status.json", "matrix-status.json", 0, 0),
                ("report-v3-asserted.json", "matrix-asserted.json", 0, 0),
                ("report-v3-timeout.json", "matrix-asserted.json", 0, 1)):
            with self.subTest(report=name):
                document = junit_xml(fixture(name), fixture(matrix))
                self.assertTrue(document.startswith(b"<?xml"))
                root = ET.fromstring(document)
                self.assertEqual(root.tag, "testsuites")
                suite = root.find("testsuite")
                self.assertEqual(suite.attrib, {
                    "name": "authmatrix", "tests": "1",
                    "failures": str(failures), "errors": str(errors)})
                case = suite.find("testcase")
                self.assertEqual(case.attrib, {
                    "name": "read-resource", "classname": "authmatrix.anonymous"})
                self.assertEqual(len(case.findall("failure")), failures)
                self.assertEqual(len(case.findall("error")), errors)

    def test_json_failure_identifies_failed_assertions(self):
        root = ET.fromstring(junit_xml(fixture("report-v2.json"), fixture("matrix-asserted.json")))
        failure = root.find("./testsuite/testcase/failure")
        self.assertEqual(failure.attrib["type"], "authorization_mismatch")
        self.assertIn("allowed-field", failure.text)
        self.assertNotIn("ok", failure.text)

    def test_every_execution_error_is_visible_as_an_error(self):
        for error in ("transport_error", "response_error", "request_timeout", "run_timeout", "not_run"):
            with self.subTest(error=error):
                report = fixture("report-v3-timeout.json")
                report["cases"][0]["error"] = error
                if error == "response_error":
                    report["cases"][0]["actual"] = 200
                root = ET.fromstring(junit_xml(report, fixture("matrix-asserted.json")))
                case = root.find("./testsuite/testcase")
                self.assertEqual(case.find("error").attrib["type"], error)
                self.assertIsNone(case.find("skipped"))
                self.assertIsNone(case.find("failure"))

    def test_mixed_and_maximum_case_counts(self):
        matrix = fixture("matrix-status.json")
        report = fixture("report-v3-status.json")
        definition, observation = matrix["cases"][0], report["cases"][0]
        matrix["cases"], report["cases"] = [], []
        for index in range(200):
            case, result = copy.deepcopy(definition), copy.deepcopy(observation)
            case["id"] = result["id"] = f"case-{index}"
            if index == 1:
                result.update(outcome="fail", actual=403)
            elif index == 2:
                result.update(outcome="error", actual=None, error="not_run")
            matrix["cases"].append(case)
            report["cases"].append(result)
        report["matrix_sha256"] = fingerprint(matrix)
        root = ET.fromstring(junit_xml(report, matrix))
        suite = root.find("testsuite")
        self.assertEqual(suite.attrib["tests"], "200")
        self.assertEqual(suite.attrib["failures"], "1")
        self.assertEqual(suite.attrib["errors"], "1")
        self.assertEqual(len(suite.findall("testcase")), 200)
        self.assertEqual(len({c.attrib["name"] for c in suite}), 200)

    def test_rejects_incomplete_or_changed_coverage(self):
        baseline = fixture("report-v3-status.json")
        matrix = fixture("matrix-status.json")
        variants = []
        for field, value in (("id", "renamed"), ("actor", "different"),
                             ("expected", [200, 201])):
            report = copy.deepcopy(baseline)
            report["cases"][0][field] = value
            variants.append(report)
        for field, value in (("cases", []), ("matrix_sha256", "0" * 64)):
            report = copy.deepcopy(baseline)
            report[field] = value
            variants.append(report)
        incomplete_matrix = copy.deepcopy(matrix)
        incomplete_matrix["cases"].append(dict(matrix["cases"][0], id="missing"))
        report = copy.deepcopy(baseline)
        report["matrix_sha256"] = fingerprint(incomplete_matrix)
        with self.assertRaises(ConfigError):
            junit_xml(report, incomplete_matrix)
        for report in variants:
            with self.subTest(report=report), self.assertRaises(ConfigError):
                junit_xml(report, matrix)
        matrix["cases"][0]["path"] = "/changed"
        with self.assertRaises(ConfigError):
            junit_xml(baseline, matrix)

    def test_rejects_inconsistent_outcomes_and_assertion_coverage(self):
        for change in ("outcome", "assertion", "missing-assertions", "schema"):
            report = fixture("report-v3-asserted.json")
            if change == "outcome":
                report["cases"][0]["outcome"] = "fail"
            elif change == "assertion":
                report["cases"][0]["assertions"][0]["id"] = "renamed"
            elif change == "missing-assertions":
                del report["cases"][0]["assertions"]
            else:
                report["schema_version"] = 1
                del report["limits"]
            with self.subTest(change=change), self.assertRaises(ConfigError):
                junit_xml(report, fixture("matrix-asserted.json"))

    def test_export_omits_matrix_details_and_arbitrary_timestamp(self):
        matrix = fixture("matrix-asserted.json")
        matrix["actors"]["anonymous"]["token_env"] = "UNREAD_TOKEN"
        matrix["cases"][0]["path"] = "/private-route?query=synthetic-query"
        matrix["cases"][0]["assert_json"][0]["path"] = ["private-field"]
        report = fixture("report-v2.json")
        report["created_at"] = "arbitrary-timestamp-" + chr(0) + "<private>"
        report["matrix_sha256"] = fingerprint(matrix)
        with patch.dict(os.environ, {}, clear=True), patch.object(
                socket.socket, "connect", side_effect=AssertionError("Export must stay offline")):
            document = junit_xml(report, matrix)
        ET.fromstring(document)
        for value in (b"127.0.0.1", b"private-route", b"synthetic-query", b"private-field",
                      b"UNREAD_TOKEN", b"arbitrary-timestamp", b"matrix_sha256"):
            self.assertNotIn(value, document)

    def test_cli_exit_codes_and_exclusive_private_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, matrix, code in (
                    ("report-v3-status.json", "matrix-status.json", 0),
                    ("report-v1.json", "matrix-status.json", 1),
                    ("report-v3-timeout.json", "matrix-asserted.json", 2)):
                output = root / f"{name}.xml"
                args = ["junit", str(FIXTURES / name), "--matrix", str(FIXTURES / matrix),
                        "--output", str(output)]
                with self.subTest(name=name), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(args), code)
                    original = output.read_bytes()
                    ET.fromstring(original)
                    if os.name == "posix":
                        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                    self.assertEqual(main(args), 2)
                    self.assertEqual(output.read_bytes(), original)

    def test_cli_invalid_input_creates_no_output_and_prints_no_details(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence, output = root / "input.json", root / "result.xml"
            for content in ('{"secret": "synthetic-query"}', "null", "not-json"):
                evidence.write_text(content, encoding="utf-8")
                with contextlib.redirect_stdout(io.StringIO()) as console:
                    self.assertEqual(main(["junit", str(evidence), "--matrix",
                                           str(FIXTURES / "matrix-status.json"),
                                           "--output", str(output)]), 2)
                self.assertFalse(output.exists())
                self.assertNotIn("synthetic-query", console.getvalue())
                self.assertNotIn("Traceback", console.getvalue())

    def test_cli_rejects_cross_matrix_report_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.xml"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["junit", str(FIXTURES / "report-v2.json"),
                                       "--matrix", str(FIXTURES / "matrix-status.json"),
                                       "--output", str(output)]), 2)
            self.assertFalse(output.exists())

    def test_concurrent_exports_preserve_the_first_complete_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.xml"
            args = ["junit", str(FIXTURES / "report-v3-status.json"),
                    "--matrix", str(FIXTURES / "matrix-status.json"), "--output", str(output)]
            with contextlib.redirect_stdout(io.StringIO()), ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(main, (args, args)))
            self.assertEqual(sorted(results), [0, 2])
            self.assertEqual(output.read_bytes(), junit_xml(
                fixture("report-v3-status.json"), fixture("matrix-status.json")))

    def test_installed_module_supports_legacy_and_current_cli_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            for report, matrix, code in (
                    ("report-v1.json", "matrix-status.json", 1),
                    ("report-v2.json", "matrix-asserted.json", 1),
                    ("report-v3-status.json", "matrix-status.json", 0),
                    ("report-v3-asserted.json", "matrix-asserted.json", 0),
                    ("report-v3-timeout.json", "matrix-asserted.json", 2)):
                output = Path(directory) / f"{report}.xml"
                result = subprocess.run([
                    sys.executable, "-I", "-m", "authmatrix", "junit",
                    str(FIXTURES / report), "--matrix", str(FIXTURES / matrix),
                    "--output", str(output)], cwd=directory, text=True,
                    capture_output=True, timeout=15)
                with self.subTest(report=report):
                    self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                    ET.parse(output)


if __name__ == "__main__":
    unittest.main()
