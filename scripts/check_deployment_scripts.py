"""Offline regression checks: no Railway calls or real credentials are used."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import tempfile
from unittest.mock import patch

import backups
import railway_target
import set_secrets

TARGET = {"project_id": "project-test", "environment_id": "staging-test"}
KEY = "a" * 32


def fails(call, message):
    try:
        call()
    except SystemExit as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError("Expected failure: " + message)


with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
    root = Path(temporary)
    directory = root / ".secrets"
    directory.mkdir()
    home = root / "home"
    (home / ".railway").mkdir(parents=True)
    (home / ".railway/config.json").write_text(json.dumps({"projects": {
        str(root): {"project": TARGET["project_id"], "environment": TARGET["environment_id"]},
    }}))
    with patch.object(railway_target, "ROOT", root / "nested"), \
            patch.object(Path, "home", return_value=home), patch.dict("os.environ", {}, clear=True):
        assert railway_target.linked_target() == TARGET
        with patch.dict("os.environ", {"RAILWAY_PROJECT_ID": "other"}):
            fails(railway_target.linked_target, "Unset Railway target overrides")

    with patch.object(railway_target, "DIRECTORY", directory), \
            patch.object(set_secrets, "DIRECTORY", directory), \
            patch.object(set_secrets, "linked_target", return_value=TARGET), \
            patch.object(set_secrets.subprocess, "check_output", return_value=b"{}") as reads, \
            patch.object(set_secrets.subprocess, "run") as uploads, \
            patch("sys.argv", ["set_secrets.py"]):
        # Existing unbound credentials cannot reach a deployment.
        (directory / "UPSTREAM_API_KEY").write_text(KEY)
        fails(set_secrets.main, "unbound")
        reads.assert_not_called()
        uploads.assert_not_called()
        with patch("sys.argv", ["set_secrets.py", "--bind", "other", "staging-test"]):
            fails(set_secrets.main, "must match")
        with patch("sys.argv", ["set_secrets.py", "--bind", *TARGET.values()]), \
                patch.object(set_secrets.subprocess, "check_output", return_value=json.dumps({"UPSTREAM_API_KEY": "b" * 32}).encode()):
            fails(set_secrets.main, "differs")
            assert not (directory / "railway-target.json").exists()
        with patch("sys.argv", ["set_secrets.py", "--bind", *TARGET.values()]):
            set_secrets.main()
        uploads.assert_not_called()
        assert json.loads((directory / "railway-target.json").read_text()) == TARGET
        assert (directory / "PROXY_API_KEY").stat().st_mode & 0o777 == 0o600

        # One invalid late key prevents all uploads, including earlier valid keys.
        (directory / "PROXY_API_KEY").write_text("invalid")
        fails(set_secrets.main, "Invalid PROXY_API_KEY")
        uploads.assert_not_called()
        (directory / "PROXY_API_KEY").write_text("c" * 32)
        set_secrets.main()
        assert uploads.call_count == 3
        for call in uploads.call_args_list:
            command = call.args[0]
            assert command[command.index("--project") + 1] == TARGET["project_id"]
            assert command[command.index("--environment") + 1] == TARGET["environment_id"]
        assert uploads.call_args_list[-1].kwargs["input"] == "c" * 32
        uploads.reset_mock()
        with patch.object(set_secrets, "linked_target", return_value=TARGET | {"environment_id": "production-test"}):
            fails(set_secrets.main, "different Railway target")
        uploads.assert_not_called()

        # A fresh clone recovers existing remote keys and creates its own binding.
        fresh = root / "fresh"
        with patch.object(set_secrets, "DIRECTORY", fresh), \
                patch.object(set_secrets.subprocess, "check_output", return_value=json.dumps({name: KEY for _, name in set_secrets.KEYS}).encode()):
            set_secrets.main()
        assert (fresh / "PROXY_API_KEY").read_text() == KEY
        assert (fresh / "railway-target.json").exists()

    def environment(identifier, names):
        return {"node": {"id": identifier, "volumeInstances": {"edges": [
            {"node": {"id": identifier + "-" + name, "volume": {"name": name}}} for name in names
        ]}}}

    status = {"id": TARGET["project_id"], "environments": {"edges": [
        environment("production-test", ["proxy-data", "tailscale-state"]),
        environment("staging-test", ["proxy-data", "tailscale-state"]),
    ]}}
    with patch.object(backups, "linked_target", return_value=TARGET), \
            patch.object(backups.subprocess, "check_output", side_effect=lambda *a, **k: json.dumps(status).encode()), \
            patch.object(backups, "api", return_value={"volumeInstanceBackupScheduleList": [{"kind": "DAILY"}]}) as api:
        backups.main()
        assert api.call_count == 6
        assert all(call.args[1]["id"].startswith("staging-test-") for call in api.call_args_list)
        api.reset_mock()
        status["environments"]["edges"][1] = environment("staging-test", ["proxy-data"])
        fails(backups.main, "exactly one tailscale-state")
        api.assert_not_called()
        status["environments"]["edges"][1] = environment("staging-test", ["proxy-data", "proxy-data", "tailscale-state"])
        fails(backups.main, "exactly one proxy-data")
        api.assert_not_called()

    for script in ("enable_admin.py", "import_auth.py"):
        with patch.object(railway_target, "bound_target", side_effect=SystemExit("binding guard")), \
                patch("sys.argv", [script]), patch("subprocess.run") as uploads:
            fails(lambda: runpy.run_path(str(Path(__file__).with_name(script))), "binding guard")
            uploads.assert_not_called()

print("PASS: linked targets, secret binding/rotation/preflight, selected-environment backups, credential upload guards")
