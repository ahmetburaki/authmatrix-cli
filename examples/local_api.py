"""Synthetic loopback-only API. No real accounts or data."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    vulnerable = False

    def do_GET(self):
        if self.path != "/documents/1":
            status = 404
        else:
            token = self.headers.get("Authorization", "")
            if token not in ("Bearer demo-owner", "Bearer demo-other"):
                status = 401
            elif token == "Bearer demo-owner" or self.vulnerable:
                status = 200
            else:
                status = 403
        self.send_response(status)
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vulnerable", action="store_true")
    args = parser.parse_args()
    Handler.vulnerable = args.vulnerable
    print("Synthetic API on 127.0.0.1:8765", flush=True)
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
