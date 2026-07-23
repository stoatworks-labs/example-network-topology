# config/

Generated/template configuration for every device and service in this design. Each
subdirectory has its own README with the specifics — this file is just about
[`docker-compose.yml`](docker-compose.yml), the one file that brings up the entire
consolidated services server (Unraid) at once.

## `docker-compose.yml` — the full mothership stack

Every Docker workload in [`docs/topology.md`](../docs/topology.md)'s "Workload / Runs as"
table, in one file: Nextcloud (+ MariaDB + Redis), Restreamer, the NDI Discovery Server,
the DERP server, ATEM ISO Ingest, VMix Record Ingest, the UniFi Controller (+ MongoDB),
GLKVM-Cloud (`rttys` + `coturn`), ATEM Overseer, ATEM Fleet Admin, Flock, and the
Tailscale subnet router. The two Windows VMs (VMix instance, BirdDog Central) aren't
here — they're VMs, not Docker, see `docs/topology.md`.

**ATEM Overseer, ATEM Fleet Admin, and Flock are separate projects** (not built from
source in this repo — `github.com/allansargeant/atem-overseer`,
`github.com/allansargeant/atem-fleet-admin`, and `github.com/allansargeant/flock`), so
their `docker-compose.yml` entries use placeholder image references (`ghcr.io/...:latest`,
clearly marked) rather than a confirmed published tag — check their own repos for the
real image/registry before deploying.

Each service also has its own doc with the full design rationale
([`docs/atem-iso-ingest.md`](../docs/atem-iso-ingest.md),
[`docs/vmix-record-ingest.md`](../docs/vmix-record-ingest.md),
[`docs/glkvm-cloud.md`](../docs/glkvm-cloud.md), [`docs/tailscale.md`](../docs/tailscale.md))
— this file just assembles the deployment. A few pieces (GLKVM-Cloud, the two ingest
scripts) also have their own standalone deployment file/instructions in their own
subdirectory, for running that one piece in isolation instead of the whole stack.

## Before running

1. `cp .env.template .env`, fill in every `REPLACE_ME` value. `.env` is gitignored —
   never commit real credentials.
2. Set `MACVLAN_PARENT` to the real bonded interface name on this box (likely `bond0`
   per the LACP setup in `docs/topology.md`, but confirm against the actual box, not
   assumed here).
3. Generate [`vmix-record-ingest/rclone.conf`](vmix-record-ingest/generate-rclone-conf.sh)
   before starting `vmix-record-ingest` — it's bind-mounted in, not generated at
   container start.
4. Bring the stack up, then run each ingest pipeline's
   `setup-nextcloud-external-storage.sh` once Nextcloud itself is reachable — see
   [`docs/deployment-runbook.md`](../docs/deployment-runbook.md) Phase 6 for the full
   sequence (this matters — running it too early, before Nextcloud has initialized,
   will fail).

## Running

```sh
docker compose up -d
```

## Design notes worth knowing before editing this file

- **Two network types.** `macvlan-mothership` gives most services a real, independently
  routable LAN IP (matches [`docs/ip-address-map.md`](../docs/ip-address-map.md) exactly)
  — the same pattern used throughout this repo. `internal-db` is a non-routed bridge
  network for the two database sidecars (`nextcloud-db`, `unifi-db`) plus
  `nextcloud-redis` — they're implementation details of their parent service, not
  independently-addressed network devices, so they don't get macvlan IPs or an
  `ip-address-map.md` entry. `nextcloud` and `unifi-network-application` are attached to
  **both** networks (their public macvlan identity, plus the internal bridge to reach
  their own DB).
- **No `ports:` mappings anywhere.** Macvlan-attached containers already have a real L3
  address on the physical LAN — Docker's `ports:`/host-publishing mechanism is for
  bridge-networked containers going through the host's own NAT, and doesn't apply here.
  Every service is reachable directly at its documented IP on whatever it natively
  listens on (this is also why Restreamer's per-stream SRT/RTMP ports, created
  dynamically through its own UI/API, need no compose-level config at all).
- **Not independently verified against a real deployment**: the NDI Discovery Server
  image (`pnxr/ndi-discovery-minimal`, a community build, not NDI/NewTek-published), the
  UniFi Controller's required MongoDB version (drifts with the controller version —
  check linuxserver's own compatibility notes before deploying), and everything already
  flagged in `docs/glkvm-cloud.md` (the `GLKVM_ACCESS_IP` WAN-remap question). None of
  these have been run against real hardware — see
  [`docs/open-questions.md`](../docs/open-questions.md) for the full list of what's
  confirmed vs. assumed across this whole design.
