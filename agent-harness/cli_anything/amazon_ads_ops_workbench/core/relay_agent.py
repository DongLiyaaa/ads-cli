#!/usr/bin/env python3
"""ads-relay: executes Amazon Ads HTTP calls on a remote server for the hub.

Standalone and stdlib-only (Python 3.6+): the hub uploads this file verbatim
over SSH and runs it as a systemd service. Every request must carry an HMAC
signature made with the shared secret; only HTTPS Amazon / S3 hosts can be
reached, so this is never an open proxy.
"""

import base64
import hashlib
import hmac
import json
import socketserver
import ssl
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import error, parse, request

VERSION = "1"
MAX_SKEW = 300
MAX_REQUEST_BODY = 16 * 1024 * 1024
ALLOWED_HOSTS = {
    "api.amazon.com",
    "advertising-api.amazon.com",
    "advertising-api-eu.amazon.com",
    "advertising-api-fe.amazon.com",
}
ALLOWED_SUFFIXES = (".amazonaws.com", ".amazonaws.com.cn")
# Hop-by-hop or transport headers the relay sets itself.
DROP_HEADERS = {"host", "content-length", "connection", "transfer-encoding"}


def allowed_url(url):
    parts = parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    return (
        parts.scheme == "https"
        and not parts.username
        and not parts.password
        and parts.port in (None, 443)
        and (host in ALLOWED_HOSTS or host.endswith(ALLOWED_SUFFIXES))
    )


def sign(secret, stamp, nonce, meta, body):
    message = "\n".join(
        ["v1", stamp, nonce, meta, hashlib.sha256(body).hexdigest()]
    ).encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def encode_meta(value):
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode()


def decode_meta(value):
    return json.loads(base64.urlsafe_b64decode(value.encode()).decode())


class NoRedirect(request.HTTPRedirectHandler):
    # Redirects go back to the hub, which re-validates and re-sends them.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


UPSTREAM = request.build_opener(NoRedirect())


class Nonces:
    def __init__(self):
        self.seen = {}
        self.lock = threading.Lock()

    def fresh(self, nonce):
        cutoff = time.time() - 2 * MAX_SKEW
        with self.lock:
            if len(self.seen) > 10000:
                self.seen = {k: v for k, v in self.seen.items() if v > cutoff}
            if nonce in self.seen:
                return False
            self.seen[nonce] = time.time()
            return True


class Handler(BaseHTTPRequestHandler):
    server_version = "ads-relay/" + VERSION
    sys_version = ""
    timeout = 120

    def log_message(self, fmt, *args):
        # URLs carry report signatures; log only method and status.
        pass

    def fail(self, code, message):
        body = json.dumps({"relay_error": message}).encode()
        self.send_response(code)
        self.send_header("X-Relay-Error", "1")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def authenticate(self, body):
        stamp = self.headers.get("X-Relay-Time", "")
        nonce = self.headers.get("X-Relay-Nonce", "")
        meta = self.headers.get("X-Relay-Meta", "")
        given = self.headers.get("X-Relay-Signature", "")
        try:
            skew = abs(time.time() - int(stamp))
        except ValueError:
            return None
        expected = sign(self.server.config["secret"], stamp, nonce, meta, body)
        if (
            skew > MAX_SKEW
            or not 16 <= len(nonce) <= 64
            or not hmac.compare_digest(expected, given)
            or not self.server.nonces.fresh(nonce)
        ):
            return None
        return meta

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_REQUEST_BODY:
            raise ValueError("request body too large")
        return self.rfile.read(length) if length else b""

    def do_GET(self):
        if self.path != "/v1/health" or self.authenticate(b"") is None:
            return self.fail(401, "unauthorized")
        body = json.dumps(
            {
                "ok": True,
                "version": VERSION,
                "python": "%d.%d.%d" % sys.version_info[:3],
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            body = self.read_body()
        except ValueError:
            return self.fail(413, "request body too large")
        meta = self.authenticate(body) if self.path == "/v1/forward" else None
        if meta is None:
            return self.fail(401, "unauthorized")
        try:
            spec = decode_meta(meta)
            url, method = spec["u"], spec["m"]
            headers = [(k, v) for k, v in spec.get("h", []) if k.lower() not in DROP_HEADERS]
            timeout = min(float(spec.get("t") or 30), 300)
        except Exception:
            return self.fail(400, "malformed request")
        if not allowed_url(url) or method not in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
            return self.fail(403, "destination not allowed")
        upstream = request.Request(url, data=body or None, method=method)
        for key, value in headers:
            upstream.add_header(key, value)
        try:
            response = UPSTREAM.open(upstream, timeout=timeout)
        except error.HTTPError as exc:
            response = exc
        except Exception as exc:
            return self.fail(502, "upstream unreachable: %s" % getattr(exc, "reason", exc))
        with response:
            self.send_response(200)
            self.send_header("X-Relay-Status", str(response.code))
            self.send_header("X-Relay-Reason", str(getattr(response, "reason", "") or ""))
            self.send_header("X-Relay-Headers", encode_meta(list(response.headers.items())))
            self.send_header("Connection", "close")
            self.end_headers()
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
        self.close_connection = True


class Server(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # Port scanners and failed TLS handshakes are routine; stay quiet.
        pass


def build_server(config):
    server = Server((config.get("listen", "0.0.0.0"), int(config["port"])), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    if hasattr(context, "minimum_version"):
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    else:
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
    context.load_cert_chain(config["cert"], config["key"])
    # Lazy handshake keeps a slow client from blocking accept().
    server.socket = context.wrap_socket(
        server.socket, server_side=True, do_handshake_on_connect=False
    )
    server.config = config
    server.nonces = Nonces()
    return server


def main(argv):
    path = argv[argv.index("--config") + 1] if "--config" in argv else "/etc/ads-relay/config.json"
    with open(path) as fh:
        config = json.load(fh)
    server = build_server(config)
    sys.stdout.write("ads-relay %s listening on %s:%s\n" % (VERSION, config.get("listen", "0.0.0.0"), config["port"]))
    sys.stdout.flush()
    server.serve_forever()


if __name__ == "__main__":
    main(sys.argv)
