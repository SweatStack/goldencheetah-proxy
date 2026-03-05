"""GoldenCheetah CORS Proxy.

A local proxy that adds CORS headers to GoldenCheetah's API responses.
Prompts the user to approve each new website that wants to access their data.
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from goldencheetah_proxy import __version__

DEFAULT_PORT = 12022
DEFAULT_GC_PORT = 12021

allowed_origins: set[str] = set()
denied_origins: set[str] = set()
origin_lock = threading.Lock()


def show_dialog(origin: str) -> bool:
    """Show a native system dialog asking the user to allow/deny an origin."""
    system = platform.system()

    try:
        if system == "Darwin":
            escaped = origin.replace('"', '\\"')
            script = (
                f'display dialog "{escaped} wants to access your '
                f'GoldenCheetah data." & return & return & '
                f'"Allow this website?" '
                f'with title "GoldenCheetah Proxy" '
                f'buttons {{"Deny", "Allow"}} '
                f'default button "Allow"'
            )
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
            )
            return "Allow" in result.stdout

        elif system == "Windows":
            escaped = origin.replace("'", "''")
            ps_script = (
                "Add-Type -AssemblyName PresentationFramework; "
                "[System.Windows.MessageBox]::Show("
                f"'{escaped} wants to access your GoldenCheetah data.`n`nAllow this website?', "
                f"'GoldenCheetah Proxy', 'YesNo', 'Question')"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
            )
            return "Yes" in result.stdout

        else:
            return _terminal_prompt(origin)

    except Exception:
        return _terminal_prompt(origin)


def _terminal_prompt(origin: str) -> bool:
    print(f'\n  "{origin}" wants to access your GoldenCheetah data.')
    answer = input("  Allow? [y/N] ").strip().lower()
    return answer in ("y", "yes")


def prompt_user(origin: str) -> bool:
    """Ask the user to allow/deny an origin. Thread-safe."""
    with origin_lock:
        if origin in allowed_origins:
            return True
        if origin in denied_origins:
            return False

        if show_dialog(origin):
            allowed_origins.add(origin)
            print(f"  Allowed: {origin}")
            return True
        else:
            denied_origins.add(origin)
            print(f"  Denied: {origin}")
            return False


def make_handler(gc_base: str) -> type[BaseHTTPRequestHandler]:
    """Create a handler class bound to a specific GoldenCheetah base URL."""

    class ProxyHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            origin = self.headers.get("Origin", "")
            if origin and origin not in allowed_origins:
                if not prompt_user(origin):
                    self.send_response(403)
                    self.end_headers()
                    return

            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin or "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Max-Age", "86400")
            self.end_headers()

        def do_GET(self):
            origin = self.headers.get("Origin", "")

            if origin and origin not in allowed_origins:
                if origin in denied_origins:
                    self._send_forbidden(origin)
                    return
                if not prompt_user(origin):
                    self._send_forbidden(origin)
                    return

            target_url = gc_base + self.path
            try:
                req = urllib.request.Request(target_url)
                resp = urllib.request.urlopen(req)
                body = resp.read()
                self._forward_response(resp.status, resp.getheaders(), body, origin)
            except urllib.error.HTTPError as e:
                # GC returned an error status — forward it as-is.
                body = e.read()
                self._forward_response(e.code, e.headers.items(), body, origin)
            except urllib.error.URLError as e:
                self.send_response(502)
                self.send_header("Access-Control-Allow-Origin", origin or "*")
                self.end_headers()
                msg = f"Could not reach GoldenCheetah at {gc_base}: {e.reason}"
                self.wfile.write(msg.encode())

        def _forward_response(self, status, headers, body, origin):
            self.send_response(status)
            self.send_header("Access-Control-Allow-Origin", origin or "*")
            for key, val in headers:
                if key.lower() not in (
                    "access-control-allow-origin",
                    "transfer-encoding",
                ):
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(body)

        def _send_forbidden(self, origin: str):
            self.send_response(403)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.end_headers()
            self.wfile.write(b"Origin denied by user")

        def log_message(self, format, *args):
            pass  # Silence per-request logs

    return ProxyHandler


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="goldencheetah-proxy",
        description="CORS proxy for the GoldenCheetah API",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--gc-port",
        type=int,
        default=DEFAULT_GC_PORT,
        help=f"GoldenCheetah API port (default: {DEFAULT_GC_PORT})",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> None:
    opts = parse_args(args)
    gc_base = f"http://localhost:{opts.gc_port}"
    handler = make_handler(gc_base)
    server = HTTPServer(("localhost", opts.port), handler)

    print(f"GoldenCheetah Proxy v{__version__}")
    print(f"Proxy running on http://localhost:{opts.port}")
    print(f"Forwarding to GoldenCheetah at {gc_base}")
    print("Waiting for connections...\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
