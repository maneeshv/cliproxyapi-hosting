"""Generate missing keys locally and upload via stdin, without printing secrets."""
import os
import json
from pathlib import Path
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / ".secrets"
DIRECTORY.mkdir(mode=0o700, exist_ok=True)
for service, name in [
    ("core", "UPSTREAM_API_KEY"),
    ("core", "MANAGEMENT_PASSWORD"),
    ("gateway", "PROXY_API_KEY"),
]:
    path = DIRECTORY / name
    if not path.exists():
        remote = json.loads(subprocess.check_output(
            ["railway", "variable", "list", "--service", service, "--json"], cwd=ROOT,
        ))
        # Re-linking an existing deployment must not rotate its persisted key.
        value = remote.get(name) or secrets.token_hex(32)
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as file:
            file.write(value)
    value = path.read_text().strip()
    if len(value) < 32 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in value):
        raise SystemExit(f"Invalid {name}: use at least 32 ASCII letters, digits, underscores or hyphens")
    path.chmod(0o600)
    subprocess.run(
        ["railway", "variable", "set", "--service", service, "--stdin", "--skip-deploys", name],
        input=value, text=True, check=True, cwd=ROOT, stdout=subprocess.DEVNULL,
    )
    print(f"Set {service}.{name} from private local file")
