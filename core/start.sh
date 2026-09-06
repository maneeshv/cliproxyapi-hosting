#!/bin/sh
set -eu
umask 077
for name in UPSTREAM_API_KEY MANAGEMENT_PASSWORD; do
  eval 'value=${'"$name"':-}'
  case "$value" in ''|*[!a-zA-Z0-9_-]*) echo "$name must contain only letters, digits, underscore or hyphen" >&2; exit 1;; esac
  [ "${#value}" -ge 32 ] || { echo "$name must be at least 32 characters" >&2; exit 1; }
done
mkdir -p /data/auths
chmod 700 /data /data/auths
# Retain dashboard settings; the gateway independently enforces the public key.
if [ ! -f /data/config.yaml ]; then
  cat > /data/config.yaml <<EOF
host: ""
port: 8317
auth-dir: /data/auths
api-keys:
  - "$UPSTREAM_API_KEY"
remote-management:
  allow-remote: true
  secret-key: ""
  disable-control-panel: false
  disable-auto-update-panel: true
debug: false
pprof:
  enable: false
plugins:
  enabled: false
ws-auth: true
logging-to-file: false
request-log: false
usage-statistics-enabled: true
request-retry: 2
EOF
fi
chmod 600 /data/config.yaml
exec /CLIProxyAPI/CLIProxyAPI --config /data/config.yaml
