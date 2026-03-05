"""Tests for the GoldenCheetah CORS proxy."""

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch
from urllib.request import Request, urlopen

import pytest

from goldencheetah_proxy.proxy import (
    DEFAULT_GC_PORT,
    DEFAULT_PORT,
    allowed_origins,
    denied_origins,
    make_handler,
    parse_args,
)


class FakeGCHandler(BaseHTTPRequestHandler):
    """Fake GoldenCheetah API server for testing."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/csv")
        self.end_headers()
        if self.path == "/":
            self.wfile.write(b"name\nAart\n")
        elif self.path.startswith("/Aart"):
            self.wfile.write(b"date,NP\n2024-01-01,250\n")
        else:
            self.wfile.write(b"ok")

    def log_message(self, format, *args):
        pass


@pytest.fixture(autouse=True)
def _clear_origins():
    """Reset origin sets between tests."""
    allowed_origins.clear()
    denied_origins.clear()
    yield
    allowed_origins.clear()
    denied_origins.clear()


@pytest.fixture(scope="module")
def gc_server():
    """Start a fake GoldenCheetah server."""
    server = HTTPServer(("localhost", 0), FakeGCHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


@pytest.fixture()
def proxy_server(gc_server):
    """Start the proxy pointing at the fake GC server."""
    handler = make_handler(f"http://localhost:{gc_server}")
    server = HTTPServer(("localhost", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


def fetch(port, path="/", headers=None):
    """Helper to fetch from the proxy."""
    req = Request(f"http://localhost:{port}{path}")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    return urlopen(req)


def fetch_options(port, path="/", headers=None):
    """Helper to send OPTIONS to the proxy."""
    req = Request(f"http://localhost:{port}{path}", method="OPTIONS")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    return urlopen(req)


class TestCORSHeaders:
    def test_get_includes_cors_headers(self, proxy_server):
        resp = fetch(proxy_server, "/")
        assert resp.headers["Access-Control-Allow-Origin"] == "*"

    def test_get_with_origin_reflects_origin(self, proxy_server):
        allowed_origins.add("http://example.com")
        resp = fetch(proxy_server, "/", {"Origin": "http://example.com"})
        assert resp.headers["Access-Control-Allow-Origin"] == "http://example.com"

    def test_options_returns_204(self, proxy_server):
        resp = fetch_options(proxy_server, "/")
        assert resp.status == 204

    def test_options_includes_all_cors_headers(self, proxy_server):
        resp = fetch_options(proxy_server, "/")
        assert resp.headers["Access-Control-Allow-Methods"] == "GET, OPTIONS"
        assert resp.headers["Access-Control-Allow-Headers"] == "*"
        assert resp.headers["Access-Control-Max-Age"] == "86400"


class TestForwarding:
    def test_forwards_root_path(self, proxy_server):
        resp = fetch(proxy_server, "/")
        body = resp.read().decode()
        assert "Aart" in body

    def test_forwards_athlete_path(self, proxy_server):
        resp = fetch(proxy_server, "/Aart")
        body = resp.read().decode()
        assert "250" in body

    def test_forwards_query_params(self, proxy_server):
        resp = fetch(proxy_server, "/Aart?metrics=NP")
        assert resp.status == 200


class TestOriginApproval:
    def test_allowed_origin_passes(self, proxy_server):
        allowed_origins.add("http://myapp.com")
        resp = fetch(proxy_server, "/", {"Origin": "http://myapp.com"})
        assert resp.status == 200

    def test_denied_origin_returns_403(self, proxy_server):
        denied_origins.add("http://evil.com")
        with pytest.raises(Exception) as exc_info:
            fetch(proxy_server, "/", {"Origin": "http://evil.com"})
        assert "403" in str(exc_info.value)

    def test_new_origin_prompts_user(self, proxy_server):
        with patch("goldencheetah_proxy.proxy.show_dialog", return_value=True) as mock:
            resp = fetch(proxy_server, "/", {"Origin": "http://new-site.com"})
            assert resp.status == 200
            mock.assert_called_once_with("http://new-site.com")
        assert "http://new-site.com" in allowed_origins

    def test_denied_prompt_returns_403(self, proxy_server):
        with patch("goldencheetah_proxy.proxy.show_dialog", return_value=False):
            with pytest.raises(Exception) as exc_info:
                fetch(proxy_server, "/", {"Origin": "http://bad-site.com"})
            assert "403" in str(exc_info.value)
        assert "http://bad-site.com" in denied_origins


class TestGCUnreachable:
    def test_returns_502_when_gc_down(self):
        handler = make_handler("http://localhost:1")  # nothing listening
        server = HTTPServer(("localhost", 0), handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with pytest.raises(Exception) as exc_info:
                fetch(port, "/")
            assert "502" in str(exc_info.value)
        finally:
            server.shutdown()


class TestCLIArgs:
    def test_defaults(self):
        opts = parse_args([])
        assert opts.port == DEFAULT_PORT
        assert opts.gc_port == DEFAULT_GC_PORT

    def test_custom_port(self):
        opts = parse_args(["--port", "9999"])
        assert opts.port == 9999

    def test_custom_gc_port(self):
        opts = parse_args(["--gc-port", "5555"])
        assert opts.gc_port == 5555

    def test_both_ports(self):
        opts = parse_args(["--port", "8000", "--gc-port", "9000"])
        assert opts.port == 8000
        assert opts.gc_port == 9000
