"""Probe the deployed public boundary without printing credentials."""
import http.client
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
url = urlsplit(sys.argv[1] if len(sys.argv) > 1 else "https://gateway-production-9f79.up.railway.app")
if url.scheme != "https":
    raise SystemExit("Use an HTTPS gateway URL")
key = (ROOT / ".secrets/PROXY_API_KEY").read_text().strip()

def request(path, credential=None):
    connection = http.client.HTTPSConnection(url.hostname, url.port or 443, timeout=30)
    headers = {"Authorization": "Bearer " + credential} if credential else {}
    connection.request("GET", path, headers=headers)
    response = connection.getresponse()
    status, body = response.status, response.read()
    connection.close()
    return status, body

for path in ["/", "/healthz", "/management.html", "/v0/management/config", "/v0/management/oauth-callback", "/codex/callback", "/anthropic/callback", "/debug/pprof/", "/v1/../management.html"]:
    for credential in [None, key]:
        status, _ = request(path, credential)
        assert status == 404, (path, status)
for credential in [None, "incorrect-key"]:
    assert request("/v1/models", credential)[0] == 401
status, body = request("/v1/models", key)
assert status == 200, ("authenticated models", status)
models = json.loads(body).get("data", [])
print(f"PASS: public management/OAuth/debug denied; missing/wrong keys denied; authenticated model list succeeds ({len(models)} models).")
