"""Verify management over the connected Tailscale client without printing secrets."""
import http.client
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
state = json.loads(subprocess.check_output(["tailscale", "status", "--json"]))
assert state.get("BackendState") == "Running", "Connect your Tailscale client first"
peers = [p for p in (state.get("Peer") or {}).values() if p.get("HostName") == "cliproxy-admin"]
assert len(peers) == 1 and peers[0].get("Online"), "Expected one online cliproxy-admin node"
peer = peers[0]
host = peer["DNSName"].rstrip(".")
password = (ROOT / ".secrets/MANAGEMENT_PASSWORD").read_text().strip()
for path, key, expected in [
    ("/management.html", None, 200),
    ("/v0/management/config", None, 401),
    ("/v0/management/config", password, 200),
]:
    connection = http.client.HTTPSConnection(host, 8317, timeout=60)
    try:
        connection.request("GET", path, headers={"Authorization": "Bearer " + key} if key else {})
        response = connection.getresponse()
        body = response.read()
        assert response.status == expected, (path, response.status)
        if path.endswith(".html"):
            assert b"<html" in body.lower(), "Expected the dashboard HTML"
        elif key:
            assert isinstance(json.loads(body), dict), "Expected management configuration"
    finally:
        connection.close()
print(f"PASS: https://{host}:8317/management.html; trusted TLS certificate; management password required and accepted")
print("Node ID:", peer["ID"], "Tags:", peer.get("Tags") or [], "Key expiry:", peer.get("KeyExpiry"))
