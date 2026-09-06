"""Ensure daily backups on this environment's two deployment volumes."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
status = json.loads(subprocess.check_output(["railway", "status", "--json"], cwd=ROOT))
if status["name"] != "cliproxyapi":
    raise SystemExit("Link the cliproxyapi project first")

def api(query, variables):
    output = subprocess.check_output(
        ["railway", "api", query, "--variables", json.dumps(variables)], cwd=ROOT,
    )
    response = json.loads(output)
    if response.get("errors"):
        raise SystemExit(response["errors"])
    return response.get("data", response)

for edge in status["environments"]["edges"]:
    environment = edge["node"]
    if environment["name"] != "production":
        continue
    for item in environment["volumeInstances"]["edges"]:
        volume = item["node"]
        if volume["volume"]["name"] not in {"proxy-data", "tailscale-state"}:
            continue
        variables = {"id": volume["id"]}
        query = "query($id:String!){volumeInstanceBackupScheduleList(volumeInstanceId:$id){kind retentionSeconds}}"
        schedules = api(query, variables)["volumeInstanceBackupScheduleList"]
        kinds = sorted({x["kind"] for x in schedules} | {"DAILY"})
        api("mutation($id:String!,$kinds:[VolumeInstanceBackupScheduleKind!]!){volumeInstanceBackupScheduleUpdate(volumeInstanceId:$id,kinds:$kinds)}", variables | {"kinds": kinds})
        verified = api(query, variables)["volumeInstanceBackupScheduleList"]
        assert "DAILY" in {x["kind"] for x in verified}
        print(volume["volume"]["name"], verified)
