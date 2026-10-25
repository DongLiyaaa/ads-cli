"""Relay transport: hub RelayHandler <-> ads-relay agent over pinned TLS (no network)."""

import io
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib import error, request
from urllib.response import addinfourl
import http.client

from ...core import relay_agent
from ...core.client import AmazonAdsClient
from ...core.env import AdsEnvironment
from ...core.relay import RelayEndpoint, health, opener_for, signed_headers, pinned_connection
from ..servers import make_certificate
from ..worker import SafeRedirect, download_rows


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FakeUpstream:
    """Stands in for Amazon behind the relay; records what the relay sent."""

    def __init__(self):
        self.calls = []
        self.routes = {}

    def open(self, req, timeout=None):
        self.calls.append(
            {
                "method": req.get_method(),
                "url": req.full_url,
                "headers": {k.lower(): v for k, v in req.header_items()},
                "body": req.data,
            }
        )
        status, headers, body = self.routes.get(req.full_url, (404, {}, b"missing"))
        msg = http.client.HTTPMessage()
        for k, v in headers.items():
            msg[k] = v
        if status >= 300:
            raise error.HTTPError(req.full_url, status, "Fixture", msg, io.BytesIO(body))
        resp = addinfourl(io.BytesIO(body), msg, req.full_url, status)
        resp.reason = "OK"
        return resp


class RelayTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cert, key, cls.fingerprint = make_certificate()
        paths = {}
        for name, data in (("cert.pem", cert), ("key.pem", key)):
            paths[name] = os.path.join(cls.tmp.name, name)
            with open(paths[name], "wb") as fh:
                fh.write(data)
        cls.port = free_port()
        cls.secret = "fixture-secret-" + "x" * 20
        cls.server = relay_agent.build_server(
            {"listen": "127.0.0.1", "port": cls.port, "secret": cls.secret, "cert": paths["cert.pem"], "key": paths["key.pem"]}
        )
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.relay = RelayEndpoint("r1", "fixture", "127.0.0.1", cls.port, cls.fingerprint, cls.secret)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        self.upstream = FakeUpstream()
        patcher = patch.object(relay_agent, "UPSTREAM", self.upstream)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_health_reports_version(self):
        self.assertEqual(health(self.relay)["version"], relay_agent.VERSION)

    def test_forward_preserves_method_headers_body(self):
        url = "https://advertising-api.amazon.com/sp/campaigns/list"
        self.upstream.routes[url] = (207, {"Content-Type": "application/json"}, b'{"ok":1}')
        req = request.Request(url, data=b'{"a":1}', method="POST", headers={"Amazon-Advertising-API-Scope": "123", "Content-Type": "application/vnd.x+json"})
        with opener_for(self.relay).open(req, timeout=10) as resp:
            self.assertEqual(resp.getcode(), 207)
            self.assertEqual(resp.headers["Content-Type"], "application/json")
            self.assertEqual(resp.read(), b'{"ok":1}')
        call = self.upstream.calls[0]
        self.assertEqual((call["method"], call["url"], call["body"]), ("POST", url, b'{"a":1}'))
        self.assertEqual(call["headers"]["amazon-advertising-api-scope"], "123")
        self.assertEqual(call["headers"]["content-type"], "application/vnd.x+json")
        self.assertNotIn("host", call["headers"])

    def test_upstream_errors_surface_as_http_error(self):
        url = "https://api.amazon.com/auth/o2/token"
        self.upstream.routes[url] = (400, {}, b'{"error":"invalid_grant"}')
        with self.assertRaises(error.HTTPError) as ctx:
            opener_for(self.relay).open(request.Request(url, data=b"x=1"), timeout=10)
        self.assertEqual(ctx.exception.code, 400)
        self.assertIn(b"invalid_grant", ctx.exception.read())
        ctx.exception.close()

    def test_client_uses_relay_for_oauth(self):
        url = "https://api.amazon.com/auth/o2/token"
        self.upstream.routes[url] = (200, {"Content-Type": "application/json"}, b'{"access_token":"Atza|fixture"}')
        env = AdsEnvironment("cid", "csecret", "rtoken", "1", "NA", "US", relay=self.relay)
        self.assertEqual(AmazonAdsClient(env).exchange_refresh_token(), "Atza|fixture")
        self.assertIn(b"refresh_token=rtoken", self.upstream.calls[0]["body"])

    def test_report_download_follows_redirect_through_relay(self):
        first = "https://offline-report-storage-us-east-1-prod.s3.amazonaws.com/a.json.gz?sig=1"
        second = "https://bucket.s3.us-east-1.amazonaws.com/a.json?sig=2"
        self.upstream.routes[first] = (302, {"Location": second}, b"")
        self.upstream.routes[second] = (200, {}, json.dumps([{"cost": 1}]).encode())
        self.assertEqual(download_rows(first, 1024 * 1024, self.relay), [{"cost": 1}])
        self.assertEqual([c["url"] for c in self.upstream.calls], [first, second])

    def test_redirect_off_allowlist_is_refused(self):
        first = "https://bucket.s3.amazonaws.com/a.json?sig=1"
        self.upstream.routes[first] = (302, {"Location": "https://evil.example.com/x"}, b"")
        with self.assertRaises(ValueError):
            opener_for(self.relay, SafeRedirect()).open(first, timeout=10)

    def test_hub_refuses_non_amazon_hosts(self):
        for url in ("https://example.com/", "http://advertising-api.amazon.com/", "https://advertising-api.amazon.com:8443/"):
            with self.assertRaises(error.URLError):
                opener_for(self.relay).open(url, timeout=5)
        self.assertEqual(self.upstream.calls, [])

    def signed_post(self, meta_value, secret=None, headers=None, body=b""):
        meta = relay_agent.encode_meta(meta_value)
        relay = RelayEndpoint("r1", "fixture", "127.0.0.1", self.port, self.fingerprint, secret or self.secret)
        conn = pinned_connection(relay, 5)
        sent = headers or signed_headers(relay, meta, body)
        conn.request("POST", "/v1/forward", body=body, headers=sent)
        resp = conn.getresponse()
        status = resp.status
        resp.read()
        conn.close()
        return status, sent

    def test_relay_rejects_bad_signature_replay_and_foreign_hosts(self):
        ok = {"m": "GET", "u": "https://advertising-api.amazon.com/v2/profiles", "h": []}
        self.upstream.routes[ok["u"]] = (200, {}, b"[]")
        self.assertEqual(self.signed_post(ok, secret="wrong-secret")[0], 401)
        status, sent = self.signed_post(ok)
        self.assertEqual(status, 200)
        self.assertEqual(self.signed_post(ok, headers=sent)[0], 401)  # replayed nonce
        self.assertEqual(self.signed_post({**ok, "u": "https://example.com/"})[0], 403)
        self.assertEqual(self.signed_post({**ok, "u": "https://127.0.0.1/"})[0], 403)
        self.assertEqual(len(self.upstream.calls), 1)

    def test_stale_timestamp_rejected(self):
        meta = relay_agent.encode_meta({"m": "GET", "u": "https://advertising-api.amazon.com/", "h": []})
        stamp = str(int(time.time()) - 1000)
        sent = {
            "X-Relay-Time": stamp,
            "X-Relay-Nonce": "a" * 32,
            "X-Relay-Meta": meta,
            "X-Relay-Signature": relay_agent.sign(self.secret, stamp, "a" * 32, meta, b""),
        }
        self.assertEqual(self.signed_post(None, headers=sent)[0], 401)

    def test_fingerprint_mismatch_refuses_to_send(self):
        wrong = RelayEndpoint("r1", "fixture", "127.0.0.1", self.port, "0" * 64, self.secret)
        with self.assertRaises(error.URLError) as ctx:
            opener_for(wrong).open("https://advertising-api.amazon.com/", timeout=5)
        self.assertIn("指纹不匹配", str(ctx.exception.reason))
        self.assertEqual(self.upstream.calls, [])

    def test_secret_not_in_repr(self):
        self.assertNotIn(self.secret, repr(self.relay))


if __name__ == "__main__":
    unittest.main()
