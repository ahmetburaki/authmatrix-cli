# Engineering decisions

## 001 — Independent authorization testing tool

Start a standalone repository for developer-focused API authorization regression
checks and proof-of-fix evidence. The project owns its package, CLI, configuration,
CI and release roadmap. AuthMatrix CLI is a provisional name. The first milestone
prioritizes a reliable local workflow and reproducible tests.

## 002 — Standard library and narrow network boundary

Use Python 3.11+, JSON matrices, unittest and http.client. Avoid DNS rebinding by
requiring literal IPs; connect to that same validated IP. Avoid redirects and
implicit proxies. Remote private staging requires normal verified TLS. Restrict
methods to GET/HEAD for the first iteration. Configuration is local trusted input;
operators remain responsible for target permission and endpoint side effects.

## 003 — Minimal, comparable evidence

Persist status observations, generic labels and a canonical configuration digest.
Do not retain response content, endpoints or credentials. Require the source
matrix for offline comparison; reject incomplete coverage, altered definitions,
cross-matrix comparisons and internally contradictory outcomes. A proof-of-fix result requires
an actual failing baseline, passing rerun and passing positive controls as declared
by the operator. Evidence is not signed, and HTTP status alone cannot validate
body-level authorization. Preserve those limits in every release claim.
