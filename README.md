# CLIProxyAPI on Railway

Public API base URL: **https://gateway-production-9f79.up.railway.app/v1**

The Caddy gateway accepts the public `PROXY_API_KEY` and forwards only the
explicit inference routes in `gateway/Caddyfile`. The CLIProxyAPI core and
Tailscale management forwarder have **no public domains or TCP proxies**.
The API key gives inference access, never management access.

## Infrastructure

| Resource | Purpose | Exposure / persistence |
| --- | --- | --- |
| `gateway` | Caddy 2.11.4, independent API-key enforcement | HTTPS domain to port 8080; health port 8081 is private |
| `core` | CLIProxyAPI 7.2.152 and dashboard 1.22.14 | Private port 8317; `/data` volume, 1 GiB |
| `admin` | Tailscale Forwarder | Private HTTPS on tailnet port 8317; `/data` identity volume, 512 MiB |

All services run one replica in Railway Singapore. Volumes prevent horizontal
replication; deployments of the core can briefly interrupt inference. Images
are pinned by digest, and the dashboard download is checksum-pinned.

`.railway/railway.ts` is the infrastructure source of truth. Dockerfiles and
startup scripts define runtime behavior. `package-lock.json` pins Railway's IaC
SDK; no application framework or database is needed.

## Reproduce

Requires authenticated Railway CLI (tested 5.43.1), Node >=22, npm, UV, and Caddy
2.11.4 for the local boundary checks. Docker can build the images locally but
is not required for Railway source uploads.

```sh
npm ci --ignore-scripts
railway init --name cliproxyapi --workspace YOUR_WORKSPACE_ID --json
railway config plan
railway config apply --yes
uv run --no-project python scripts/set_secrets.py
uv run --no-project python scripts/check_gateway.py --caddy /absolute/path/to/caddy
railway up --service core --detach
railway up --service gateway --detach
railway domain --service gateway --port 8080 --json
```

Review the plan before apply. `--detach` starts deployment; it does **not** mean
healthy. Check `railway deployment list --service core --limit 1 --json` and the
equivalent gateway command. Then run:

```sh
uv run --no-project python scripts/check_public.py https://YOUR_GATEWAY_DOMAIN
railway config plan --detailed-exit-code
```

For the existing project, use `railway link --project
026a2a3c-6ff3-45c5-a5f2-41df123b0bb1 --environment production` instead of `init`.
Generated Railway domains are not managed by Railway IaC; the explicit domain
command above is the reproducible provisioning step. Never attach a domain to
`core` or `admin`, or point the gateway domain at health port 8081.

## Keys

`scripts/set_secrets.py` creates three independent random keys. They are stored
in ignored `.secrets/` files, mode 600, and uploaded using stdin. It recovers
existing Railway values on a fresh checkout instead of silently rotating them.
Store recovery copies in your password manager; `.secrets/` is not a backup.

| Key | Used by | Share with |
| --- | --- | --- |
| `PROXY_API_KEY` | Gateway | Your inference clients |
| `UPSTREAM_API_KEY` | Gateway → core | Nobody; internal credential |
| `MANAGEMENT_PASSWORD` | Core management API/dashboard | Administrators only |

You can choose your own public key by editing `.secrets/PROXY_API_KEY` to at
least 32 ASCII letters, digits, underscores or hyphens, running
`scripts/set_secrets.py`, and redeploying `gateway`. Update clients afterward.
Keys in URL query strings are not accepted. Use `Authorization: Bearer KEY`
or Anthropic's `X-Api-Key` header. Browser CORS is not enabled; clients making
cross-origin browser requests need an explicit origin policy before adding it.

Public-key rotation does not affect provider subscriptions. To rotate the
internal `UPSTREAM_API_KEY`, **first** add the replacement alongside the old key
through the private dashboard's API Keys settings, then update the secret file,
run `set_secrets.py`, and redeploy core and gateway. Verify inference before
removing the old key from the dashboard. Changing only the Railway variable
breaks authentication because the existing volume retains its configuration.

To rotate management access, change `.secrets/MANAGEMENT_PASSWORD`, run the
secret script and redeploy core. Keep the dashboard's separate `secret-key`
empty; if you set one there, it remains another accepted management credential.

## Private management and subscriptions

Follow [docs/tailscale.md](docs/tailscale.md), then run:

```sh
uv run --no-project python scripts/enable_admin.py
```

Connect your device to Tailscale and open
`https://cliproxy-admin.tail55db0.ts.net:8317/management.html` using
`MANAGEMENT_PASSWORD`. Use the full hostname so it matches the TLS certificate;
the short name and IP address do not. Enable HTTPS certificates in Tailscale's
DNS settings when reproducing this in another tailnet. Run
`uv run --no-project python scripts/check_private.py` to verify
private access. The enrolled node has the verified `tag:cliproxy-admin` tag;
see `docs/tailscale.md` for the access policy and current verification limits.
Authenticate Claude/Codex/xAI accounts through the private management interface
or import your existing CLIProxyAPI auth files. For a new workstation, create and
register a dedicated SSH key in the standard SSH directory (the tested Railway
CLI only discovers keys there):

```sh
ssh-keygen -t ed25519 -f ~/.ssh/cliproxyapi_railway -C cliproxyapi-deployment
railway ssh keys add --key cliproxyapi_railway --name cliproxyapi-deployment
uv run --no-project python scripts/import_auth.py
```

This deployment's key is registered to the Railway user account, not a service
role. Protect it accordingly. On the setup machine it is stored at
`~/.ssh/cliproxyapi_railway`, with an additional ignored local copy at
`.secrets/railway-ssh`; both copies are sensitive. `import_auth.py` preserves existing remote files
and does not overwrite refreshed credentials. It accepts `--providers` and
`--source` to limit an import. Provider OAuth callback routes
remain private; use the dashboard's remote callback/paste flow if the provider
redirects to localhost on your device. Never open callback ports publicly.

Provider auth files contain refresh tokens. Keep `/data/auths` private and avoid
independent copies of the same refresh token being refreshed concurrently if a
provider rotates tokens. Reauthentication is the recovery path for rejected or
expired credentials. An authenticated model list does not prove inference;
verify a small real completion and streaming response after enrollment.

## Claude Code endpoint diagnosis

Copy `scripts/test_endpoint_tmp.py` to the remote machine (Python 3.9+, no
packages), then run:

```sh
python3 test_endpoint_tmp.py --base-url https://gateway-production-9f79.up.railway.app --model claude-sonnet-5
```

The script reads `PROXY_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, or `ANTHROPIC_API_KEY`
in that order, otherwise prompts without echo. Use `--key-file /path/to/key`
to override existing credentials. Never pass the key itself as an argument.
It verifies TLS, unauthenticated rejection, both supported authentication
headers, model listing, token counting, a tiny completion and complete SSE
stream. Inference consumes subscription usage. Exit 0 means all checks passed.

For Claude Code, set `ANTHROPIC_BASE_URL` to the origin above **without `/v1`**,
and `ANTHROPIC_AUTH_TOKEN` to the public proxy key. Clear a conflicting
`ANTHROPIC_API_KEY`, select `claude-sonnet-5`, and inspect `/status` for the
effective endpoint and credential source. Settings-file environment values can
override shell exports. See the [Claude Code gateway guide](https://code.claude.com/docs/en/llm-gateway-connect).

## Persistence, backups and recovery

The core seeds `/data/config.yaml` once and preserves later dashboard edits.
`/data/auths` contains provider credentials. IaC recreates infrastructure and
bootstrap settings; restoring current dashboard settings and subscriptions
requires restoring this volume. Do not casually detach or recreate it.

Apply and verify daily Railway backup schedules with:

```sh
uv run --no-project python scripts/backups.py
```

This preserves any existing additional schedules. Daily retention is six days
in the verified deployment. Backup scheduling is managed through the supported
Railway GraphQL API because the IaC SDK does not expose this setting.
Restore tests are required before calling backups verified. Volume snapshots
contain sensitive credentials; restrict access like a password manager.
For manual exports, use Railway's authenticated volume download or SSH into
the service. Keep exports under `.secrets/` or another encrypted backup location.

Rollback: restore the prior Docker image/config revision and redeploy the same
service with its existing volume. Do not run a destructive IaC apply to roll
back code. If corruption is involved, restore a verified volume backup first.

For changes: review upstream release notes and routes, update pinned digests,
run the local checks, preview IaC, deploy, then run public checks plus a real
inference request. Do not enable unreviewed image auto-updates. Application
request/debug logs are disabled; avoid putting keys in URLs or diagnostics.

The shared public key provides shared access and subscription quotas; it does
not provide per-user accounting or quotas. Request bodies are limited to 32 MiB.
The gateway supports SSE and WebSocket forwarding on the allowed routes.
Railway's Under Attack Mode is not enabled: its browser challenge can reject
normal API clients. No custom Caddy plugin or per-key rate limiter is installed.

## Deployment record and sources

See [docs/deployment.md](docs/deployment.md) for live identifiers and verification.

- [Railway IaC](https://docs.railway.com/infrastructure-as-code/reference)
- [Railway best practices](https://docs.railway.com/overview/best-practices)
- [Railway private networking](https://docs.railway.com/networking/private-networking)
- [CLIProxyAPI release](https://github.com/router-for-me/CLIProxyAPI/releases/tag/v7.2.152)
- [Exact upstream route definitions](https://github.com/router-for-me/CLIProxyAPI/blob/c76dfd4e0edabab9000628b1560ab8ab379eadb8/internal/api/server_routes.go)
- [Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
