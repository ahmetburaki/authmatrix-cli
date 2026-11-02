"""Pinned hostname HTTPS tests using disposable, verified loopback peers only."""
import contextlib
import copy
import errno
import io
import json
import os
from pathlib import Path
import shutil
import socket
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from jsonschema import Draft202012Validator
from referencing import Registry

from authmatrix.cli import main
from authmatrix.contracts import get_schema
from authmatrix.core import ConfigError, check_report, compare, fingerprint, run, validate


NAME = "staging.example.invalid"
TOKEN = "synthetic-staging-token"


class API(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append((self.path, self.headers.get("Host"),
                                     self.headers.get("Authorization")))
        if self.server.mutate is not None:
            mutate, self.server.mutate = self.server.mutate, None
            mutate()
        body = b'{"ok":true,"padding":"' + b'x' * 40 + b'"}'
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "https://elsewhere.invalid/private")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(self.server.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Set-Cookie", "synthetic-private-cookie")
        try:
            if self.path == "/headers":
                self.flush_headers()
                self.wfile.write(b"X-Slow: ")
                for _ in range(40):
                    self.wfile.write(b"x")
                    self.wfile.flush()
                    time.sleep(0.05)
                self.wfile.write(b"\r\n")
            if self.path != "/close":
                self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command == "HEAD":
                return
            if self.path in ("/slow", "/close"):
                for byte in body:
                    self.wfile.write(bytes([byte]))
                    self.wfile.flush()
                    time.sleep(0.05)
            else:
                self.wfile.write(body)
        except OSError:
            pass

    do_HEAD = do_GET

    def log_message(self, *args):
        pass


class TLSAPI(ThreadingHTTPServer):
    def get_request(self):
        sock, peer = super().get_request()
        try:
            sock.settimeout(2)
            return self.context.wrap_socket(sock, server_side=True), peer
        except BaseException:
            sock.close()
            raise


class TLSIPv6API(TLSAPI):
    address_family = socket.AF_INET6


class StalledHandshake(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(1)
        try:
            while self.request.recv(8192):
                pass
        except OSError:
            pass


class HostnameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        openssl = shutil.which("openssl")
        if openssl is None:
            raise RuntimeError("OpenSSL is required for synthetic hostname TLS tests")
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.fixtures = Path(cls.temp.name)
        for name in ("trusted", "unrelated"):
            subprocess.run(
                [openssl, "req", "-x509", "-newkey", "rsa:2048", "-sha256", "-nodes",
                 "-keyout", str(cls.fixtures / f"{name}.key"),
                 "-out", str(cls.fixtures / f"{name}.crt"), "-days", "1",
                 "-subj", "/CN=AuthMatrix synthetic hostname test only",
                 "-addext", f"subjectAltName=DNS:{NAME},IP:127.0.0.1",
                 "-addext", "basicConstraints=critical,CA:TRUE"],
                check=True, capture_output=True, timeout=15)
        cls.server, cls.worker = cls.start_server(TLSAPI, "127.0.0.1")
        cls.schema = Draft202012Validator(get_schema("matrix"), registry=Registry())

    @classmethod
    def start_server(cls, server_type, host):
        server = server_type((host, 0), API)
        server.requests, server.names = [], []
        server.mutate, server.status = None, 200
        server.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server.context.load_cert_chain(cls.fixtures / "trusted.crt", cls.fixtures / "trusted.key")
        server.context.set_servername_callback(lambda sock, name, context: server.names.append(name))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        return server, worker

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def setUp(self):
        self.server.requests.clear()
        self.server.names.clear()
        self.server.mutate, self.server.status = None, 200
        self.ca = self.fixtures / "trusted.crt"
        self.matrix = {
            "version": 2, "environment": "staging",
            "base_url": f"https://{NAME}:{self.server.server_port}",
            "connect_ip": "127.0.0.1",
            "actors": {"owner": {"token_env": "HOSTNAME_TEST_TOKEN"}},
            "cases": [self.case("first", "/resource")]}
        self.env = patch.dict(os.environ, {"HOSTNAME_TEST_TOKEN": TOKEN})
        self.env.start()
        self.addCleanup(self.env.stop)

    def case(self, name, path):
        return {"id": name, "actor": "owner", "method": "GET", "path": path,
                "expect_status": [200],
                "assert_json": [{"id": "allowed", "op": "equals", "path": ["ok"], "value": True}]}

    def test_validation_accepts_only_explicit_scoped_pins_without_dns(self):
        for pin in ("127.0.0.1", "::1", "10.1.2.3", "172.16.0.1", "172.31.255.255",
                    "192.168.1.1", "fc00::1", "fd00::1"):
            with self.subTest(pin=pin), patch.object(socket, "getaddrinfo", side_effect=AssertionError):
                self.matrix["connect_ip"] = pin
                validate(self.matrix)
                self.schema.validate(self.matrix)
        self.assertEqual(self.server.requests, [])

    def test_invalid_origins_pins_and_version_aliases_send_nothing(self):
        changes = [
            ("version", 1), ("version", 2.0), ("environment", "local"),
            ("base_url", f"http://{NAME}"), ("base_url", f"https://{NAME}."),
            ("base_url", f"https://{NAME.upper()}"),
            ("base_url", f" https://{NAME}"), ("base_url", f"https://{NAME}\n"),
            ("base_url", f"https://{NAME}/path"), ("base_url", f"https://{NAME}?"),
            ("base_url", f"https://{NAME}#"), ("base_url", f"https://user@{NAME}"),
            ("base_url", f"https://{NAME}:0"), ("base_url", f"https://{NAME}:65536"),
            ("base_url", f"https://{NAME}:0443"), ("base_url", f"https://{NAME}:"),
            ("base_url", "https://127.0.0.1"), ("base_url", "https://[::1]"),
            ("base_url", "https://*.example.invalid"), ("base_url", "https://x_y.invalid"),
            ("base_url", "https://x..invalid"), ("base_url", "https://-x.invalid"),
            ("base_url", "https://é.invalid"), ("base_url", "https://x%2einvalid"),
            ("connect_ip", "8.8.8.8"), ("connect_ip", "169.254.169.254"),
            ("connect_ip", "100.64.0.1"), ("connect_ip", "198.18.0.1"),
            ("connect_ip", "0.0.0.0"), ("connect_ip", "224.0.0.1"),
            ("connect_ip", "2001:db8::1"), ("connect_ip", "fe80::1"),
            ("connect_ip", "::"), ("connect_ip", "::ffff:127.0.0.1"),
            ("connect_ip", "fc00::1%lo0"), ("connect_ip", "localhost"),
            ("connect_ip", "127.0.0.1:443"), ("connect_ip", ""), ("connect_ip", None),
            ("connect_ip", True), ("connect_ip", 2130706433)]
        with patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")):
            for key, value in changes:
                with self.subTest(key=key, value=value):
                    matrix = copy.deepcopy(self.matrix)
                    matrix[key] = value
                    with self.assertRaises(ConfigError):
                        run(matrix, ca_file=self.ca)
            missing = copy.deepcopy(self.matrix)
            del missing["connect_ip"]
            with self.assertRaises(ConfigError):
                validate(missing)
        self.assertEqual(self.server.requests, [])

    def test_verified_pin_preserves_sni_host_and_minimized_evidence(self):
        report = run(self.matrix, ca_file=self.ca)
        self.assertEqual(report["cases"][0]["outcome"], "pass")
        self.assertEqual(self.server.names, [NAME])
        self.assertEqual(self.server.requests, [("/resource", f"{NAME}:{self.server.server_port}",
                                                 "Bearer " + TOKEN)])
        check_report(report)
        for private in (NAME, "127.0.0.1", str(self.ca), TOKEN, "HOSTNAME_TEST_TOKEN",
                        "/resource", "synthetic-private-cookie", "padding"):
            self.assertNotIn(private, json.dumps(report))

    def test_dns_and_proxy_changes_cannot_redirect_a_pinned_connection(self):
        with patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden")) as dns, \
             patch.object(socket, "create_connection", side_effect=AssertionError("Resolver helper forbidden")), \
             patch.dict(os.environ, {"HTTPS_PROXY": "http://192.0.2.1:8888",
                                     "ALL_PROXY": "http://192.0.2.2:8888", "NO_PROXY": ""}):
            report = run(self.matrix, ca_file=self.ca)
        self.assertEqual(report["cases"][0]["outcome"], "pass")
        dns.assert_not_called()
        self.assertEqual(len(self.server.requests), 1)
        self.assertNotIn("192.0.2.1", json.dumps(report))

    def test_untrusted_wrong_ca_and_wrong_hostname_fail_before_http_credentials(self):
        for ca_file, host in ((None, NAME), (self.fixtures / "unrelated.crt", NAME),
                              (self.ca, "wrong.example.invalid")):
            with self.subTest(ca_file=ca_file, host=host):
                matrix = copy.deepcopy(self.matrix)
                matrix["base_url"] = f"https://{host}:{self.server.server_port}"
                report = run(matrix, ca_file=ca_file)
                self.assertEqual(report["cases"][0]["error"], "transport_error")
                self.assertEqual(report["cases"][0]["actual"], None)
                self.assertEqual(self.server.requests, [])
                self.assertNotIn(TOKEN, json.dumps(report))

    def test_ca_file_errors_and_credential_preflight_send_nothing(self):
        invalid = self.fixtures / "invalid-ca.pem"
        invalid.write_text("synthetic invalid certificate", encoding="utf-8")
        with patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")):
            for path in ("", self.fixtures / "missing.pem", invalid):
                with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                    run(self.matrix, ca_file=path)
            matrix = copy.deepcopy(self.matrix)
            matrix["version"], matrix["environment"] = 1, "local"
            matrix["base_url"] = "http://127.0.0.1"
            del matrix["connect_ip"]
            with self.assertRaises(ConfigError):
                run(matrix, ca_file=self.ca)
            with patch.dict(os.environ, {"HOSTNAME_TEST_TOKEN": ""}), self.assertRaises(ConfigError):
                run(self.matrix, ca_file=self.ca)
        self.assertEqual(self.server.requests, [])

    def test_redirects_are_observations_without_followup_requests(self):
        case = self.case("redirect", "/redirect")
        del case["assert_json"]
        self.matrix["cases"] = [case]
        report = run(self.matrix, ca_file=self.ca)
        self.assertEqual((report["cases"][0]["actual"], report["cases"][0]["outcome"]), (302, "fail"))
        self.assertEqual(len(self.server.requests), 1)
        self.assertNotIn("elsewhere", json.dumps(report))

    def test_pinned_header_and_body_deadlines_allow_later_cases(self):
        for path in ("/headers", "/slow", "/close"):
            with self.subTest(path=path):
                self.matrix["cases"] = [self.case("slow", path), self.case("fast", "/resource")]
                start = time.monotonic()
                report = run(self.matrix, ca_file=self.ca, request_timeout=0.2, run_timeout=2)
                self.assertLess(time.monotonic() - start, 1)
                self.assertEqual([c.get("error") for c in report["cases"]], ["request_timeout", None])
                self.assertEqual(report["cases"][1]["outcome"], "pass")
                check_report(report)

    def test_pinned_run_deadline_retains_results_and_suppresses_remaining_requests(self):
        self.matrix["cases"] += [self.case("slow", "/close"), self.case("last", "/never")]
        report = run(self.matrix, ca_file=self.ca, request_timeout=2, run_timeout=0.25)
        self.assertEqual([c.get("error") for c in report["cases"]], [None, "run_timeout", "not_run"])
        self.assertEqual([r[0] for r in self.server.requests], ["/resource", "/close"])
        self.assertFalse(compare(report, report, self.matrix)["proof_of_fix"])
        check_report(report)

    def test_pinned_tls_handshake_uses_request_deadline(self):
        with socketserver.ThreadingTCPServer(("127.0.0.1", 0), StalledHandshake) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                self.matrix["base_url"] = f"https://{NAME}:{server.server_address[1]}"
                report = run(self.matrix, ca_file=self.ca, request_timeout=0.15)
                self.assertEqual(report["cases"][0]["error"], "request_timeout")
                check_report(report)
            finally:
                server.shutdown()
                worker.join()

    def test_pin_changes_invalidate_comparison_but_old_matrix_and_ip_tls_still_work(self):
        self.server.status = 403
        before = run(self.matrix, ca_file=self.ca)
        self.server.status = 200
        after = run(self.matrix, ca_file=self.ca)
        self.assertTrue(compare(before, after, self.matrix)["proof_of_fix"])
        changed = copy.deepcopy(self.matrix)
        changed["connect_ip"] = "127.0.0.2"
        with self.assertRaises(ConfigError):
            compare(before, after, changed)
        legacy = copy.deepcopy(self.matrix)
        legacy["version"], legacy["environment"] = 1, "local"
        legacy["base_url"] = f"https://127.0.0.1:{self.server.server_port}"
        del legacy["connect_ip"]
        self.assertEqual(run(legacy, ca_file=self.ca)["cases"][0]["outcome"], "pass")
        legacy["base_url"] = self.matrix["base_url"]
        with self.assertRaises(ConfigError):
            validate(legacy)

    def test_matrix_snapshot_keeps_pin_and_report_digest_stable_during_run(self):
        self.matrix["cases"].append(self.case("second", "/resource"))
        digest = fingerprint(self.matrix)
        self.server.mutate = lambda: self.matrix.update(
            connect_ip="8.8.8.8", base_url="https://changed.example.invalid")
        report = run(self.matrix, ca_file=self.ca)
        self.assertEqual([c["outcome"] for c in report["cases"]], ["pass", "pass"])
        self.assertEqual(report["matrix_sha256"], digest)
        self.assertEqual(self.server.names, [NAME, NAME])
        self.assertEqual(len(self.server.requests), 2)

    def test_installed_cli_saves_private_evidence_and_sanitizes_ca_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = (Path(temp) / name for name in ("matrix.json", "evidence.json"))
            source.write_text(json.dumps(self.matrix), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-I", "-m", "authmatrix", "run", str(source), "--authorized",
                 "--ca-file", str(self.ca), "--output", str(output)], cwd=temp,
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(output.read_text(encoding="utf-8"))
            check_report(report)
            self.assertEqual(report["cases"][0]["outcome"], "pass")
            self.assertNotIn(NAME, output.read_text(encoding="utf-8") + result.stdout)
            failed_output = Path(temp) / "failed.json"
            with contextlib.redirect_stdout(io.StringIO()) as console:
                code = main(["run", str(source), "--authorized", "--ca-file",
                             "synthetic-private-missing-path", "--output", str(failed_output)])
            self.assertEqual(code, 2)
            self.assertFalse(failed_output.exists())
            self.assertNotIn("synthetic-private-missing-path", console.getvalue())

    def test_ipv6_pin_uses_same_verified_hostname(self):
        try:
            server, worker = self.start_server(TLSIPv6API, "::1")
        except OSError as exc:
            if exc.errno not in (errno.EAFNOSUPPORT, errno.EPROTONOSUPPORT, errno.EADDRNOTAVAIL):
                raise
            self.skipTest(f"IPv6 loopback unavailable: {exc.errno}")
        try:
            self.matrix["base_url"] = f"https://{NAME}:{server.server_port}"
            self.matrix["connect_ip"] = "::1"
            with patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS forbidden")):
                report = run(self.matrix, ca_file=self.ca)
            self.assertEqual(report["cases"][0]["outcome"], "pass")
            self.assertEqual(server.names, [NAME])
            self.assertEqual(server.requests[0][1], f"{NAME}:{server.server_port}")
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_pinned_tcp_failure_and_tls_timeout_close_sockets(self):
        with patch.object(socket, "socket") as constructor:
            constructor.return_value.connect.side_effect = OSError("synthetic-sensitive")
            report = run(self.matrix, ca_file=self.ca)
        constructor.return_value.close.assert_called_once()
        self.assertEqual(report["cases"][0]["error"], "transport_error")
        self.assertNotIn("synthetic-sensitive", json.dumps(report))
        context = ssl.create_default_context(cafile=self.ca)
        original, sockets = context.wrap_socket, []
        def wrap(*args, **kwargs):
            sock = original(*args, **kwargs)
            sockets.append(sock)
            return sock
        self.matrix["cases"] = [self.case("slow", "/close")]
        with patch("authmatrix.core.ssl.create_default_context", return_value=context), \
             patch.object(context, "wrap_socket", side_effect=wrap):
            report = run(self.matrix, ca_file=self.ca, request_timeout=0.2)
        self.assertEqual(report["cases"][0]["error"], "request_timeout")
        self.assertTrue(sockets)
        self.assertTrue(all(sock.fileno() == -1 for sock in sockets))

    def test_documented_loopback_tls_fixture_proves_an_authorization_fix(self):
        from examples.local_api import Handler, make_server
        matrix = json.loads((Path(__file__).resolve().parents[1] /
                             "examples/hostname-matrix.json").read_text(encoding="utf-8"))
        with make_server(0, cert_file=self.ca, key_file=self.fixtures / "trusted.key") as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                matrix["base_url"] = f"https://{NAME}:{server.server_port}"
                with patch.dict(os.environ, {"AUTHMATRIX_OWNER_TOKEN": "demo-owner",
                                             "AUTHMATRIX_OTHER_TOKEN": "demo-other"}):
                    with patch.object(Handler, "vulnerable", True):
                        before = run(matrix, ca_file=self.ca)
                    with patch.object(Handler, "vulnerable", False):
                        after = run(matrix, ca_file=self.ca)
                self.assertEqual([c["outcome"] for c in before["cases"]], ["pass", "fail", "pass"])
                self.assertEqual([c["outcome"] for c in after["cases"]], ["pass", "pass", "pass"])
                result = compare(before, after, matrix)
                self.assertTrue(result["proof_of_fix"])
                self.assertEqual(result["fixed"], ["cross-owner-denied"])
            finally:
                server.shutdown()
                worker.join()
