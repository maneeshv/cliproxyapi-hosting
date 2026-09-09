"""Run only after reviewing the tailnet policy in docs/tailscale.md."""
from pathlib import Path
import subprocess

from railway_target import bound_target, target_flags

ROOT = Path(__file__).resolve().parents[1]
target = bound_target()
path = ROOT / ".secrets/tailscale-auth-key"
key = path.read_text().strip()
if not key.startswith("tskey-auth-") or any(c.isspace() for c in key):
    raise SystemExit("Expected a Tailscale auth key in .secrets/tailscale-auth-key")
path.chmod(0o600)
subprocess.run(
    ["railway", "variable", "set", *target_flags(target), "--service", "admin", "--stdin", "--skip-deploys", "TS_AUTHKEY"],
    input=key, text=True, check=True, cwd=ROOT, stdout=subprocess.DEVNULL,
)
subprocess.run(["railway", "up", *target_flags(target), "--service", "admin", "--detach"], cwd=ROOT, check=True)
