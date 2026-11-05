"""Offline JUnit XML from minimized, source-matrix-validated evidence."""
import xml.etree.ElementTree as ET

from .core import check_report_against_matrix


def junit_xml(report, matrix):
    check_report_against_matrix(report, matrix)
    cases = report["cases"]
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite", {
        "name": "authmatrix", "tests": str(len(cases)),
        "failures": str(sum(case["outcome"] == "fail" for case in cases)),
        "errors": str(sum(case["outcome"] == "error" for case in cases))})
    for case in cases:
        node = ET.SubElement(suite, "testcase", {
            "name": case["id"], "classname": f"authmatrix.{case['actor']}"})
        if case["outcome"] == "fail":
            failure = ET.SubElement(node, "failure", {
                "type": "authorization_mismatch",
                "message": "HTTP status or JSON assertion mismatch"})
            failure.text = (f"Expected HTTP statuses {case['expected']}. "
                            f"Observed HTTP status {case['actual']}.")
            failed = [a["id"] for a in case.get("assertions", []) if a["outcome"] == "fail"]
            if failed:
                failure.text += "\nFailed JSON assertions " + ", ".join(failed)
        elif case["outcome"] == "error":
            error = ET.SubElement(node, "error", {
                "type": case["error"], "message": "Authorization check execution error"})
            error.text = case["error"]
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"
