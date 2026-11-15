FROM eceasy/cli-proxy-api:v8.0.72@sha256:7cac48fd7f3ac0b7b6b73508d92179e29454087d9af81eb9a5c9fb50cdd87bc8
ADD --checksum=sha256:035cdd5340a5b9a76cb43d11e45444be1990ae1ecff413d6a92b7e8f03bc6373 https://github.com/router-for-me/Cli-Proxy-API-Management-Center/releases/download/v1.28.0/management.html /CLIProxyAPI/static/management.html
ENV MANAGEMENT_STATIC_PATH=/CLIProxyAPI/static
COPY core/start.sh /usr/local/bin/start-proxy
ENTRYPOINT ["/bin/sh", "/usr/local/bin/start-proxy"]
