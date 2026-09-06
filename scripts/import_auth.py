"""Copy selected existing CLIProxyAPI credentials over authenticated SSH, once."""
import argparse
import base64
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, default=Path.home() / ".cli-proxy-api")
parser.add_argument("--providers", nargs="+", default=["claude", "codex", "xai"])
parser.add_argument("--identity", type=Path, default=Path.home() / ".ssh/cliproxyapi_railway")
args = parser.parse_args()
counts = {}
for path in sorted(args.source.glob("*.json")):
    payload = path.read_bytes()
    record = json.loads(payload)
    provider = record.get("type")
    if provider not in args.providers:
        continue
    # Preserve unique filenames and never overwrite refreshed remote credentials.
    target = shlex.quote("/data/auths/" + path.name)
    staging = shlex.quote("/data/auths/" + path.name + ".pending")
    command = f"set -eu; umask 077; test ! -e {target} || exit 17; base64 -d > {staging}; chmod 600 {staging}; mv {staging} {target}"
    result = subprocess.run(
        ["railway", "ssh", "--service", "core", "--identity-file", str(args.identity), "--", "sh", "-c", command],
        input=base64.b64encode(payload), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT,
    )
    if result.returncode == 17:
        print(f"Skipped existing {provider} credential; remote copy preserved")
        continue
    if result.returncode:
        raise SystemExit(f"Credential upload failed for {provider} (exit {result.returncode}); inspect SSH connectivity, no secret output shown")
    counts[provider] = counts.get(provider, 0) + 1
print("Imported credential counts:", counts)
