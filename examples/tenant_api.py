"""Synthetic two-tenant, two-role API; binds only to IPv4 loopback."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ACTORS = {
    "demo-a-owner": {"id": "a-owner", "tenant": "a", "role": "member"},
    "demo-a-peer": {"id": "a-peer", "tenant": "a", "role": "member"},
    "demo-a-admin": {"id": "a-admin", "tenant": "a", "role": "admin"},
    "demo-b-owner": {"id": "b-owner", "tenant": "b", "role": "member"},
    "demo-b-admin": {"id": "b-admin", "tenant": "b", "role": "admin"},
}
DOCUMENTS = {
    "/documents/a-1": {"tenant": "a", "owner": "a-owner", "record": "a-1"},
    "/documents/a-2": {"tenant": "a", "owner": "a-peer", "record": "a-2"},
    "/documents/b-1": {"tenant": "b", "owner": "b-owner", "record": "b-1"},
}
FAULTS = ("none", "ownership", "tenant", "role", "all")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        document = DOCUMENTS.get(self.path)
        routes = {f"/tenants/{tenant}/{view}": (tenant, view)
                  for tenant in ("a", "b") for view in ("summary", "admin")}
        if document:
            tenant, view = document["tenant"], "document"
        elif self.path in routes:
            tenant, view = routes[self.path]
        else:
            self.respond(404, {"error": "unknown_route"})
            return

        authorization = self.headers.get("Authorization", "")
        actor = ACTORS.get(authorization.removeprefix("Bearer "))
        # The scheme prefix is mandatory; bare demo tokens are not authentication.
        if not authorization.startswith("Bearer ") or actor is None:
            self.respond(401, {"error": "unauthenticated"})
            return

        fault = self.server.fault
        if actor["tenant"] != tenant and fault not in ("tenant", "all"):
            self.respond(403, {"error": "forbidden"})
            return
        if (document and actor["id"] != document["owner"] and actor["role"] != "admin"
                and fault not in ("ownership", "all")):
            self.respond(403, {"error": "forbidden"})
            return
        if view == "admin" and actor["role"] != "admin" and fault not in ("role", "all"):
            self.respond(403, {"error": "forbidden"})
            return

        payload = {"tenant": tenant, "view": view}
        if document:
            payload.update(record=document["record"], owner=document["owner"])
        self.respond(200, payload)

    def respond(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def make_server(port=8766, fault="none"):
    if fault not in FAULTS:
        raise ValueError("Unknown synthetic fault mode")
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.fault = fault
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fault", choices=FAULTS, default="none")
    args = parser.parse_args()
    server = make_server(fault=args.fault)
    print(f"Synthetic tenant API on 127.0.0.1:8766 (fault={args.fault})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
