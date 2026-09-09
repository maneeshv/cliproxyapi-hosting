"""Ensure daily backups on this environment's two deployment volumes."""
import json
import subprocess

from railway_target import ROOT, linked_target, target_flags


def api(query, variables):
    output = subprocess.check_output(
        ["railway", "api", query, "--variables", json.dumps(variables)], cwd=ROOT,
    )
    response = json.loads(output)
    if response.get("errors"):
        raise SystemExit(response["errors"])
    return response.get("data", response)


def main():
    target = linked_target()
    status = json.loads(subprocess.check_output(
        ["railway", "status", *target_flags(target), "--json"], cwd=ROOT,
    ))
    environments = [edge["node"] for edge in status["environments"]["edges"]
                    if edge["node"]["id"] == target["environment_id"]]
    if status["id"] != target["project_id"] or len(environments) != 1:
        raise SystemExit("Linked Railway project/environment was not found")
    volumes = [edge["node"] for edge in environments[0]["volumeInstances"]["edges"]]
    selected = []
    for name in ("proxy-data", "tailscale-state"):
        matches = [volume for volume in volumes if volume["volume"]["name"] == name]
        if len(matches) != 1:
            raise SystemExit(f"Expected exactly one {name} volume in the linked environment")
        selected.extend(matches)
    for volume in selected:
        variables = {"id": volume["id"]}
        query = "query($id:String!){volumeInstanceBackupScheduleList(volumeInstanceId:$id){kind retentionSeconds}}"
        schedules = api(query, variables)["volumeInstanceBackupScheduleList"]
        kinds = sorted({x["kind"] for x in schedules} | {"DAILY"})
        api("mutation($id:String!,$kinds:[VolumeInstanceBackupScheduleKind!]!){volumeInstanceBackupScheduleUpdate(volumeInstanceId:$id,kinds:$kinds)}", variables | {"kinds": kinds})
        verified = api(query, variables)["volumeInstanceBackupScheduleList"]
        if "DAILY" not in {x["kind"] for x in verified}:
            raise SystemExit(f"Daily backup verification failed for {volume['volume']['name']}")
        print(volume["volume"]["name"], verified)


if __name__ == "__main__":
    main()
