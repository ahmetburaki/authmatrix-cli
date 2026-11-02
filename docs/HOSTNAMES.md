# Verified staging hostnames with explicit IP pins

Matrix version 2 supports one explicitly configured staging hostname and a
loopback/private destination IP. It never resolves the hostname. TCP connects
directly to the numeric pin; TLS SNI, certificate verification and HTTP Host use
the configured hostname. DNS changes cannot select a different destination.

```json
{
  "version": 2,
  "environment": "staging",
  "base_url": "https://staging.example.invalid:8443",
  "connect_ip": "127.0.0.1",
  "actors": {"anonymous": {"token_env": null}},
  "cases": [
    {"id": "read", "actor": "anonymous", "method": "GET", "path": "/resource", "expect_status": [200]}
  ]
}
```

The origin is an exact single-host allowlist. Version 2 requires staging HTTPS,
a lowercase ASCII DNS hostname with valid labels, no trailing dot, and an optional
canonical decimal port. Credentials, alternate URL encodings, non-root origin
paths, queries and fragments are rejected. Use version 1 for literal-IP origins;
existing version-1 matrices and legacy evidence comparisons continue to work.

The pin must be loopback, RFC1918 or IPv6 ULA. Public, link-local/metadata,
unspecified, multicast, mapped/scoped IPv6 and hostname pins are rejected. IPv4
and IPv6 pins use their corresponding socket families without getaddrinfo.
Private addressing does not establish permission; use only owned/authorized
local or staging targets. No production targets are supported.

## Trust and execution

System trust is used by default. An explicit PEM CA bundle is available for
verified HTTPS, including existing version-1 HTTPS matrices:

```sh
authmatrix validate examples/hostname-matrix.json
authmatrix run examples/hostname-matrix.json --authorized \
  --ca-file .local-tls/ca.pem --output evidence/staging.json
```

An explicit CA file supplies the trust roots for that run. It must be nonempty,
readable and valid; errors stop the run before network requests. HTTP matrices
cannot use the option. Certificate chain and hostname checks remain required;
there is no TLS verification bypass. These use the standard Python
[verified HTTPS connection](https://docs.python.org/3.11/library/http.client.html#http.client.HTTPSConnection)
and [default client context](https://docs.python.org/3.11/library/ssl.html#ssl.create_default_context).

Credential preflight, GET/HEAD restrictions, redirects/proxies being unused,
JSON read limits and request/run deadlines apply unchanged. CA loading and input
snapshotting consume run time but, like other local work, are not preempted.

The run snapshots the matrix before validation, keeping destination, case
definitions and evidence digest consistent even if the caller later mutates its
original dictionary. The pin is part of the matrix digest: changing it invalidates
before/after comparison. Evidence still uses schema 3 and omits hostname, pin,
CA path, credentials, headers and body. CA trust selection is operator input and
is not included in the matrix digest; evidence remains unsigned regression data.

## Reproduce locally without DNS changes

From the repository root, generate a disposable loopback fixture certificate/key.
The certificate below has the same hostname as the example matrix. The directory
is ignored by Git and the keys are only for this synthetic fixture.

```sh
mkdir -p .local-tls evidence
openssl req -x509 -newkey rsa:2048 -sha256 -nodes \
  -keyout .local-tls/key.pem -out .local-tls/ca.pem -days 1 \
  -subj "/CN=AuthMatrix disposable loopback fixture" \
  -addext "subjectAltName=DNS:staging.example.invalid" \
  -addext "basicConstraints=critical,CA:TRUE"
python3 examples/local_api.py --port 8443 \
  --tls-cert .local-tls/ca.pem --tls-key .local-tls/key.pem --vulnerable
```

In another terminal, use only the synthetic demo credentials:

```sh
export AUTHMATRIX_OWNER_TOKEN=demo-owner
export AUTHMATRIX_OTHER_TOKEN=demo-other
python3 -m authmatrix run examples/hostname-matrix.json --authorized \
  --ca-file .local-tls/ca.pem --output evidence/hostname-before.json
```

Expected exit 1: the cross-owner case receives 200. Stop the fixture and restart
the same TLS command without `--vulnerable`, then run:

```sh
python3 -m authmatrix run examples/hostname-matrix.json --authorized \
  --ca-file .local-tls/ca.pem --output evidence/hostname-after.json
python3 -m authmatrix compare evidence/hostname-before.json \
  evidence/hostname-after.json --matrix examples/hostname-matrix.json
```

Expected: `fixed=["cross-owner-denied"]`, `proof_of_fix=true`, exit 0, with owner
and anonymous controls passing. The fixture binds only to 127.0.0.1; no DNS or
hosts-file edits are involved. `validate` and `compare` need no TLS files or network.
See [acceptance](HOSTNAME_VALIDATION.md) for the tested boundaries.
