# Deployment record — 2026-09-06

[Railway project](https://railway.com/project/026a2a3c-6ff3-45c5-a5f2-41df123b0bb1)

| Item | Value |
| --- | --- |
| Project | `cliproxyapi` / `026a2a3c-6ff3-45c5-a5f2-41df123b0bb1` |
| Workspace | `75ca093d-3a79-410b-979e-00c31c698666` |
| Environment | `production` / `1c70fd00-9321-4e78-84b9-f4962873206a` |
| Region | Singapore / `asia-southeast1-eqsg3a` |
| OpenAI API base | `https://gateway-production-9f79.up.railway.app/v1` |
| Claude Code base | `https://gateway-production-9f79.up.railway.app` (no `/v1`) |
| Gateway service | `423d8b1a-4fb3-44f2-8bfa-0ce735e17ce1` |
| Core service | `99fd589b-ef3a-4963-88c9-439435752e50` |
| Admin service | `839cc6e0-b016-4583-8cfb-caf479fc72aa` |
| Core volume | `proxy-data` / `2d084eb8-b1ff-461a-97ed-dab95c8d595b` |
| Core volume instance | `40ab84e3-e8a9-492e-8bbb-d47bc7665bb0` |
| Tailscale volume | `tailscale-state` / `d7d2fef9-5e0d-4584-bb6f-6b0023282c0d` |
| Tailscale volume instance | `a34e8960-781b-4846-901d-9ed4364118fb` |
| Gateway deployment | `cbc6f99c-0ae8-4af7-80d4-315314eef482` — SUCCESS |
| Core deployment | `d8d13fa4-73ad-437d-bc15-69c81ef08d7f` — SUCCESS |
| Admin deployment | `51772483-0947-47b9-a166-06907c800b83` — SUCCESS (HTTPS) |
| Private dashboard | `https://cliproxy-admin.tail55db0.ts.net:8317/management.html` |
| Tailscale node ID | `nLMD9pasVs11CNTRL` |

## Verified

- Native Railway IaC plan reports no changes after apply.
- 98 local security checks pass using Caddy 2.11.4 and an HTTP mock backend.
- Public HTTPS: management, OAuth, debug, root and health paths return 404,
  including with the valid inference key. Missing/wrong keys return 401.
- Authenticated `/v1/models` returned 200 with 41 advertised models immediately
  after import; the latest verification returned 40. This list is dynamic and
  is not proof that every advertised model has usable upstream entitlement.
- Real `gpt-5.6-luna` completion returns `OK`; SSE response returns data and
  `[DONE]`. Both requests return 200.
- Claude/Fable inference and architecture consultation completed through Claude
  Code against the new gateway. Advertised model ID is `claude-fable-5-1`.
- Three existing credential files (Claude, Codex, xAI) copied through SSH and
  verified mode 600. Credential contents were not printed or committed.
- Persistent config and checksum-pinned dashboard verified inside the core.
- Core and admin have zero public domains. All three services have zero public
  TCP proxies. The gateway domain targets port 8080, not its health port 8081.
- Daily backup schedules read back successfully for both volumes, retention
  `518400` seconds (six days). Snapshot restoration has not been tested.
- Tailscale forwarder enrolled and its deployment succeeded. The local client
  was connected using its existing settings. Private dashboard HTTP 200;
  anonymous management API HTTP 401; password-authenticated management API
  HTTP 200. `scripts/check_private.py` reproduces these checks.
- Public boundary checks passed again after enrollment; core/admin still have
  no public domain, and all three services have no public TCP proxy.
- Restarted the admin service. Startup logs at 16:57:59Z and 17:00:41Z establish
  that the process restarted; the node ID remained `nLMD9pasVs11CNTRL` and all
  private access checks passed afterward. The persistent identity volume works.
- The browser's original insecure label came from the HTTP-only dashboard;
  browsers do not recognize Tailscale tunnel encryption as HTTPS. Switched the
  same private port to HTTPS using the native `https:` forwarder
  mapping. Verified TLS 1.3, trusted Let's Encrypt issuer YE1, and a certificate
  matching `cliproxy-admin.tail55db0.ts.net` (expires 2026-12-05 16:29:11 UTC).
  Certificate renewal is handled by the forwarder/Tailscale certificate flow.
  This TLS certificate expiry is separate from the Tailscale node-key expiry.
- HTTPS dashboard returned 200, anonymous management 401 and authenticated
  management 200. Public boundary tests passed again, and IaC plan reports no
  drift. Initial TLS probes during the rollout returned EOF; subsequent curl
  and Python certificate verification and application checks passed. No TLS
  verification bypass was used.
- The former plaintext HTTP URL no longer serves the dashboard. Bookmarks
  must use the full HTTPS hostname; there is no HTTP redirect on port 8317.

## Remaining setup and limitations

### Remote Claude Code diagnosis — 2026-09-07

The remote client reported that `claude-sonnet-5` may not exist or be accessible.
`scripts/test_endpoint_tmp.py` tested that exact model from the setup machine
against public HTTPS using `.secrets/PROXY_API_KEY`: missing key 401; Bearer
and x-api-key model listing 200; selected model advertised; token counting 200;
Messages 200 with response model `claude-sonnet-5`; streaming 200 ending in
`message_stop` without error events. All checks passed. No gateway change was
made. The remote machine's base URL, effective credentials and client settings
have not been verified; this local result does not establish the remote cause.

### Other limitations

- **Machine tag verified.** After the user assigned it in Tailscale,
  `scripts/check_private.py` confirms `tag:cliproxy-admin` on the same node ID,
  dashboard HTTP 200, anonymous management HTTP 401 and authenticated management
  HTTP 200. Node-key expiry remains `2027-03-05T16:57:58Z`; tagging did not
  automatically remove its existing expiry.
- Browser automation still times out, so the full tailnet policy and denial
  from another identity could not be inspected/tested. Only one user identity
  is visible to the local client; this is not proof of the complete tailnet
  membership or policy. No tailnet policy was changed. Local Tailscale is now
  connected and was left running for dashboard access.
- xAI `grok-3-mini` inference returns upstream HTTP 402,
  `personal-team-blocked:spending-limit`. The account requires credits or a
  qualifying subscription. Credential import alone does not establish
  entitlement. No purchase or account change was made.
- Public gateway currently supports the explicit OpenAI/Anthropic text routes
  in its Caddyfile; Gemini-native, media and arbitrary `/v1/*` routes are denied.
- Files are in a local Git repository, without a commit or GitHub remote.
  Deployments use explicit Railway source uploads. No autodeploy is configured.
- The shared key has no per-user rate limit or attribution. Rotate the public
  key promptly if exposed. Native Railway Under Attack Mode challenges browsers
  and can block API clients, so it is not enabled as a generic rate limiter.

## Consultation record

The requested literal model `claude-fable-5.1` failed through the pre-existing
local proxy with HTTP 502 `unknown provider for model claude-fable-5.1`.
Failed Claude session: `6d07c3d5-5575-4e98-bb3d-950bc9de98e5`.

Retry used the provider's advertised `claude-fable-5-1` through the new Railway
gateway. Native exit status 0; session
`706285b0-8371-4488-832b-10edc7fc9c7f` (ephemeral consultation; not persisted for
resume). The native CLI displayed an unrecognized-model warning, but the
provider returned a successful Fable response. The initial persisted session
can be inspected with `claude --resume 6d07c3d5-5575-4e98-bb3d-950bc9de98e5`.

Fable identified tailnet scope, rate limits, token backups and coordinated
internal-key rotation as review areas. The port-specific grant and rotation
procedure are documented. A non-ephemeral forwarder with persistent state is
intentional, matching the reviewed Forwarder implementation; ephemeral nodes
would not preserve the management hostname across restarts. No unreviewed
Caddy plugin was added.
