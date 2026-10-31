"""Bound real loopback slow peers, including TLS and HTTP framing reads."""
import contextlib
import copy
import http.client
import io
import json
from pathlib import Path
import shutil
import socket
import socketserver
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from authmatrix.cli import main
from authmatrix.core import ConfigError, check_report, compare, run
from authmatrix.deadlines import Budget, HTTPConnection, HTTPSConnection


class SlowAPI(BaseHTTPRequestHandler):
    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, BrokenPipeError, ssl.SSLError):
            pass  # Expected peer cancellation in deadline/connection-only tests.

    def trickle(self, data):
        for byte in data:
            self.wfile.write(bytes([byte]))
            self.wfile.flush()
            time.sleep(0.05)

    def do_GET(self):
        self.server.paths.append(self.path)
        body = b'{"ok":true,"padding":"' + b'x' * 40 + b'"}'
        try:
            if self.path == "/status":
                self.trickle(b'HTTP/1.0 200 OK\r\n')
                self.wfile.write(b'Content-Length: 0\r\n\r\n')
                return
            self.wfile.write(b'HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n')
            if self.path == "/headers":
                self.wfile.write(b'X-Slow: ')
                self.trickle(b'x' * 40)
                self.wfile.write(b'\r\n')
            if self.path in ("/chunk-size", "/trailers"):
                self.wfile.write(b'Transfer-Encoding: chunked\r\n\r\n')
                if self.path == "/chunk-size":
                    self.wfile.write(f'{len(body):x};slow='.encode())
                    self.trickle(b'x' * 40)
                    self.wfile.write(b'\r\n' + body + b'\r\n0\r\n\r\n')
                else:
                    self.wfile.write(f'{len(body):x}\r\n'.encode() + body + b'\r\n0\r\nX-Trailer: ')
                    self.trickle(b'x' * 40)
                    self.wfile.write(b'\r\n\r\n')
                return
            if self.path != "/close-body":
                self.wfile.write(f'Content-Length: {len(body)}\r\n'.encode())
            self.wfile.write(b'\r\n')
            if self.command == "HEAD":
                return
            if self.path in ("/body", "/close-body"):
                self.trickle(body)
            else:
                self.wfile.write(body)
        except (OSError, ssl.SSLError):
            pass

    do_HEAD = do_GET

    def log_message(self, *args):
        pass


class TLSAPI(ThreadingHTTPServer):
    def get_request(self):
        sock, address = super().get_request()
        try:
            return self.tls.wrap_socket(sock, server_side=True), address
        except BaseException:
            sock.close()
            raise


class StalledHandshake(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(1)
        try:
            # Consume ClientHello without sending TLS handshake progress.
            while self.request.recv(8192):
                pass
        except OSError:
            pass


class DeadlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate a throwaway trust root/key; no private TLS material is committed.
        openssl = shutil.which("openssl")
        if openssl is None:
            raise RuntimeError("OpenSSL is required for synthetic TLS deadline tests")
        cls.fixture_temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixture_temp.cleanup)
        cls.fixtures = Path(cls.fixture_temp.name)
        subprocess.run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-sha256", "-nodes",
                        "-keyout", str(cls.fixtures / "loopback-test.key"),
                        "-out", str(cls.fixtures / "loopback-test.crt"), "-days", "1",
                        "-subj", "/CN=AuthMatrix synthetic loopback test only",
                        "-addext", "subjectAltName=IP:127.0.0.1",
                        "-addext", "basicConstraints=critical,CA:TRUE"],
                       check=True, capture_output=True, timeout=15)
        cls.servers = []
        cls.workers = []
        for server_type in (ThreadingHTTPServer, TLSAPI):
            server = server_type(("127.0.0.1", 0), SlowAPI)
            server.paths = []
            if server_type is TLSAPI:
                server.tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                server.tls.load_cert_chain(cls.fixtures / 'loopback-test.crt', cls.fixtures / 'loopback-test.key')
            cls.servers.append(server)
        cls.http, cls.https = cls.servers
        for server in cls.servers:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            cls.workers.append(worker)

    @classmethod
    def tearDownClass(cls):
        for server in cls.servers:
            server.shutdown()
            server.server_close()
        for worker in cls.workers:
            worker.join()

    def setUp(self):
        self.http.paths.clear()
        self.https.paths.clear()
        self.matrix = {"version": 1, "environment": "local",
                       "base_url": f'http://127.0.0.1:{self.http.server_port}',
                       "actors": {"anonymous": {"token_env": None}},
                       "cases": [self.case("fast", "/fast")]}

    def case(self, name, path, asserted=True, method="GET"):
        result = {"id": name, "actor": "anonymous", "method": method,
                  "path": path, "expect_status": [200]}
        if asserted:
            result["assert_json"] = [{"id": "ok", "op": "equals", "path": ["ok"], "value": True}]
        return result

    def trust_context(self):
        return ssl.create_default_context(cafile=str(self.fixtures / 'loopback-test.crt'))

    def test_slow_status_headers_body_and_framing_stop_within_request_budget(self):
        for path in ("/status", "/headers", "/body", "/close-body", "/chunk-size", "/trailers"):
            with self.subTest(path=path):
                self.matrix["cases"] = [self.case("slow", path)]
                start = time.monotonic()
                report = run(self.matrix, request_timeout=0.15, run_timeout=3)
                elapsed = time.monotonic() - start
                self.assertLess(elapsed, 0.8)
                self.assertGreaterEqual(elapsed, 0.10)
                case = report["cases"][0]
                self.assertEqual((case["outcome"], case["actual"], case["error"]), ("error", None, "request_timeout"))
                self.assertEqual(case["assertions"], [{"id": "ok", "outcome": "error"}])
                check_report(report)

    def test_head_and_status_only_headers_use_same_deadline(self):
        for method in ("GET", "HEAD"):
            self.matrix["cases"] = [self.case("slow", "/headers", asserted=False, method=method)]
            report = run(self.matrix, request_timeout=0.15)
            self.assertEqual(report["cases"][0]["error"], "request_timeout")
            check_report(report)

    def test_request_timeout_allows_next_case_in_remaining_run_budget(self):
        self.matrix["cases"] = [self.case("slow", "/body"), self.case("fast", "/fast")]
        report = run(self.matrix, request_timeout=0.15, run_timeout=3)
        self.assertEqual([c["outcome"] for c in report["cases"]], ["error", "pass"])
        self.assertEqual(self.http.paths, ["/body", "/fast"])
        check_report(report)

    def test_run_timeout_retains_passes_and_marks_remaining_cases_not_run(self):
        self.matrix["cases"] = [self.case("first", "/fast"), self.case("slow", "/body"),
                                self.case("last", "/never")]
        start = time.monotonic()
        report = run(self.matrix, request_timeout=2, run_timeout=0.25)
        self.assertLess(time.monotonic() - start, 0.8)
        self.assertEqual([c.get("error") for c in report["cases"]], [None, "run_timeout", "not_run"])
        self.assertEqual(report["cases"][0]["outcome"], "pass")
        self.assertEqual(self.http.paths, ["/fast", "/body"])
        check_report(report)
        self.assertFalse(compare(report, report, self.matrix)["proof_of_fix"])

    def test_validation_time_counts_toward_run_budget_without_requests(self):
        from authmatrix.core import validate
        def delayed(matrix):
            time.sleep(0.03)
            return validate(matrix)
        with patch("authmatrix.core.validate", side_effect=delayed):
            report = run(self.matrix, run_timeout=0.01)
        self.assertEqual(report["cases"][0]["error"], "not_run")
        self.assertEqual(self.http.paths, [])
        check_report(report)

    def test_cli_saves_complete_error_evidence_and_exits_two(self):
        self.matrix["cases"] = [self.case("slow", "/body"), self.case("last", "/never")]
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()) as console:
            source, output = [Path(temp) / name for name in ('matrix.json', 'evidence.json')]
            source.write_text(json.dumps(self.matrix))
            result = main(["run", str(source), "--authorized", "--output", str(output),
                           "--run-timeout", "0.15", "--request-timeout", "2"])
            self.assertEqual(result, 2)
            report = json.loads(output.read_text())
            check_report(report)
            self.assertEqual([c["error"] for c in report["cases"]], ["run_timeout", "not_run"])
            self.assertEqual(report["limits"], {"request_seconds": 2.0, "run_seconds": 0.15})
            self.assertNotIn("/body", output.read_text() + console.getvalue())

    def test_verified_https_and_slow_close_delimited_tls_body(self):
        self.matrix["environment"] = "staging"
        self.matrix["base_url"] = f'https://127.0.0.1:{self.https.server_port}'
        context = self.trust_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        with patch("ssl._create_default_https_context", return_value=context):
            self.assertEqual(run(self.matrix)["cases"][0]["outcome"], "pass")
            self.matrix["cases"] = [self.case("slow", "/close-body")]
            start = time.monotonic()
            report = run(self.matrix, request_timeout=0.2)
            self.assertLess(time.monotonic() - start, 0.9)
            self.assertEqual(report["cases"][0]["error"], "request_timeout")
            check_report(report)
        self.matrix["cases"] = [self.case("fast", "/fast")]
        # Without the test trust root, default certificate verification rejects this fixture.
        self.assertEqual(run(self.matrix)["cases"][0]["error"], "transport_error")

    def test_stalled_tls_handshake_respects_same_request_budget(self):
        with socketserver.ThreadingTCPServer(("127.0.0.1", 0), StalledHandshake) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            self.matrix["environment"] = "staging"
            self.matrix["base_url"] = f'https://127.0.0.1:{server.server_address[1]}'
            try:
                start = time.monotonic()
                report = run(self.matrix, request_timeout=0.15)
                self.assertLess(time.monotonic() - start, 0.8)
                self.assertEqual(report["cases"][0]["error"], "request_timeout")
                check_report(report)
            finally:
                server.shutdown()
                worker.join()

    def test_tcp_remaining_allowance_is_recomputed_before_tls(self):
        context = self.trust_context()
        connection = HTTPSConnection("127.0.0.1", self.https.server_port,
                                     budget=Budget(time.monotonic() + 1, time.monotonic() + 2))
        observed = []
        original = context.wrap_socket
        def wrap(sock, **kwargs):
            observed.append(sock.gettimeout())
            return original(sock, **kwargs)
        connection._context = context
        real_connect = socket.create_connection
        def delayed_connect(*args, **kwargs):
            time.sleep(0.08)
            return real_connect(*args, **kwargs)
        try:
            with patch("authmatrix.deadlines.socket.create_connection", side_effect=delayed_connect), patch.object(context, "wrap_socket", side_effect=wrap):
                connection.connect()
            self.assertLess(observed[0], 0.96)
            self.assertGreater(observed[0], 0)
        finally:
            connection.close()

    def test_socket_inactivity_timeout_remains_transport_error(self):
        with patch("authmatrix.deadlines.socket.create_connection", side_effect=TimeoutError("sensitive")):
            report = run(self.matrix)
        self.assertEqual(report["cases"][0]["error"], "transport_error")
        self.assertNotIn("sensitive", json.dumps(report))

    def test_timeout_closes_connection_and_detached_response_descriptors(self):
        real_connect = socket.create_connection
        for secure in (False, True):
            for path in ("/headers", "/close-body"):
                with self.subTest(secure=secure, path=path):
                    sockets = []
                    def connect(*args, **kwargs):
                        sock = real_connect(*args, **kwargs)
                        sockets.append(sock)
                        return sock
                    context = self.trust_context()
                    real_wrap = context.wrap_socket
                    def wrap(*args, **kwargs):
                        sock = real_wrap(*args, **kwargs)
                        sockets.append(sock)
                        return sock
                    self.matrix["base_url"] = (f'https://127.0.0.1:{self.https.server_port}' if secure
                                               else f'http://127.0.0.1:{self.http.server_port}')
                    self.matrix["cases"] = [self.case("slow", path)]
                    with patch("authmatrix.deadlines.socket.create_connection", side_effect=connect), \
                         patch("ssl._create_default_https_context", return_value=context), \
                         patch.object(context, "wrap_socket", side_effect=wrap):
                        report = run(self.matrix, request_timeout=0.2)
                    self.assertEqual(report["cases"][0]["error"], "request_timeout")
                    self.assertTrue(sockets)
                    self.assertTrue(all(sock.fileno() == -1 for sock in sockets))

    def test_legacy_schema_one_and_two_still_compare_with_schema_three(self):
        for asserted, legacy_version in ((False, 1), (True, 2)):
            self.matrix["cases"] = [self.case("fast", "/fast", asserted)]
            current = run(self.matrix)
            old = copy.deepcopy(current)
            old["schema_version"] = legacy_version
            del old["limits"]
            old["cases"][0].update(actual=403, outcome="fail")
            check_report(old)
            self.assertTrue(compare(old, current, self.matrix)["proof_of_fix"])

    def test_deadline_evidence_rejects_false_success_or_observed_status(self):
        self.matrix["cases"] = [self.case("slow", "/body")]
        report = run(self.matrix, request_timeout=0.15)
        for field, value in (("outcome", "pass"), ("actual", 200), ("error", "unknown")):
            changed = copy.deepcopy(report)
            changed["cases"][0][field] = value
            with self.assertRaises(ConfigError):
                check_report(changed)
        no_assertion_error = copy.deepcopy(report)
        no_assertion_error["cases"][0]["assertions"][0]["outcome"] = "pass"
        with self.assertRaises(ConfigError):
            check_report(no_assertion_error)

    def test_invalid_budgets_fail_before_requests(self):
        for value in (True, False, None, 0, -1, float('inf'), float('nan'), 3601, 10 ** 500, "1"):
            for name in ("request_timeout", "run_timeout"):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    run(self.matrix, **{name: value})
        self.assertEqual(self.http.paths, [])

    def test_non_main_thread_repeated_runs_leave_no_deadline_threads(self):
        before = set(threading.enumerate())
        results = []
        def invoke():
            for _ in range(3):
                results.append(run(self.matrix)["cases"][0]["outcome"])
            slow = copy.deepcopy(self.matrix)
            slow["cases"] = [self.case("slow", "/body")]
            results.append(run(slow, request_timeout=0.15)["cases"][0]["outcome"])
        worker = threading.Thread(target=invoke)
        worker.start()
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(results, ["pass"] * 3 + ["error"])
        # Only fixture request threads may briefly remain; no timers/workers are introduced.
        extras = set(threading.enumerate()) - before
        self.assertTrue(all('process_request_thread' in t.name for t in extras))


if __name__ == "__main__":
    unittest.main()
