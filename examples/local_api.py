"""Synthetic loopback-only API. No real accounts or data."""
import argparse
import json
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vulnerable", action="store_true")
    args = parser.parse_args()
    Handler.vulnerable = args.vulnerable
    print("Synthetic API on 127.0.0.1:8765", flush=True)
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
