FROM eceasy/cli-proxy-api:v8.0.15@sha256:ebc2ffc189cf241ff589cd9237c63ca9feba3c9b87fe6213ab9a0b642df132ae
ADD --checksum=sha256:866bae020785b59126a209e89389b77f673fd791beb2208ea650dcc07b3a108d https://github.com/router-for-me/Cli-Proxy-API-Management-Center/releases/download/v1.25.3/management.html /CLIProxyAPI/static/management.html
ENV MANAGEMENT_STATIC_PATH=/CLIProxyAPI/static
COPY core/start.sh /usr/local/bin/start-proxy
ENTRYPOINT ["/bin/sh", "/usr/local/bin/start-proxy"]
