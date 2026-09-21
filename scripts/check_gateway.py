#!/usr/bin/env python3
"""Exercise the real Caddy boundary: python3 scripts/check_gateway.py --caddy PATH."""

import argparse
import base64
import hashlib
import http.client
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_KEY = "public_test_key_" + "a" * 32
UPSTREAM_KEY = "upstream_test_key_" + "b" * 32


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--caddy", default=shutil.which("caddy"))
    args = parser.parse_args()
    if not args.caddy:
        parser.error("install Caddy or supply --caddy /path/to/caddy")

    env = os.environ | {
        "PROXY_API_KEY": PUBLIC_KEY,
        "UPSTREAM_API_KEY": UPSTREAM_KEY,
        "MANAGEMENT_PASSWORD": "management_test_key_" + "c" * 32,
        "UPSTREAM_HOST": "127.0.0.1",
    }
    checks = 0
    for script, names in (
        ("gateway/start.sh", ("PROXY_API_KEY", "UPSTREAM_API_KEY")),
        ("core/start.sh", ("UPSTREAM_API_KEY", "MANAGEMENT_PASSWORD")),
    ):
        for name in names:
            for invalid in (None, "", "short", "a" * 32 + "\n", "a" * 32 + '"'):
                test_env = env.copy()
                if invalid is None:
                    test_env.pop(name, None)
                else:
                    test_env[name] = invalid
                result = subprocess.run(
                    ["sh", str(ROOT / script)], env=test_env,
                    capture_output=True, text=True, timeout=5,
                )
                assert result.returncode != 0 and name in result.stderr, (script, name)
                checks += 1

    requests = []

    class Backend(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            record = {"method": self.command, "path": self.path, "headers": dict(self.headers)}
            requests.append(record)
            if self.headers.get("Upgrade", "").lower() == "websocket":
                accept = base64.b64encode(hashlib.sha1(
                    (self.headers["Sec-WebSocket-Key"] + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()
                ).digest()).decode()
                self.send_response(101)
                self.send_header("Connection", "Upgrade")
                self.send_header("Upgrade", "websocket")
                self.send_header("Sec-WebSocket-Accept", accept)
                self.end_headers()
                self.wfile.write(b"\x81\x02ok")
                self.wfile.flush()
                return
            body = json.dumps(record).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_POST = do_GET

        def log_message(self, *_):
            pass

    def free_port():
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            return listener.getsockname()[1]

    public_port, health_port = free_port(), free_port()

    def request(method, path, headers=None, port=public_port):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    backend = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Backend)
    threading.Thread(target=backend.serve_forever, daemon=True).start()
    process = None
    try:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryFile() as log:
            config = (ROOT / "gateway/Caddyfile").read_text()
            config = config.replace("{$UPSTREAM_HOST}:8317", "{$UPSTREAM_HOST}:" + str(backend.server_port))
            config = config.replace(":8080 {", f"http://127.0.0.1:{public_port} {{")
            config = config.replace(":8081 {", f"http://127.0.0.1:{health_port} {{")
            config_path = Path(temp) / "Caddyfile"
            config_path.write_text(config)
            process = subprocess.Popen(
                [args.caddy, "run", "--config", str(config_path), "--adapter", "caddyfile"],
                env=env, stdout=log, stderr=log,
            )
            for _ in range(100):
                if process.poll() is not None:
                    log.seek(0)
                    raise AssertionError("Caddy failed to start: " + log.read().decode())
                try:
                    if request("GET", "/healthz", port=health_port)[0] == 200:
                        break
                except OSError:
                    pass
                time.sleep(0.05)
            else:
                raise AssertionError("Caddy health listener did not start")

            allowed = [
                ("GET", "/v1/models"), ("GET", "/v1/responses"),
                ("POST", "/v1/chat/completions"), ("POST", "/v1/completions"),
                ("POST", "/v1/messages"), ("POST", "/v1/messages/count_tokens"),
                ("POST", "/v1/responses"), ("POST", "/v1/responses/compact"),
                ("POST", "/v1/live"), ("GET", "/v1/live/rtc_test-123"),
                ("GET", "/v1/realtime?model=gpt-realtime"),
            ]
            for method, path in allowed:
                for headers in ({"Authorization": "Bearer " + PUBLIC_KEY}, {"X-Api-Key": PUBLIC_KEY}):
                    headers |= {"X-Management-Key": "must-not-forward", "X-Goog-Api-Key": "must-not-forward"}
                    before = len(requests)
                    status, body = request(method, path, headers)
                    assert status == 200 and len(requests) == before + 1, (method, path, status)
                    record = json.loads(body)
                    forwarded = {k.lower(): v for k, v in record["headers"].items()}
                    assert record["method"] == method and record["path"] == path
                    assert forwarded["authorization"] == "Bearer " + UPSTREAM_KEY
                    assert not {"x-api-key", "x-goog-api-key", "x-management-key"} & forwarded.keys()
                    checks += 1
                for headers in ({}, {"Authorization": "Bearer invalid"}, {"X-Api-Key": "invalid"}, {"Authorization": "Bearer " + UPSTREAM_KEY}):
                    before = len(requests)
                    assert request(method, path, headers)[0] == 401, (method, path)
                    assert len(requests) == before, ("unauthenticated request reached backend", path)
                    checks += 1

            blocked = [
                ("GET", path) for path in (
                    "/", "/healthz", "/management.html", "/v0/management/config",
                    "/v0/management/auth-files/download?name=example.json",
                    "/v0/management/oauth-callback", "/anthropic/callback", "/codex/callback",
                    "/antigravity/callback", "/debug/pprof/", "/v1/ws", "/v1/realtime/calls",
                    "/v1/live", "/v1/live/", "/v1/live/rtc_test/extra", "/v1/live/..",
                    "/v1/live/rtc_test%2fextra", "/v1/live/rtc_test/../../v0/management/config",
                    "/v1/models/", "/v1/models/../management.html", "/v1/%2e%2e/management.html",
                    "/v1/%2e%2e%2fmanagement.html", "/v1/models%2f..%2f..%2fmanagement.html",
                    "/v1/models/../../v0/management/config", "/v1/models;management.html",
                )
            ] + [
                ("POST", "/v0/management/oauth-callback"), ("POST", "/v0/management/api-call"),
                ("POST", "/v1/models"), ("GET", "/v1/chat/completions"),
                ("PUT", "/v1/responses"), ("DELETE", "/v1/messages"),
                ("HEAD", "/v1/models"), ("OPTIONS", "/v1/models"),
                ("POST", "/v1/realtime"), ("POST", "/v1/realtime/calls"),
                ("POST", "/v1/realtime/client_secrets"), ("DELETE", "/v1/live/rtc_test"),
                ("POST", "/v1/live/rtc_test"), ("PUT", "/v1/live"),
            ]
            for method, path in blocked:
                before = len(requests)
                status, _ = request(method, path, {"Authorization": "Bearer " + PUBLIC_KEY})
                assert status == 404, (method, path, status)
                assert len(requests) == before, ("blocked request reached backend", path)
                checks += 1
            for path in ("/v1/responses", "/v1/live/rtc_test-123", "/v1/realtime?call_id=rtc_test-123"):
                upgrade = {"Connection": "Upgrade", "Upgrade": "websocket",
                           "Sec-WebSocket-Version": "13", "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="}
                for credential in (None, "invalid", PUBLIC_KEY):
                    headers = upgrade | ({"Authorization": "Bearer " + credential} if credential else {})
                    before = len(requests)
                    connection = http.client.HTTPConnection("127.0.0.1", public_port, timeout=3)
                    try:
                        connection.request("GET", path, headers=headers)
                        response = connection.getresponse()
                        if credential == PUBLIC_KEY:
                            assert response.status == 101, (path, response.status)
                            assert response.getheader("Sec-WebSocket-Accept") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
                            assert response.fp.read(4) == b"\x81\x02ok"
                            assert requests[-1]["headers"]["Authorization"] == "Bearer " + UPSTREAM_KEY
                        else:
                            assert response.status == 401 and len(requests) == before
                        checks += 1
                    finally:
                        connection.close()
            for path in ("/v1/models?key=" + PUBLIC_KEY, "/v1/models?auth_token=" + PUBLIC_KEY):
                before = len(requests)
                assert request("GET", path)[0] == 401
                assert len(requests) == before
                checks += 1
            assert request("GET", "/management.html", port=health_port)[0] == 404
            checks += 1
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        backend.shutdown()
        backend.server_close()
    print(f"PASS: {checks} real-gateway and startup checks")


if __name__ == "__main__":
    main()
