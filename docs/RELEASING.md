# Preparing and publishing a release

AuthMatrix CLI uses the [MIT license](../LICENSE). Version reporting and
distribution metadata read the single literal `authmatrix.__version__` value.
The software version is independent of matrix versions 1/2 and evidence schema 3.
This procedure separates validated candidate files from an approved release tag.

## Build and validate a candidate

Use a clean checkout and a current Python patch version. Packaging CI uses Python
3.14 on Ubuntu and Windows; the runtime suite covers Python 3.11–3.14.

```sh
python -m pip install ".[test]" -r requirements/packaging.txt
python -m unittest discover -s tests -v
python -m build --sdist --wheel --outdir dist
python -m twine check --strict dist/*.whl dist/*.tar.gz
python tools/check_dist.py dist --require-clean
```

Start with a clean `dist/` directory, or use another empty output directory. The
checker requires exactly one wheel and one source archive. Omit `--require-clean`
only for local work in progress; CI enforces a clean matching source revision.
It verifies:

- Name/version/Python requirement, MIT metadata and license bytes, Markdown readme,
  optional-only dependencies, console entry point and all bundled schema resources.
- Expected source/test/fixture/example/documentation files; reject environment,
  evidence and cache paths, private-key file extensions, unsafe paths and archive links.
- A wheel rebuilt from the extracted source archive has the same runtime payload.
- A new virtual environment installs that wheel without dependency downloads.
  From an empty directory, isolated Python and the installed console script report
  the expected version; schema exports, all example matrix validations and both
  legacy-to-current proof comparisons succeed without optional validators.
- The full test suite also runs from the extracted source archive, checking that
  the release contains the files needed to reproduce the local fixtures.

The checker writes `SHA256SUMS` for the two package files. It uses LF line endings
on both platforms so the same file can be checked on macOS and Linux. It also
writes `BUILD_INFO.json` with version, source revision, dirty-tree state and check
results. A release candidate must be rebuilt from the clean approved source
revision. Use the checksums to verify the downloaded files from that build.

CI uploads both platform candidates after validation with seven-day retention.
They are build artifacts for review, not published releases. No PyPI credentials
or repository-write token is required by the workflow.

## Finalize an approved release

1. Review the candidate PR and all runtime, distribution and secret checks.
2. Replace the candidate heading in CHANGELOG.md with the final version/date,
   review release notes and merge the final release change into main.
3. Wait for all main checks on that exact commit, then rebuild/check its candidate
   archives in a clean checkout. Verify `BUILD_INFO.json` matches that commit and
   reports `working_tree_dirty=false`; retain hashes of the selected files.
4. With the release approved, create and push an annotated version tag on that
   tested main commit. Never move an existing release tag to a different commit.
5. Run the manual CI workflow on the tag reference and verify the same gates.
6. Create a draft GitHub release for the existing tag, attach the checked wheel,
   source archive, checksums and build information, and inspect the draft before
   publishing. Package-index publication requires its own account and explicit plan.

For example, after approval and after replacing the commit placeholder:

```sh
git tag -a v0.1.0 TESTED_MAIN_COMMIT -m "AuthMatrix CLI 0.1.0"
git push origin v0.1.0
gh workflow run ci.yml --ref v0.1.0
```

The commands above are manual release steps, not part of the packaging checker.
The source archive includes examples and tests; the wheel contains the runtime
package and distribution metadata. Tests use synthetic loopback APIs only.

Tooling follows [PyPA build](https://build.pypa.io/en/stable/),
[Twine metadata checks](https://twine.readthedocs.io/en/stable/) and
[standard license metadata](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license-and-license-files).
