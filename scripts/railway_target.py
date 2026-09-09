"""Keep local deployment credentials tied to one explicitly linked target."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / ".secrets"


def linked_target():
    # CLI v5.43.1 status JSON contains every environment, not the selected ID.
    # Read the same nearest-ancestor link as the CLI; never inspect auth fields.
    if any(name in os.environ for name in (
        "RAILWAY_TOKEN", "RAILWAY_PROJECT_ID", "RAILWAY_ENVIRONMENT_ID",
    )) or os.environ.get("RAILWAY_ENV", "production").lower() != "production":
        raise SystemExit("Unset Railway target overrides and use railway login/link before running this script")
    try:
        projects = json.loads((Path.home() / ".railway/config.json").read_text())["projects"]
        link = next((projects[str(path)] for path in (ROOT, *ROOT.parents) if str(path) in projects), {})
        target = {"project_id": link["project"], "environment_id": link["environment"]}
        if not all(isinstance(value, str) and value for value in target.values()):
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        raise SystemExit("Link a Railway project and environment with railway link first") from None
    return target


def target_flags(target):
    return ["--project", target["project_id"], "--environment", target["environment_id"]]


def bound_target():
    target = linked_target()
    verify_binding(target)
    return target


def verify_binding(target):
    try:
        saved = json.loads((DIRECTORY / "railway-target.json").read_text())
    except (OSError, ValueError):
        raise SystemExit("Bind local secrets first: python scripts/set_secrets.py --bind PROJECT_ID ENVIRONMENT_ID") from None
    if saved != target:
        raise SystemExit("Local secrets belong to a different Railway target; relink it or use a separate clone")


def write_private(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as file:
        file.write(value)
