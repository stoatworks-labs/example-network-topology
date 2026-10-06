# GLKVM-Cloud (self-hosted)

Centralized remote administration (web UI + SSH terminal) for the 14 GL-iNet A-1300
routers, via a self-hosted instance of GL.iNet's open-source GLKVM-Cloud instead of their
vendor-hosted `glkvm.com` — no physical KVM hardware involved. Full design rationale and
the WAN port-forward mapping (needed to avoid colliding with the DERP server's own WAN
`443/tcp` + `3478/udp`) is in [`docs/glkvm-cloud.md`](../../docs/glkvm-cloud.md) — read
that first, this is just the deployment file.

This service is also included in [`config/docker-compose.yml`](../docker-compose.yml),
the full-stack file that brings up everything on the consolidated server at once — this
standalone template is for deploying/testing GLKVM-Cloud on its own instead.

## Files

- [`docker-compose.yml.template`](docker-compose.yml.template) — the two-container stack
  (`rttys` = the GLKVM-Cloud app, `coturn` = its TURN relay), each on its own macvlan IP.
  Replace every `REPLACE_ME`/`REPLACE_WITH_*` placeholder before running — none of these
  are real credentials, they're unset on purpose.

## Before running

- **Confirm the upstream compose file hasn't changed** — this template follows GL.iNet's
  own reference (checked against upstream commit `be821d4`, 2026-08-20), adapted to
  macvlan, not vendored as a file dependency. Diff against
  [the live version](https://github.com/gl-inet/glkvm-cloud/blob/main/docker-compose/docker-compose.yml)
  before deploying.
- **Fetch the upstream checkout** both services mount their entrypoint script, config
  templates and default certificate from (`git clone
  https://github.com/gl-inet/glkvm-cloud.git`, then put its path in place of
  `UPSTREAM_DIR`). The image's own entrypoint is bare `rttys` with no config, so without
  these mounts every `RTTYS_*`/`TURN_*` value is silently ignored.
- **Set real values** for `RTTYS_TOKEN`, `RTTYS_PASS`, `TURN_USER`/`TURN_PASS` (must match
  between `rttys` and `coturn`), and `GLKVM_ACCESS_IP` — the venue's **public IPv4**
  (upstream writes it into `rttys`'s `webrtc-ip` and `coturn`'s `external-ip`), not the
  `kvm.example.net` hostname. `TURN_PORT` differs per service on purpose: `3479` on `rttys`
  (the WAN port it advertises), `3478` on `coturn` (what it listens on).
- **Apply the port forwards** in
  [`config/unifi/network-config.yaml`](../unifi/network-config.yaml) before expecting
  remote (off-venue) access to work — LAN access on `192.168.1.20` works regardless.
- **Register each of the 14 routers** against this instance using the connection script
  from the GLKVM-Cloud web UI, once it's up — not this repo's problem to script, since
  it's a one-time action taken from the UI itself, run over SSH on each A-1300.

## Running

1. Fill in every `REPLACE_WITH_...` placeholder in
   [`docker-compose.yml.template`](docker-compose.yml.template).
2. Copy it to `docker-compose.yml` (the `.template` suffix marks the unfilled version;
   only the copy with real values gets a runnable name).
3. Bring it up:

```sh
docker compose up -d
```
