# Private management access

The existing Twingate connector is in another Railway project. Railway private
networks are scoped to one project/environment. A new Twingate remote network,
connector credentials, and DNS resource would be needed here. The requested
fallback is a Tailscale Forwarder in this project.

Before enrolling the forwarder, merge the following into your **existing** tailnet
policy, replacing the email with your actual Tailscale identity. Do not replace
the entire policy. Review existing broad rules: grants are additive, so an
existing `*` to `*` rule would still allow other tailnet members to connect.

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
enrollment expiry; the node retains its identity on its Railway volume. Save the
key in `.secrets/tailscale-auth-key`, mode 600. Do not paste it into chat or Git.
Enable MagicDNS and HTTPS certificates in Tailscale's DNS settings. The mapping
is `https:8317:core.railway.internal:8317`: the forwarder terminates TLS inside
the tailnet and reaches the core through Railway's private network. The existing
TCP 8317 grant stays valid; no new port is opened.

The private dashboard address for this deployment is
`https://cliproxy-admin.tail55db0.ts.net:8317/management.html`.
Use the full DNS name: the short hostname and IP address do not match the
certificate. This is not a public Railway domain. Login additionally requires
`MANAGEMENT_PASSWORD`. The forwarder obtains and renews its certificate through
Tailscale's local certificate flow; certificate verification remains enabled.
The certificate hostname appears in public Certificate Transparency records,
but service access remains private to the tailnet. The former HTTP URL is no
longer served; update bookmarks to HTTPS rather than bypassing browser warnings.
No subnet routes, exit node, public TCP proxy, or Tailscale Funnel are required.

Verify access from your authorized device, and denial from another tailnet
identity if one exists. Save policy changes in your tailnet's existing policy
repository; this file is a merge snippet, not authoritative live policy.

Current deployment: `tag:cliproxy-admin` is now verified on the existing node
after the user assigned it in the admin console. Dashboard access and its
additional password check still pass. The full policy and denial from another
identity have not been independently verified; a tag alone does not establish
which grants match. The node still reports key expiry on 2027-03-05. Do not
assume replacing `TS_AUTHKEY` retags or reauthenticates a node already using its
persistent state.

Run `uv run --no-project python scripts/check_private.py` to verify connectivity,
dashboard content and management authentication, and display current node tags
and expiry without printing secrets.

Sources: [Railway private networking](https://docs.railway.com/networking/private-networking),
[Forwarder](https://github.com/brody192/tailscale-forwarder),
[Tailscale grants](https://tailscale.com/docs/features/grants),
[HTTPS certificates](https://tailscale.com/docs/how-to/set-up-https-certificates),
[auth keys](https://tailscale.com/docs/features/access-control/auth-keys).
