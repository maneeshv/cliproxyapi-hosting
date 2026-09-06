import { defineRailway, preserve, project, service, volume } from "railway/iac";

export default defineRailway(() => {
  const data = volume("proxy-data", { region: "asia-southeast1-eqsg3a", sizeMB: 1024 });
  const core = service("core", {
    replicas: { "asia-southeast1-eqsg3a": 1 },
    healthcheck: "/healthz",
    healthcheckTimeout: 120,
    volumeMounts: { "/data": data },
    env: {
      PORT: "8317",
      TZ: "UTC",
      RAILWAY_DOCKERFILE_PATH: "core/Dockerfile",
      UPSTREAM_API_KEY: preserve(),
      MANAGEMENT_PASSWORD: preserve(),
    },
  });
  const gateway = service("gateway", {
    replicas: { "asia-southeast1-eqsg3a": 1 },
    healthcheck: "/healthz",
    healthcheckTimeout: 60,
    env: {
      PORT: "8081",
      RAILWAY_DOCKERFILE_PATH: "gateway/Dockerfile",
      UPSTREAM_HOST: core.env.RAILWAY_PRIVATE_DOMAIN,
      UPSTREAM_API_KEY: core.env.UPSTREAM_API_KEY,
      PROXY_API_KEY: preserve(),
    },
  });
  const tailscaleState = volume("tailscale-state", { region: "asia-southeast1-eqsg3a", sizeMB: 512 });
  const admin = service("admin", {
    replicas: { "asia-southeast1-eqsg3a": 1 },
    volumeMounts: { "/data": tailscaleState },
    env: {
      RAILWAY_DOCKERFILE_PATH: "admin/Dockerfile",
      TS_HOSTNAME: "cliproxy-admin",
      TS_STATE_DIR: "/data",
      TS_EPHEMERAL: "false",
      TS_AUTHKEY: preserve(),
      CONNECTION_MAPPING_01: "https:8317:${{core.RAILWAY_PRIVATE_DOMAIN}}:8317",
    },
  });
  return project("cliproxyapi", { resources: [core, gateway, admin, data, tailscaleState] });
});
