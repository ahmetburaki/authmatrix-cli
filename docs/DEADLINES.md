# Request and run deadlines

Every `run()` call now applies monotonic absolute deadlines. Defaults are 10
seconds per request and 120 seconds per run, in addition to the existing
five-second socket inactivity timeout. The earlier limit wins.

```sh
python3 -m authmatrix run examples/tenant-matrix.json --authorized \
  --output evidence/deadline-run.json --request-timeout 3 --run-timeout 30
```

Direct callers use `run(matrix, request_timeout=3, run_timeout=30)`. Each value
must be a finite number greater than zero and at most 3600 seconds. Booleans,
zero, negative values, NaN and infinity cannot disable the protection. The
network/authorization matrix itself is unchanged, so existing matrix files work.

## What the limits cover

The request allowance covers TCP connection, TLS handshake, sending request
headers, reading status/headers, optional JSON body reads, chunk sizes/extensions
and trailers. The remaining allowance is recomputed at every raw socket receive,
including responses whose sockets have been detached from the HTTP connection.
TCP and TLS use the remaining allowance rather than each receiving a fresh full
budget. Completion checks reject observations that finish after their deadline.
If a socket timer fires just before the monotonic clock reaches its limit, the
error keeps the request/run limit that supplied that operation's allowance.
An exhausted run allowance prevents subsequent requests even in that interval.

No signal alarms, background cancellation threads, retries or TLS bypasses are
introduced. HTTPS continues through the standard verified TLS implementation.
Status-only cases still do not read response bodies; asserted body bytes and JSON
limits remain unchanged. A silent peer may hit the five-second inactivity limit
before the ten-second request deadline; that remains a transport error.

The run clock begins inside `run`, before matrix validation and credential
preflight. Those checks consume its allowance, and all credentials are still
validated before any network request. Input-file loading and output-file writing
are outside that clock. Local validation, bounded JSON evaluation, result
serialization and OS scheduling are not preempted; these are network execution
budgets, not hard real-time guarantees for the entire process.

## Outcomes and continuation

| Error code | Meaning | Later cases |
| --- | --- | --- |
| `request_timeout` | Active case exhausted its request allowance | Continue if run time remains |
| `run_timeout` | Active case exhausted the shared run allowance | No more requests |
| `not_run` | Case was not started because run time was exhausted | No request sent for this case |
| `transport_error` | Other network failure or inactivity timeout | Continue if run time remains |
| `response_error` | Invalid asserted JSON response | Continue if run time remains |

A timeout records `outcome=error`, `actual=null`, and error outcomes for all of
that case's assertions. An incomplete observation does not retain an HTTP status
as a completed result. Previously completed cases keep their observations. Every
unstarted case is retained with `not_run`, preserving full matrix coverage.
The CLI still writes the minimized report exclusively and exits 2 if any case has
an error. An incomplete/error case never contributes a fail-to-pass fix.

## Evidence schema 3 and compatibility

New runs emit schema 3 with a `limits` object containing `request_seconds` and
`run_seconds`. It adds the three explicit deadline/not-run codes above without
changing generic case/actor/assertion labels or retaining raw response content.

The new reader accepts legacy schema 1 status-only and schema 2 JSON-asserted
reports with unchanged source matrices. It can compare either legacy version
with schema 3, or two schema-3 reports, while preserving complete matrix and
assertion coverage checks. Older installed readers cannot read schema 3 and must
be upgraded. Limits describe execution conditions and are not part of the matrix
digest; changing a timeout cannot turn an error baseline into a demonstrated fix.
Evidence remains unsigned local regression data rather than independent attestation.

## Regression coverage

The original slow-header trigger took about 0.67 seconds and was recorded as a
passing HTTP observation with no elapsed bound. With a 0.15-second allowance,
synthetic slow status, header, fixed-length/close-delimited JSON, chunk-size and
trailer fixtures terminate with deadline errors. Tests also cover TLS handshake
stalling, verified HTTPS success, TLS verification rejection, remaining allowance
between TCP/TLS, HEAD/status-only requests, continuation, full run exhaustion,
partial evidence, invalid budgets, legacy comparisons and non-main-thread use.

Tests generate a disposable self-signed loopback certificate/key using OpenSSL
and remove them afterward. No private TLS key is committed, and the fixture is
trusted only by its test-specific verified client context. Running the test suite
requires an OpenSSL executable; the installed CLI has no such runtime dependency.
