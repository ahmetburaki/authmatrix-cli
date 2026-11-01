"""Synthetic loopback-only API. No real accounts or data."""
import argparse
import json
import ssl
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    vulnerable = False

    def do_GET(self):
        body = None
        token = self.headers.get("Authorization", "")
        if self.path not in ("/documents/1", "/profiles/1"):
            status = 404
        else:
            if token not in ("Bearer demo-owner", "Bearer demo-other"):
                status = 401
            elif self.path == "/profiles/1":
                status = 200
                body = {"display_name": "demo"}
                if token == "Bearer demo-owner" or self.vulnerable:
                    body["private_email"] = "synthetic@example.invalid"
            elif token == "Bearer demo-owner" or self.vulnerable:
                status = 200
            else:
                status = 403
        self.send_response(status)
        if body is not None:
            body = json.dumps(body).encode()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body is not None:
            self.wfile.write(body)

    def log_message(self, *args):
        pass


class LocalServer(HTTPServer):
    def get_request(self):
        sock, peer = super().get_request()
        if self.tls_context is None:
            return sock, peer
        try:
            sock.settimeout(5)
            return self.tls_context.wrap_socket(sock, server_side=True), peer
        except BaseException:
            sock.close()
            raise


def make_server(port=8765, *, cert_file=None, key_file=None):
    if (cert_file is None) != (key_file is None):
        raise ValueError("Both TLS certificate and key are required")
    context = None
    if cert_file is not None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
    server = LocalServer(("127.0.0.1", port), Handler)
    server.tls_context = context
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vulnerable", action="store_true")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--tls-cert")
    parser.add_argument("--tls-key")
    args = parser.parse_args()
    if (args.tls_cert is None) != (args.tls_key is None):
        parser.error("Use --tls-cert and --tls-key together")
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535")
    Handler.vulnerable = args.vulnerable
    with make_server(args.port, cert_file=args.tls_cert, key_file=args.tls_key) as server:
        scheme = "https" if args.tls_cert is not None else "http"
        print(f"Synthetic API on {scheme}://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()
