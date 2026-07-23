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

- **Confirm the upstream compose file hasn't changed** — this template is transcribed
  from GL.iNet's own reference as of when this repo was written, not vendored as a file
  dependency. Diff against
  [the live version](https://github.com/gl-inet/glkvm-cloud/blob/main/docker-compose/docker-compose.yml)
  before deploying.
- **Set real values** for `RTTYS_TOKEN`, `RTTYS_PASS`, `TURN_USER`/`TURN_PASS` (must match
  between `rttys` and `coturn`), and `GLKVM_ACCESS_IP`.
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
