# Deployment runbook

Ordered build sequence synthesizing every doc/config in this repo into one checklist.
Each step links to the doc with the actual detail — this is a map, not a duplicate.

## Phase 0 — Before touching anything

- [ ] Confirm the consolidated server's full spec (validated ECC, PCIe lanes for the
      NVMe pools, RAM/cores — no GPU/IOMMU checks needed any more) —
      [`docs/open-questions.md`](open-questions.md) #1
- [ ] Confirm the Cloud Gateway model (LAG support assumed, not confirmed) —
      [`docs/open-questions.md`](open-questions.md) resolved-items section
- [ ] Decide a real hostname/DDNS for the DERP server and confirm you can port-forward on
      the Cloud Gateway — [`docs/tailscale.md`](tailscale.md)
- [ ] Confirm VMix's actual recording mode/bitrate and get SMB sharing set up on all 4 VMix
      PCs — [`docs/vmix-record-ingest.md`](vmix-record-ingest.md)
- [ ] Confirm ATEM FTP credentials and recording path on a real unit —
      [`docs/atem-iso-ingest.md`](atem-iso-ingest.md)
- [ ] Decide a real hostname/DDNS for GLKVM-Cloud and confirm `GLKVM_ACCESS_IP`'s exact
      format for the WAN-remapped ports — [`docs/glkvm-cloud.md`](glkvm-cloud.md)
- [ ] Confirm ATEM Overseer's, ATEM Fleet Admin's, and Flock's real container images, and
      whether the ATEM and BirdDog Play can actually originate their monitoring/preview
      streams alongside their primary feeds — [`docs/open-questions.md`](open-questions.md) #11
- [ ] Settle the live-editing open questions — footage-volume sizing, the Mac mini's
      combined Project Server + Remote Render role, standalone cameras in scope or not —
      [`docs/open-questions.md`](open-questions.md) #12-14

## Phase 1 — Mothership networking (Cloud Gateway)

1. Apply [`config/unifi/network-config.yaml`](../config/unifi/network-config.yaml) via the
   UniFi Network UI/API — 4 uplink VLANs, firewall baseline, LAG port profile, DERP +
   GLKVM-Cloud port forwards. Steps in [`config/unifi/README.md`](../config/unifi/README.md).
2. Wire the 4 VLAN uplink cable runs (3 theatres per group) — [`docs/topology.md`](topology.md#uplink-vlan-grouping).
3. Bond the consolidated server's 2 NICs (802.3ad/LACP) into the Cloud Gateway (or an
   intermediate switch if LAG isn't supported) — [`docs/topology.md`](topology.md), watch
   the LACP rate/hash-policy gotcha with Ubiquiti gear.

## Phase 2 — Consolidated services server (Unraid)

1. Install Unraid.
2. Create the BirdDog Central Windows VM — the design's only VM, no GPU passthrough
   needed — [`docs/topology.md`](topology.md).
3. Bring up every Docker container in one shot with
   [`config/docker-compose.yml`](../config/docker-compose.yml) — Nextcloud, Restreamer,
   NDI Discovery Server, DERP, ATEM ISO Ingest, VMix Record Ingest, UniFi Controller,
   GLKVM-Cloud (`rttys` + `coturn`), ATEM Overseer, ATEM Fleet Admin, Flock, Tailscale
   subnet router. See [`config/README.md`](../config/README.md) for the `.env` setup and
   prerequisites first — DERP and GLKVM-Cloud specifically need their hostnames/
   port-forwards from Phase 0/1 in place before they're actually useful, and ATEM
   Overseer/Fleet Admin/Flock need their real container images confirmed first (see
   [`docs/open-questions.md`](open-questions.md) #11) — DERP and GLKVM-Cloud will start
   but be non-functional without their hostnames/forwards, and the three
   placeholder-image services won't start at all until real images are filled in.
4. Optionally adopt the Cloud Gateway into the UniFi Controller for local management —
   [`config/unifi/README.md`](../config/unifi/README.md). Purely a local console; the
   network config in Phase 1 doesn't depend on it.
5. Router registration into GLKVM-Cloud happens later, in Phase 4, once the routers
   themselves exist.

## Phase 3 — Tailscale tailnet

1. Load [`config/tailscale-acl.json`](../config/tailscale-acl.json) into the tailnet admin
   console — cross-theatre isolation ACLs + the self-hosted DERP region.
2. Run the mothership's `tailscale up` (see
   [`config/tailscale-up-all-devices.sh`](../config/tailscale-up-all-devices.sh)) from the
   Tailscale subnet-router container.
3. Approve routes in the admin console (or configure `autoApprovers`) — nothing routes
   until approved, regardless of what's advertised.

## Phase 4 — Theatre + VMix node routers (GL-iNet A-1300 ×14)

1. Flash/reset all 14 units, apply Wi-Fi lockdown per venue policy (not covered by the
   generated configs).
2. Apply each theatre's UCI config from [`config/gl-inet/`](../config/gl-inet/) — replace
   every `REPLACE_WITH_MAC_nn` with real device MACs first (config won't do anything
   useful otherwise). Steps in [`config/gl-inet/README.md`](../config/gl-inet/README.md).
3. Run each router's `tailscale up` line from
   [`config/tailscale-up-all-devices.sh`](../config/tailscale-up-all-devices.sh).
4. Confirm the physical wiring matches the current plan: ATEM on the dedicated LAN 1 port,
   everything else (including BirdDog Play) via the Netgear switch on LAN 2 —
   [`docs/topology.md`](topology.md).
5. Register each router against GLKVM-Cloud (brought up in Phase 2) using the connection
   script from its web UI, run over SSH on each A-1300 — rides the tailnet already set up
   in step 3, no WAN exposure needed for this part — [`docs/glkvm-cloud.md`](glkvm-cloud.md).

## Phase 5 — BirdDog Play + NDI discovery

1. Change the default `birddog` admin password on all 12 PLAY units.
2. Point BirdDog Central and all 12 PLAY units at the NDI Discovery Server
   (`192.168.1.15:5959`) via BirdUI's Network panel — [`docs/streaming-flow.md`](streaming-flow.md).

## Phase 6 — Nextcloud external storage + ingest pipelines

1. Run [`config/atem-iso-ingest/setup-nextcloud-external-storage.sh`](../config/atem-iso-ingest/setup-nextcloud-external-storage.sh)
   and [`config/vmix-record-ingest/setup-nextcloud-external-storage.sh`](../config/vmix-record-ingest/setup-nextcloud-external-storage.sh)
   — mounts the External Storage folders and prints the cron lines for targeted rescans.
   Add those cron entries.
2. Fill in real credentials and start `pull-iso.py` (or the `rclone-mount-rsync/`
   alternative) — [`config/atem-iso-ingest/README.md`](../config/atem-iso-ingest/README.md).
3. Fill in real SMB credentials/share names and start `mount-and-sync.sh` —
   [`config/vmix-record-ingest/README.md`](../config/vmix-record-ingest/README.md).
4. Configure Nextcloud version-retention for both ingest folders — both ingest docs flag
   this as worth tuning once running for real.
5. **Dual-write caveat**: the second write destination (the edit-suite NAS, see
   [`docs/live-editing.md`](live-editing.md)) is documented but **not yet implemented**
   in either ingest script — implement it or consciously defer it before the event
   ([`docs/open-questions.md`](open-questions.md) #15). As shipped, both scripts write
   only the Nextcloud destination.

## Phase 6b — Live editing subsystem

The edit suite ([`docs/live-editing.md`](live-editing.md)) is its own 10GbE LAN, off the
tailnet, so it can be built any time after Phase 2 — it only depends on the ingest
pipelines (Phase 6) for its footage feed:

1. Stand up the `192.168.22.0/24` 10GbE LAN — switch, edit-suite NAS (`.22.2`), routed
   connection back to the mothership LAN for the dual-write (no Tailscale).
2. Set up the Mac mini (`.22.20`): install DaVinci Resolve Studio + the Project Server
   app, create the shared project library, enable it as a Remote Render node.
3. Connect both MacBook Pros (`.22.11`/`.22.12`) via Thunderbolt-to-10GbE, mount the NAS
   on all three machines with identical paths (Resolve's Remote Render requires the media
   volume mounted on every machine).
4. Run resolve-configurator against the event's session CSV to build the shell project;
   apply each smart-bin recipe once, by hand, in Resolve's UI.

## Phase 7 — Verify before the event

- [ ] `tailscale status` / `tailscale ping` from a few nodes — confirm direct vs relay —
      [`docs/tailscale.md`](tailscale.md)
- [ ] `tailscale netcheck` on a theatre router — confirm the self-hosted DERP region is reachable
      and not blocked by the uplink-VLAN firewall rule — [`docs/open-questions.md`](open-questions.md) #3
- [ ] Copy an ATEM file mid-recording and confirm it opens/scrubs — empirically verify the
      "safe to read mid-write" assumption — [`docs/atem-iso-ingest.md`](atem-iso-ingest.md)
- [ ] Confirm ingested files actually appear in Nextcloud's UI (not just on disk) for both
      pipelines
- [ ] Confirm cross-theatre isolation: from one theatre's subnet, verify you cannot reach
      another theatre's devices, only the mothership — this is the core ACL guarantee the
      whole design depends on ([`config/tailscale-acl.json`](../config/tailscale-acl.json))
- [ ] From off-venue (a network that isn't the mothership's own), confirm the GLKVM-Cloud
      web UI is actually reachable through `https://kvm.example.net:8443`, and that all 14
      routers show up registered and their SSH terminal/web-proxy access works —
      [`docs/glkvm-cloud.md`](glkvm-cloud.md)
- [ ] Confirm all 12 theatres' monitoring/preview streams actually reach ATEM Overseer and
      Flock and show up live in each dashboard — this is the first real-hardware test of
      the dual-stream assumption flagged in
      [`docs/open-questions.md`](open-questions.md) #11
- [ ] Live editing: confirm footage lands on the edit-suite NAS as it's ingested (once
      the dual-write is implemented — see Phase 6 step 5), both editors can open the
      shared show project simultaneously, the smart bins auto-fill as clips arrive, and
      a test export dispatched to the Mac mini via Remote Render completes —
      [`docs/live-editing.md`](live-editing.md)
