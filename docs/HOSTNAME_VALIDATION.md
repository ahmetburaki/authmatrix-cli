# Pinned hostname acceptance — 2026-11-01

The matrix-v2 staging path separates the validated TCP pin from the verified TLS
and HTTP hostname. Its transport bypasses DNS helpers and snapshots configuration
before execution. Version-1 IP matrices and schema-3 evidence remain supported.
This branch builds on merged PR #8; its main revision
`778500cfb1480c1961cf5fa89c79b7d8e8884b11` passed all eight
[post-merge CI jobs](https://github.com/ahmetburaki/authmatrix-cli/actions/runs/41339041263).

## Local checks

- All 16 hostname tests passed locally on Python 3.14.7, including real IPv4 and
  IPv6 loopback TLS with SNI/Host checks and an explicit temporary CA.
- Public/metadata/ambiguous target settings are rejected before connections.
  DNS lookup helpers and proxy variables cannot change a pinned destination.
- Default rejection of the disposable certificate, wrong CA and wrong hostname
  all produce transport errors before any HTTP credential is sent.
- Invalid/empty/missing CA files and missing credentials send no requests.
- Slow headers, fixed-length/close-delimited bodies and TLS handshakes stop at
  their deadlines. Run exhaustion retains prior passes and skips remaining cases;
  TCP failure/TLS timeout cleanup closes sockets.
- Redirect responses cause no followup request. Evidence omits target identity,
  pins, CA paths, tokens, cookies and body content.
- Changing the pin invalidates comparison; mutating the caller's dictionary during
  a run cannot change its destination or recorded configuration digest.
- The installed CLI runs from outside the checkout and saves valid minimized
  evidence. The TLS-enabled example reproduces cross-owner failure and its fix
  while keeping owner/anonymous positive controls intact.
- All 79 tests passed locally, including the previous 63 tests. Compilation,
  diff checks and 52 local documentation links passed. The old version-1 matrix
  schema, evidence schema and compatibility corpus are unchanged.
- A wheel was installed without dependencies into an environment with neither
  optional validator present. Outside the checkout it completed a verified
  pinned-hostname TLS run, saved minimized evidence, exported both schemas and
  validated all four example matrices.

Tests generate disposable keys in temporary directories; no private keys or real
API observations are committed. IPv6 tests explicitly skip only when the runner
cannot provide an IPv6 loopback listener. No real private network or external API
was tested.

## Hosted acceptance

The initial hosted suite passed all eight Ubuntu/Windows Python 3.11–3.14 jobs,
including the real IPv6 test. GitGuardian then identified a Basic Auth string
in a fabricated proxy URL used only by the no-proxy test. It had no associated
account or service. The fixture now uses a credential-free documentation address,
preserving the proxy-isolation check without hardcoded credential syntax.
The unmerged PR history was replaced after creating a local backup; secret checks
remain enabled. Fresh hosted/security results are pending for the cleaned history.
[PR #9](https://github.com/ahmetburaki/authmatrix-cli/pull/9) targets main directly.

## Commands

```sh
python -m pip install ".[test]"
python -m compileall -q authmatrix tests examples
python -m unittest discover -s tests -p test_hostnames.py -v
python -m unittest discover -s tests -v
authmatrix validate examples/hostname-matrix.json
git diff --check
```

The fixture and transport tests preserve normal TLS verification. Request/run
budgets cover network execution; local work and scheduling are not preempted.
Reports remain unsigned and do not authenticate observations independently.
