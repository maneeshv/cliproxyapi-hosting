FROM eceasy/cli-proxy-api:v7.2.152@sha256:02b3bb12d866cfc8255b5ee066eee86ad425669da6a79de5b55569eddbe48ba8
ADD --checksum=sha256:8237ceaed15aab4ae5d4d6ecdfe73c3bbd6591de6995397c2f1ac418fd053c08 https://github.com/router-for-me/Cli-Proxy-API-Management-Center/releases/download/v1.22.14/management.html /CLIProxyAPI/static/management.html
ENV MANAGEMENT_STATIC_PATH=/CLIProxyAPI/static
COPY core/start.sh /usr/local/bin/start-proxy
ENTRYPOINT ["/bin/sh", "/usr/local/bin/start-proxy"]
