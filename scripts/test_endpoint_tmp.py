#!/usr/bin/env python3
"""Portable API smoke test. Python 3.9+, no packages; prompts for the key securely."""
import argparse
import getpass
import json
import os
from pathlib import Path
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("ANTHROPIC_BASE_URL", "https://gateway-production-9f79.up.railway.app"))
    parser.add_argument("--model", default=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"))
    parser.add_argument("--key-file", type=Path, help="Read a key file instead of environment/prompt; never put the key in arguments")
    parser.add_argument("--timeout", type=float, default=90, help="Socket timeout in seconds")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    url = urllib.parse.urlsplit(base)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment or url.path:
        parser.error("Use the HTTPS origin only, e.g. https://gateway-production-9f79.up.railway.app (no /v1)")
    key = (args.key_file.read_text() if args.key_file else os.getenv("PROXY_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY") or getpass.getpass("Proxy API key (hidden): ")).strip()
    if not key or any(c.isspace() for c in key):
        parser.error("The API key must be nonempty and contain no whitespace")

    # Do not follow redirects with authentication headers attached.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    failed = []

    def check(label, path, payload=None, auth="bearer", expected=200, streaming=False):
        headers = {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
        if auth == "bearer":
            headers["Authorization"] = "Bearer " + key
        elif auth == "x-api-key":
            headers["x-api-key"] = key
        request = urllib.request.Request(base + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        started = time.monotonic()
        try:
            try:
                response = opener.open(request, timeout=args.timeout)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                status = response.status
                raw = response.read(1_048_576).decode("utf-8", errors="replace")
            try:
                body = json.loads(raw) if not streaming and raw else {}
            except json.JSONDecodeError:
                body = {}
            if not isinstance(body, dict):
                body = {}
            ok = status == expected
            if path == "/v1/models" and expected == 200:
                ok = ok and isinstance(body.get("data"), list)
            if streaming and status == 200:
                events = [json.loads(line[5:].strip()) for line in raw.splitlines() if line.startswith("data:") and line[5:].strip() != "[DONE]"]
                errors = [event for event in events if event.get("type") == "error" or event.get("error")]
                ok = not errors and any(event.get("type") == "message_stop" for event in events)
                detail = json.dumps(errors) if errors else "message_stop=" + str(ok)
            elif payload is not None and status == 200:
                ok = "input_tokens" in body if path.endswith("count_tokens") else body.get("type") == "message" and bool(body.get("content"))
                detail = "input_tokens=" + str(body.get("input_tokens")) if path.endswith("count_tokens") else "response_model=" + str(body.get("model"))
            elif status != expected:
                detail = raw[:800]
            else:
                detail = ""
            print(f"{'PASS' if ok else 'FAIL'} {label}: HTTP {status} ({time.monotonic()-started:.1f}s) {detail}".replace(key, "[REDACTED]"), flush=True)
            if not ok:
                failed.append(label)
            return body
        except (OSError, ValueError, urllib.error.URLError) as error:
            print(f"FAIL {label}: {type(error).__name__}: {str(error).replace(key, '[REDACTED]')}", flush=True)
            failed.append(label)
            return {}

    print(f"Endpoint: {base}\nModel: {args.model}\nKey: loaded (never printed)", flush=True)
    check("No-key rejection", "/v1/models", auth=None, expected=401)
    models = check("Bearer authentication", "/v1/models")
    check("x-api-key authentication", "/v1/models", auth="x-api-key")
    advertised = [item["id"] for item in models.get("data", []) if "id" in item]
    print("Selected model advertised:", args.model in advertised, flush=True)
    print("Available Claude models:", ", ".join(m for m in advertised if m.startswith("claude-")), flush=True)
    payload = {"model": args.model, "messages": [{"role": "user", "content": "Reply with exactly OK."}]}
    check("Count tokens", "/v1/messages/count_tokens", payload)
    check("Messages", "/v1/messages", payload | {"max_tokens": 64})
    check("Messages streaming", "/v1/messages", payload | {"max_tokens": 64, "stream": True}, streaming=True)
    print("FAILED: " + ", ".join(failed) if failed else "All endpoint checks passed.", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
