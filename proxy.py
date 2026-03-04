# /// script
# requires-python = ">=3.11"
# ///
"""
GoldenCheetah CORS Proxy

A local proxy that adds CORS headers to GoldenCheetah's API responses.
Prompts the user to approve each new website that wants to access their data.

Usage:
    uv run proxy.py
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error
import threading
import subprocess
import platform

LISTEN_PORT = 12022
GC_BASE = "http://localhost:12021"

allowed_origins = set()
denied_origins = set()
origin_lock = threading.Lock()


def show_dialog(origin):
    """Show a native system dialog. Returns True if user clicks Allow."""
    title = "GoldenCheetah Proxy"
    message = f'"{origin}" wants to access your GoldenCheetah data.\n\nAllow this website?'
    system = platform.system()

    try:
        if system == "Darwin":
            escaped_origin = origin.replace('"', '\\"')
            script = (
                f'display dialog "{escaped_origin} wants to access your '
                f'GoldenCheetah data." & return & return & '
                f'"Allow this website?" '
                f'with title "{title}" '
                f'buttons {{"Deny", "Allow"}} '
                f'default button "Allow"'
            )
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True,
            )
            return "Allow" in result.stdout

        elif system == "Windows":
            escaped_origin = origin.replace("'", "''")
            ps_script = (
                "Add-Type -AssemblyName PresentationFramework; "
                "[System.Windows.MessageBox]::Show("
                f"'{escaped_origin} wants to access your GoldenCheetah data.`n`nAllow this website?', "
                f"'{title}', 'YesNo', 'Question')"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True,
            )
            return "Yes" in result.stdout

        else:
            # Linux / fallback: terminal prompt
            print(f'\n  "{origin}" wants to access your GoldenCheetah data.')
            answer = input("  Allow? [y/N] ").strip().lower()
            return answer in ("y", "yes")

    except Exception:
        # If dialog fails, fall back to terminal
        print(f'\n  "{origin}" wants to access your GoldenCheetah data.')
        answer = input("  Allow? [y/N] ").strip().lower()
        return answer in ("y", "yes")


def prompt_user(origin):
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
                self.send_response(403)
                self.send_header("Access-Control-Allow-Origin", origin)
                self.end_headers()
                self.wfile.write(b"Origin denied by user")
                return
            if not prompt_user(origin):
                self.send_response(403)
                self.send_header("Access-Control-Allow-Origin", origin)
                self.end_headers()
                self.wfile.write(b"Origin denied by user")
                return

        target_url = GC_BASE + self.path
        try:
            req = urllib.request.Request(target_url)
            resp = urllib.request.urlopen(req)
            body = resp.read()

            self.send_response(resp.status)
            self.send_header("Access-Control-Allow-Origin", origin or "*")
            for key, val in resp.getheaders():
                if key.lower() not in ("access-control-allow-origin", "transfer-encoding"):
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(body)
        except urllib.error.URLError as e:
            self.send_response(502)
            self.send_header("Access-Control-Allow-Origin", origin or "*")
            self.end_headers()
            msg = f"Could not reach GoldenCheetah at {GC_BASE}: {e.reason}"
            self.wfile.write(msg.encode())

    def log_message(self, format, *args):
        pass  # Silence per-request logs


def main():
    server = HTTPServer(("localhost", LISTEN_PORT), ProxyHandler)
    print(f"GoldenCheetah CORS Proxy running on http://localhost:{LISTEN_PORT}")
    print(f"Forwarding to {GC_BASE}")
    print(f"Waiting for connections...\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
