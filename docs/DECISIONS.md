# Engineering decisions

## 001 — Independent authorization testing tool

Start a standalone repository for developer-focused API authorization regression
checks and proof-of-fix evidence. The project owns its package, CLI, configuration,
CI and release workflow. AuthMatrix CLI is a provisional name. The first milestone
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

## 004 — Explicit JSON assertions with bounded evidence

Allow opt-in presence, absence and type-strict scalar equality checks on GET
responses. Use literal key/index paths rather than an expression language. Bound
body reads to 64 KiB plus one sentinel and reject ambiguous/invalid JSON. Preserve
status-only version-1 evidence; use schema 2 when assertions are configured. Store
only generic assertion IDs and outcomes, and require complete source-matrix
coverage during offline comparison. Invalid response bodies are errors, never
passing fixes. Wall-clock deadlines remain a separate operational change.

## 005 — Absolute network execution deadlines

Apply monotonic request/run budgets at TCP/TLS/send and each raw response read,
including HTTP framing and detached close-delimited response sockets. Preserve
standard verified TLS and HTTP parsing. Avoid signals and background cancellation
threads to support ordinary Windows and non-main-thread Python callers.

New evidence is schema 3 with explicit timeout/not-run errors and limit metadata.
Accept old schema 1/2 reports for offline comparison with unchanged matrices.
Keep prior completed observations; after run exhaustion send no more requests.
See [deadline contract](DEADLINES.md) and [acceptance](DEADLINE_VALIDATION.md).

## 006 — Bundled structural contracts with runtime semantic validation

Ship self-contained JSON Schema 2020-12 matrix/evidence assets inside the Python
package, with offline CLI exports and a pinned test-only validator. Preserve the
dependency-free runtime and legacy evidence versions. Do not duplicate IP/origin
validation or source-matrix comparison in JSON Schema: retain those authoritative
runtime checks and test/document structural acceptance gaps explicitly.

Fixed synthetic compatibility fixtures and installed-package export checks guard
against schema drift and missing wheel assets. See [schemas](SCHEMAS.md).

## 007 — Explicit staging hostname pins with verified identity

Add matrix version 2 for a canonical staging HTTPS hostname plus a required
loopback/private numeric pin. Bypass DNS entirely for that transport while keeping
the hostname in standard TLS SNI/identity checks and HTTP Host. Preserve version-1
IP origins, generic evidence and existing deadlines. An optional CA file supplies
trust roots through a verified default context; no insecure mode is added.

Snapshot the matrix before validation so target, cases and report digest refer to
one configuration. The pin is included in the digest and changing it prevents
comparison. CA-file paths remain execution input and are not retained in evidence.
See [hostname contract](HOSTNAMES.md) and [acceptance](HOSTNAME_VALIDATION.md).
