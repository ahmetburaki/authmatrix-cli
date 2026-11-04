"""Validate candidate archives, rebuild the sdist and test an isolated install."""
import argparse
import ast
import configparser
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile

from packaging.requirements import Requirement


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "authmatrix"


def version_from_source(root):
    tree = ast.parse((root / PACKAGE / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, str):
                return value
    raise ValueError("Missing literal package version")


def safe_name(name):
    path = PurePosixPath(name)
    if (path.is_absolute() or ".." in path.parts or "\\" in name
            or any(part.lower() in {".git", ".local-tls", "evidence", "__pycache__"}
                   or part.lower().startswith(".env") for part in path.parts)
            or path.suffix.lower() in {".key", ".pem", ".p12", ".pfx", ".pyc", ".pyo"}):
        raise ValueError(f"Unexpected archive path: {name}")
    return path


def check_metadata(data, expected_version):
    metadata = BytesParser().parsebytes(data)
    if (metadata["Name"] != "authmatrix-cli" or metadata["Version"] != expected_version
            or metadata["Requires-Python"] != ">=3.11"
            or metadata["License-Expression"] != "MIT"
            or "LICENSE" not in metadata.get_all("License-File", [])
            or metadata["Description-Content-Type"] != "text/markdown"):
        raise ValueError("Incomplete or inconsistent distribution metadata")
    for text in metadata.get_all("Requires-Dist", []):
        requirement = Requirement(text)
        if requirement.marker is None or str(requirement.marker) != 'extra == "test"':
            raise ValueError("Unexpected default runtime dependency")


def source_files(root, directory, suffixes):
    return {p.relative_to(root).as_posix() for p in (root / directory).rglob("*")
            if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts}


def inspect_wheel(path, root, version):
    expected = source_files(root, PACKAGE, {".py", ".json"})
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = {entry.filename for entry in entries if not entry.is_dir()}
        if len(names) != sum(not entry.is_dir() for entry in entries):
            raise ValueError("Duplicate wheel member")
        metadata_names = [n for n in names if n.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise ValueError("Expected one wheel metadata directory")
        info = str(PurePosixPath(metadata_names[0]).parent)
        for entry in entries:
            part = safe_name(entry.filename)
            if stat.S_ISLNK(entry.external_attr >> 16) or part.parts[0] not in (PACKAGE, info):
                raise ValueError("Unexpected wheel content")
        if not expected <= names:
            raise ValueError(f"Missing wheel resources: {sorted(expected - names)}")
        if {n for n in names if n.startswith(PACKAGE + "/")} != expected:
            raise ValueError("Unexpected runtime package file")
        check_metadata(archive.read(metadata_names[0]), version)
        if archive.read(f"{info}/licenses/LICENSE") != (root / "LICENSE").read_bytes():
            raise ValueError("Wheel license differs from source")
        entry_points = configparser.ConfigParser()
        entry_points.read_string(archive.read(f"{info}/entry_points.txt").decode())
        if entry_points.get("console_scripts", "authmatrix") != "authmatrix.cli:main":
            raise ValueError("Missing CLI entry point")
        return {name: archive.read(name) for name in expected}


def unpack_sdist(path, root, destination, version):
    expected = {"README.md", "LICENSE", "CHANGELOG.md", "CONTRIBUTING.md",
                "pyproject.toml", "MANIFEST.in", ".gitignore", "requirements/packaging.txt"}
    for directory in (PACKAGE, "tests", "examples", "tools", "docs"):
        expected |= source_files(root, directory, {".py", ".json", ".md"})
    allowed = {PACKAGE, "tests", "examples", "tools", "docs", "requirements",
               "authmatrix_cli.egg-info", "PKG-INFO", "setup.cfg"} | expected
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        roots = {safe_name(m.name).parts[0] for m in members}
        if len(roots) != 1:
            raise ValueError("Expected a single source archive root")
        prefix = roots.pop()
        names = set()
        for member in members:
            parts = safe_name(member.name).parts
            if not (member.isdir() or member.isfile()):
                raise ValueError("Source archive links and devices are unsupported")
            if len(parts) > 1:
                relative = "/".join(parts[1:])
                if parts[1] not in allowed:
                    raise ValueError(f"Unexpected source content: {relative}")
                if member.isfile():
                    if relative in names:
                        raise ValueError("Duplicate source member")
                    names.add(relative)
        if not expected <= names:
            raise ValueError(f"Missing source files: {sorted(expected - names)}")
        # Packaging checks use current Python patches with the standard safe filter.
        archive.extractall(destination, filter="data")
    unpacked = destination / prefix
    check_metadata((unpacked / "PKG-INFO").read_bytes(), version)
    if (unpacked / "LICENSE").read_bytes() != (root / "LICENSE").read_bytes():
        raise ValueError("Source archive license differs from checkout")
    return unpacked


def execute(arguments, *, cwd, timeout=300):
    process = subprocess.run([str(a) for a in arguments], cwd=cwd, text=True,
                             capture_output=True, timeout=timeout)
    if process.returncode:
        raise RuntimeError(f"Distribution check failed:\n{process.stdout[-6000:]}\n{process.stderr[-6000:]}")
    return process.stdout


def isolated_smoke(python, wheel, source, empty, version):
    execute([python, "-m", "pip", "install", "--no-index", "--no-deps", wheel], cwd=empty)
    probe = (
        "import importlib.util,importlib.metadata;"
        "assert importlib.util.find_spec('jsonschema') is None;"
        "assert importlib.util.find_spec('referencing') is None;"
        f"assert importlib.metadata.version('authmatrix-cli') == {version!r}")
    execute([python, "-I", "-c", probe], cwd=empty)
    command = [python, "-I", "-m", PACKAGE]
    if execute(command + ["--version"], cwd=empty).strip() != f"authmatrix {version}":
        raise ValueError("CLI and distribution versions differ")
    cli = python.parent / ("authmatrix.exe" if os.name == "nt" else "authmatrix")
    if execute([cli, "--version"], cwd=empty).strip() != f"authmatrix {version}":
        raise ValueError("Installed console entry point failed")
    for kind in ("matrix", "evidence"):
        document = json.loads(execute(command + ["schema", kind], cwd=empty))
        if document["$schema"] != "https://json-schema.org/draft/2020-12/schema":
            raise ValueError("Invalid installed schema export")
    for matrix in sorted((source / "examples").glob("*matrix.json")):
        execute(command + ["validate", matrix], cwd=empty)
    fixtures = source / "tests" / "fixtures" / "contracts"
    for before, after, matrix in (
            ("report-v1.json", "report-v3-status.json", "matrix-status.json"),
            ("report-v2.json", "report-v3-asserted.json", "matrix-asserted.json")):
        result = json.loads(execute(command + ["compare", fixtures / before, fixtures / after,
                                               "--matrix", fixtures / matrix], cwd=empty))
        if result["proof_of_fix"] is not True:
            raise ValueError("Legacy comparison failed after installation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    parser.add_argument("--require-clean", action="store_true",
                        help="Require a clean Git checkout and matching CI revision")
    args = parser.parse_args()
    dist = args.dist.resolve()
    wheels, sdists = sorted(dist.glob("*.whl")), sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("Use a clean dist directory with one wheel and one source archive")
    wheel, sdist = wheels[0], sdists[0]
    version = version_from_source(ROOT)
    payload = inspect_wheel(wheel, ROOT, version)
    with tempfile.TemporaryDirectory(prefix="authmatrix-dist-") as temp:
        workspace = Path(temp)
        source = unpack_sdist(sdist, ROOT, workspace, version)
        rebuilt = workspace / "rebuilt"
        execute([sys.executable, "-m", "build", "--wheel", "--outdir", rebuilt, source], cwd=workspace)
        rebuilt_wheels = list(rebuilt.glob("*.whl"))
        if len(rebuilt_wheels) != 1 or inspect_wheel(rebuilt_wheels[0], source, version) != payload:
            raise ValueError("Rebuilt runtime package differs from the candidate wheel")
        environment, empty = workspace / "venv", workspace / "empty"
        empty.mkdir()
        execute([sys.executable, "-m", "venv", environment], cwd=workspace)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        isolated_smoke(python, rebuilt_wheels[0], source, empty, version)
        # This also checks that examples/tests/fixtures needed by the suite shipped.
        execute([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=source)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                              capture_output=True, check=False).stdout.strip() or None
    state = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True,
                           capture_output=True, check=False)
    if args.require_clean and (revision is None or state.returncode != 0 or state.stdout.strip()
                               or os.environ.get("GITHUB_SHA", revision) != revision):
        raise ValueError("Candidate requires a clean checkout of the expected revision")
    checksums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
                        for p in (wheel, sdist))
    (dist / "SHA256SUMS").write_text(checksums, encoding="utf-8", newline="\n")
    summary = {"version": version, "license": "MIT", "source_revision": revision,
               "working_tree_dirty": bool(state.stdout.strip()) if state.returncode == 0 else None,
               "runtime_payload_rebuilt": True, "isolated_install_without_dependencies": True,
               "legacy_comparisons": 2, "sdist_test_suite": "passed"}
    (dist / "BUILD_INFO.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
