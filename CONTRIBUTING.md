# Contributing

Use English in repository source, documentation, issues and commit messages.
Keep changes small enough to review. Include the problem, resulting behavior and
relevant verification in PRs. Run `python3 -m unittest discover -s tests -v` and
`python3 -m authmatrix validate examples/matrix.json` before proposing changes. The TLS regression tests require an OpenSSL executable
to generate disposable loopback certificates; the CLI itself has no OpenSSL command dependency.

Use only synthetic local fixtures in tests and CI. Never include real credentials,
private API paths, response contents or evidence from real systems. Do not contact
external targets. A regression test must distinguish the faulty and corrected
behavior. Consult docs/ROADMAP.md for commit-sized work and acceptance criteria.

This starter has no selected distribution license yet. Choose one before public
release; do not infer an open-source license from repository visibility.
