"""CLI with stable exit codes and secret-free error messages."""
import argparse
import json
import os
from pathlib import Path

from .core import ConfigError, compare, run, validate
from .json_checks import strict_json
from .deadlines import DEFAULT_REQUEST_TIMEOUT, DEFAULT_RUN_TIMEOUT


def load(path):
    if Path(path).stat().st_size > 1_000_000:
        raise ConfigError("Input exceeds 1 MB")
    return strict_json(Path(path).read_text(encoding="utf-8"))


def save(path, report):
    # Exclusive creation prevents destroying earlier evidence; owner-only permissions.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        json.dump(report, out, indent=2)
        out.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="authmatrix")
    sub = parser.add_subparsers(dest="command", required=True)
    lint = sub.add_parser("validate", help="Validate a matrix without network access")
    lint.add_argument("matrix")
    execute = sub.add_parser("run")
    execute.add_argument("matrix")
    execute.add_argument("--authorized", action="store_true", help="Confirm permission for this target")
    execute.add_argument("--output", required=True)
    execute.add_argument("--request-timeout", type=float, default=DEFAULT_REQUEST_TIMEOUT,
                         help="Wall-clock seconds per request (default: 10; maximum: 3600)")
    execute.add_argument("--run-timeout", type=float, default=DEFAULT_RUN_TIMEOUT,
                         help="Wall-clock seconds for the run (default: 120; maximum: 3600)")
    diff = sub.add_parser("compare")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.add_argument("--matrix", required=True, help="Source matrix used by both runs")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            validate(load(args.matrix))
            print("Matrix valid (no requests sent)")
            return 0
        if args.command == "run":
            if not args.authorized:
                raise ConfigError("Explicit --authorized confirmation is required")
            if Path(args.output).exists():
                raise ConfigError("Output already exists; choose a new evidence path")
            report = run(load(args.matrix), request_timeout=args.request_timeout,
                         run_timeout=args.run_timeout)
            save(args.output, report)
            counts = {state: sum(c["outcome"] == state for c in report["cases"])
                      for state in ("pass", "fail", "error")}
            print(json.dumps(counts))
            return 2 if counts["error"] else 1 if counts["fail"] else 0
        result = compare(load(args.before), load(args.after), load(args.matrix))
        print(json.dumps(result))
        return 0 if result["proof_of_fix"] else 1
    except (ConfigError, OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        # Do not echo user inputs, URL, credentials, HTTP headers or exception details.
        print("Input, target, credential or evidence error; check documentation and configuration")
        return 2
