#!/bin/sh
set -eu
for name in PROXY_API_KEY UPSTREAM_API_KEY; do
  eval 'value=${'"$name"':-}'
  case "$value" in ''|*[!a-zA-Z0-9_-]*) echo "$name must contain only letters, digits, underscore or hyphen" >&2; exit 1;; esac
  [ "${#value}" -ge 32 ] || { echo "$name must be at least 32 characters" >&2; exit 1; }
done
: "${UPSTREAM_HOST:?UPSTREAM_HOST is required}"
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
