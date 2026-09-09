"""Probe the deployed public boundary without printing credentials."""
import argparse
import http.client
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("base_url", help="HTTPS gateway origin, e.g. https://gateway.example.com")
args = parser.parse_args()
try:
    url = urlsplit(args.base_url)
    valid = (url.scheme == "https" and url.hostname and url.username is None and url.password is None
             and url.path in ("", "/") and not any(c.isspace() or ord(c) < 32 for c in args.base_url)
             and not any(c in args.base_url for c in "?#\\") and url.port != 0)
except ValueError:
    valid = False
if not valid:
    parser.error("Use the HTTPS origin only, e.g. https://gateway.example.com (no /v1)")
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
