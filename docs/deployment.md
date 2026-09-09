# Deployment and recovery

## Existing deployments

Link the intended project and environment, then inspect the result:

```sh
railway link --project YOUR_PROJECT_ID --environment YOUR_ENVIRONMENT_ID
railway status
```

`set_secrets.py` binds `.secrets/` to that project/environment. A fresh checkout
without local keys recovers existing Railway values instead of rotating them.
If you already have local key files but no `.secrets/railway-target.json`, run
the one-time binding command with the IDs you have verified:

```sh
uv run --no-project python scripts/set_secrets.py --bind YOUR_PROJECT_ID YOUR_ENVIRONMENT_ID
```

Binding verifies the target and existing local/remote key agreement; it does
not upload variables or deploy. If the local files belong to another target,
use a separate checkout instead of rebinding them. After binding, normal
`set_secrets.py` runs allow intentional rotation of edited local keys; follow
the coordinated rotation steps in the README.

The operational helpers read the nearest linked project from Railway CLI's
local configuration and validate its IDs against Railway. They require the
standard local `railway login` / `railway link` workflow and reject conflicting
project-token/target environment overrides. They do not silently relink projects.

## Deployment checklist

1. Review `railway config plan` before applying infrastructure changes.
2. Run local regression and gateway checks from the README.
3. Upload only the intended services with `railway up --service SERVICE --detach`.
4. Wait for the latest deployments to succeed; a detached upload is not a health check.
5. Confirm core/admin have no public domains or TCP proxies, and gateway HTTPS
   targets 8080. Keep the gateway health port 8081 private.
6. Run `check_public.py` with the explicit gateway origin. From your authorized
   tailnet device, run `check_private.py`; separately test denial from an
   unauthorized identity to validate the tailnet policy.
7. Run `check_endpoint.py` with your origin and model to verify real completion
   and streaming. An authenticated model list alone is insufficient.
8. Run `railway config plan --detailed-exit-code` and investigate unexpected drift.

## Persistence and backups

Core seeds `/data/config.yaml` once and preserves subsequent dashboard edits.
`/data/auths` holds provider credentials; admin's `/data` holds its tailnet
identity. Do not casually recreate or detach either volume.

Enable and read back daily backup schedules for both expected volumes in the
**currently linked environment**:

```sh
uv run --no-project python scripts/backups.py
```

The script preserves additional schedule kinds and fails if `proxy-data` or
`tailscale-state` is missing. It uses Railway's GraphQL API because the IaC SDK
does not manage backup schedules. Read the returned retention values rather
than assuming a fixed retention period. Test a restoration before treating
backup recovery as verified.

Volume snapshots contain credentials. Restrict access like a password manager.
For manual exports, use authenticated Railway volume download or SSH and store
exports under `.secrets/` or in an encrypted backup location.

Rollback by restoring the prior image/config revision and redeploying the same
service with its existing volume. Do not use a destructive IaC apply to roll
back code. Restore a verified snapshot first if the volume itself is corrupted.

## Private notes and publication

Keep actual URLs, project/workspace/environment IDs, tailnet hostnames, deployment
records, and account-specific troubleshooting in ignored `.secrets/` files.
For example, `.secrets/deployment.md` can hold your runbook and
`.secrets/deployment.env` can hold private endpoint variables passed explicitly
to the check scripts. Keep these shell variables unexported so they do not
conflict with Railway's linked-context safeguards. Do not store literal secrets
in command examples or shell history.

`.gitignore` and `.dockerignore` exclude `.secrets/`. Git does not back it up;
keep an encrypted recovery copy elsewhere. Before removing personal information
from tracked files, preserve the originals privately and verify the copies.

Before making a previously private repository public, inspect **all Git history**
as well as current files. Removing a value in a later commit does not erase
older commits. Sanitize the history or publish a clean snapshot if those
historical details should remain private. Rotate any credentials discovered in
history; deleting their text alone does not revoke them.

## References

- [Railway CLI](https://docs.railway.com/guides/cli)
- [Railway IaC reference](https://docs.railway.com/infrastructure-as-code/reference)
- [Railway private networking](https://docs.railway.com/networking/private-networking)
- [CLIProxyAPI pinned release](https://github.com/router-for-me/CLIProxyAPI/releases/tag/v7.2.152)
