"""Generate missing keys locally and upload via stdin, without printing secrets."""
import argparse
import json
import secrets
import subprocess

from railway_target import DIRECTORY, ROOT, linked_target, target_flags, verify_binding, write_private

KEYS = [
    ("core", "UPSTREAM_API_KEY"),
    ("core", "MANAGEMENT_PASSWORD"),
    ("gateway", "PROXY_API_KEY"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", nargs=2, metavar=("PROJECT_ID", "ENVIRONMENT_ID"),
                        help="verify and bind existing local keys without uploading")
    args = parser.parse_args()
    target = linked_target()
    binding = DIRECTORY / "railway-target.json"
    if args.bind and args.bind != [target["project_id"], target["environment_id"]]:
        raise SystemExit("--bind IDs must match the linked Railway project and environment")
    if binding.exists():
        verify_binding(target)
    elif not args.bind and any((DIRECTORY / name).exists() for _, name in KEYS):
        raise SystemExit("Existing local keys are unbound; run with --bind PROJECT_ID ENVIRONMENT_ID first")

    values = {}
    for service in dict.fromkeys(service for service, _ in KEYS):
        remote = json.loads(subprocess.check_output(
            ["railway", "variable", "list", *target_flags(target), "--service", service, "--json"], cwd=ROOT,
        ))
        for key_service, name in KEYS:
            if key_service != service:
                continue
            path = DIRECTORY / name
            value = path.read_text().strip() if path.exists() else remote.get(name) or secrets.token_hex(32)
            if not isinstance(value, str) or len(value) < 32 or any(
                c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in value
            ):
                raise SystemExit(f"Invalid {name}: use at least 32 ASCII letters, digits, underscores or hyphens")
            if args.bind and remote.get(name) and remote[name] != value:
                raise SystemExit(f"Local {name} differs from this deployment; recover matching keys before binding")
            values[name] = value

    # Validate every key before writing any local file or uploading any variable.
    DIRECTORY.mkdir(mode=0o700, exist_ok=True)
    DIRECTORY.chmod(0o700)
    if not binding.exists():
        write_private(binding, json.dumps(target, indent=2) + "\n")
    binding.chmod(0o600)
    for _, name in KEYS:
        path = DIRECTORY / name
        if not path.exists():
            write_private(path, values[name])
        path.chmod(0o600)
    if args.bind:
        print("Bound local keys to the linked target; no variables uploaded")
        return
    for service, name in KEYS:
        subprocess.run(
            ["railway", "variable", "set", *target_flags(target), "--service", service,
             "--stdin", "--skip-deploys", name],
            input=values[name], text=True, check=True, cwd=ROOT, stdout=subprocess.DEVNULL,
        )
        print(f"Set {service}.{name} from private local file")


if __name__ == "__main__":
    main()
