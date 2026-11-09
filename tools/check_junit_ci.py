"""Exercise the installed CLI and render synthetic JUnit results in CI."""
import argparse
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def command(arguments, *, cwd, expected=0, env=None):
    result = subprocess.run(
        [sys.executable, "-I", "-m", "authmatrix", *map(str, arguments)],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
    if result.returncode != expected:
        raise RuntimeError(f"Expected exit {expected}, received {result.returncode}")
    return result.stdout


def report_rows(name, path, expected):
    root = ET.parse(path).getroot()
    suites = root.findall("testsuite")
    if root.tag != "testsuites" or len(suites) != 1:
        raise RuntimeError("Expected one JUnit suite")
    suite = suites[0]
    rows = []
    observed = {}
    for case in suite.findall("testcase"):
        failure, error = case.find("failure"), case.find("error")
        if failure is not None and error is not None:
            raise RuntimeError("Contradictory JUnit result")
        outcome = "error" if error is not None else "fail" if failure is not None else "pass"
        reason = error.attrib["type"] if error is not None else outcome
        key = (case.attrib["classname"], case.attrib["name"])
        if key in observed or case.find("skipped") is not None:
            raise RuntimeError("Unexpected or duplicate JUnit case")
        observed[key] = (outcome, reason)
        rows.append(f"| {name} | {key[0]} | {key[1]} | {reason} |")
    if observed != expected or suite.attrib != {
            "name": "authmatrix", "tests": str(len(expected)),
            "failures": str(sum(value[0] == "fail" for value in expected.values())),
            "errors": str(sum(value[0] == "error" for value in expected.values()))}:
        raise RuntimeError("JUnit cases or counts differ from the expected fixture")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True)
    fixture = runpy.run_path(str(ROOT / "examples" / "local_api.py"))
    matrix = json.loads((ROOT / "examples" / "matrix.json").read_text(encoding="utf-8"))
    environment = dict(os.environ, AUTHMATRIX_OWNER_TOKEN="demo-owner",
                       AUTHMATRIX_OTHER_TOKEN="demo-other")
    rows = []
    with fixture["make_server"](0) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            matrix["base_url"] = f"http://127.0.0.1:{server.server_port}"
            source = output / "matrix.json"
            source.write_text(json.dumps(matrix), encoding="utf-8")
            for scenario, vulnerable, code in (("before", True, 1), ("after", False, 0)):
                fixture["Handler"].vulnerable = vulnerable
                evidence, xml = output / f"{scenario}.json", output / f"{scenario}.xml"
                command(["run", source, "--authorized", "--output", evidence],
                        cwd=output, expected=code, env=environment)
                command(["junit", evidence, "--matrix", source, "--output", xml],
                        cwd=output, expected=code)
                outcome = "fail" if vulnerable else "pass"
                expected = {
                    ("authmatrix.owner", "owner-read"): ("pass", "pass"),
                    ("authmatrix.other", "cross-owner-denied"): (outcome, outcome),
                    ("authmatrix.anonymous", "anonymous-denied"): ("pass", "pass")}
                rows.extend(report_rows(scenario, xml, expected))
            comparison = json.loads(command([
                "compare", output / "before.json", output / "after.json", "--matrix", source],
                cwd=output))
            if comparison != {"fixed": ["cross-owner-denied"], "regressions": [],
                              "proof_of_fix": True, "all_passed": True}:
                raise RuntimeError("The local fixture did not demonstrate the expected fix")
            (output / "comparison.json").write_text(
                json.dumps(comparison, indent=2) + "\n", encoding="utf-8", newline="\n")
        finally:
            server.shutdown()
            worker.join(timeout=5)
    contracts = ROOT / "tests" / "fixtures" / "contracts"
    for scenario, error in (("stored-timeout", "request_timeout"), ("stored-not-run", "not_run")):
        evidence = json.loads((contracts / "report-v3-timeout.json").read_text(encoding="utf-8"))
        evidence["cases"][0]["error"] = error
        source, xml = output / f"{scenario}.json", output / f"{scenario}.xml"
        source.write_text(json.dumps(evidence), encoding="utf-8")
        command(["junit", source, "--matrix", contracts / "matrix-asserted.json",
                 "--output", xml], cwd=output, expected=2)
        rows.extend(report_rows(scenario, xml, {
            ("authmatrix.anonymous", "read-resource"): ("error", error)}))
    summary = (
        "## AuthMatrix synthetic JUnit acceptance\n\n"
        "All four scenarios matched their expected CLI exit codes and XML outcomes. "
        "The vulnerable fixture produced one expected mismatch, and the fixed API "
        "passed all three cases. Comparison confirmed the cross-owner fix.\n\n"
        "The timeout and not-run scenarios use stored synthetic evidence.\n\n"
        "| Scenario | Actor group | Case | Result |\n"
        "| --- | --- | --- | --- |\n" + "\n".join(rows) + "\n")
    (output / "summary.md").write_text(summary, encoding="utf-8", newline="\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8", newline="\n") as target:
            target.write(summary)
    print("Four synthetic JUnit scenarios and proof comparison passed")


if __name__ == "__main__":
    main()
