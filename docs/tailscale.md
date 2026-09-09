# Private management access

The `admin` service forwards tailnet HTTPS on port 8317 to the core through
Railway's private network. It needs no public domain, TCP proxy, subnet route,
exit node, or Tailscale Funnel. Complete core/gateway setup and secret binding
from the README before enrolling it.

## Tailnet policy and enrollment

Merge this snippet into your **existing** tailnet policy, replacing the email
with your Tailscale identity. Do not replace the whole policy. Grants are
additive: an existing broad allow rule can still give other members access.

```json
{
  "tagOwners": {"tag:cliproxy-admin": ["autogroup:admin"]},
  "grants": [{
    "src": ["YOUR-TAILSCALE-EMAIL"],
    "dst": ["tag:cliproxy-admin"],
    "ip": ["tcp:8317"]
  }]
}
```

Create a non-ephemeral auth key carrying `tag:cliproxy-admin` in
[Tailscale Keys](https://login.tailscale.com/admin/settings/keys). Use a short
enrollment expiry. Save it in `.secrets/tailscale-auth-key`, mode 600; do not
paste it into Git or command arguments. Enable MagicDNS and HTTPS certificates
in Tailscale's DNS settings, then run:

```sh
uv run --no-project python scripts/enable_admin.py
railway deployment list --service admin --limit 1 --json
```

The script uploads the enrollment key via stdin and starts deployment. Wait for
success. The configured mapping is
`https:8317:${{core.RAILWAY_PRIVATE_DOMAIN}}:8317`; TLS terminates inside the
tailnet and traffic reaches core over Railway's private network. Admin's
persistent `/data` volume and `TS_EPHEMERAL=false` retain its identity.

## Connect and verify

Connect your device to Tailscale and find the full DNS name of `cliproxy-admin`
in the Tailscale admin console. Open:

```text
https://cliproxy-admin.YOUR_TAILNET.ts.net:8317/management.html
```

Use `MANAGEMENT_PASSWORD` from your private secret file. The hostname must match
the certificate: do not use the short name or IP, or disable TLS verification.
Tailscale/Forwarder obtains and renews the HTTPS certificate. The hostname
appears in Certificate Transparency records, while service access stays private.

```sh
uv run --no-project python scripts/check_private.py
```

This discovers the online `cliproxy-admin` peer from the local client and checks
trusted HTTPS, dashboard content, anonymous management rejection, and password
acceptance. It prints the node's tags and expiry without printing credentials.
It expects one matching online peer; keep the configured hostname unique in
your tailnet.

Confirm `tag:cliproxy-admin` is attached, review the effective policy, and test
denial from another identity. A tag or a successful authorized connection alone
does not prove isolation. Store the full policy in your existing tailnet policy
repository; this snippet is not authoritative live policy.

Node-key expiry and enrollment-key expiry are separate. Inspect node expiry and
plan reauthentication when required. Replacing `TS_AUTHKEY` does not necessarily
retag or reauthenticate a node already using persistent state. Save operational
hostnames, node IDs, and verification records in ignored `.secrets/` notes.

## References

- [Railway private networking](https://docs.railway.com/networking/private-networking)
- [Tailscale Forwarder](https://github.com/brody192/tailscale-forwarder)
- [Tailscale grants](https://tailscale.com/docs/features/grants)
- [HTTPS certificates](https://tailscale.com/docs/how-to/set-up-https-certificates)
- [Auth keys](https://tailscale.com/docs/features/access-control/auth-keys)
