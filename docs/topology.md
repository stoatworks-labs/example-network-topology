# Topology

## Theatre nodes (×12)

Each theatre is its own subnet, NAT'd by its own GL-iNet **A-1300 (Slate Plus)** router.
The router runs Tailscale as a subnet router (LAN + WAN side routing enabled), advertising
the theatre's `/24`.

**Physical wiring:** the A-1300 has 1 WAN + 2 LAN gigabit ports. Both LAN ports are used:

- **LAN 1 → ATEM Mini Extreme ISO directly.** Dedicated port, so the router's other LAN
  traffic (rclone syncs, control laptop, etc.) never shares a switch segment with it. The
  ATEM carries the heaviest sustained traffic of any theatre device — the near-real-time
  ISO ingest pull (see [`docs/atem-iso-ingest.md`](atem-iso-ingest.md)) is a continuous
  50-90 Mbps flow, well above BirdDog Play's — so it gets the dedicated port.
- **LAN 2 → 8-port unmanaged Netgear switch**, which fans out to everything else: BirdDog
  Play, PowerPoint Main/Backup, VT Main/Backup, Control laptop (5 devices, 3 spare switch
  ports).

All devices stay on the same `192.168.X.0/24` — this is a physical port split for traffic
separation, not a VLAN/subnet split.

| Role | Address | Physical connection |
|---|---|---|
| GL-iNet A-1300 router (LAN gateway) | `192.168.X.1` | — |
| ATEM Mini Extreme ISO | `192.168.X.2` | A-1300 LAN 1 (direct) |
| BirdDog Play | `192.168.X.20` | Netgear switch → A-1300 LAN 2 |
| PowerPoint Main | `192.168.X.5` | Netgear switch → A-1300 LAN 2 |
| PowerPoint Backup | `192.168.X.6` | Netgear switch → A-1300 LAN 2 |
| VT Main | `192.168.X.7` | Netgear switch → A-1300 LAN 2 |
| VT Backup | `192.168.X.8` | Netgear switch → A-1300 LAN 2 |
| Control laptop | `192.168.X.10` | Netgear switch → A-1300 LAN 2 |

`X` per the subnet map in the [top-level README](../README.md#subnet-map): Theatre 1
→ `2`, Theatre 2 → `3`, ... Theatre 12 → `13`.

The ATEM's built-in FTP server (its ISO recording drive) is pulled continuously by the
mothership over Tailscale subnet routing — see [`docs/atem-iso-ingest.md`](atem-iso-ingest.md).

**Alternative to the GL-iNet router**, documented but not recommended: plain switch +
Tailscale on generic Linux — see
[`docs/topology-alternative-tailscale-switches.md`](topology-alternative-tailscale-switches.md).

## Uplink VLAN grouping

Theatres are grouped 3-per-physical-VLAN purely to organize uplink cabling back to the
mothership — **this grouping does not itself provide cross-theatre isolation**. Each
GL-iNet A-1300 already NATs its own theatre LAN, and once every router joins the same
tailnet, routes are reachable tailnet-wide unless Tailscale ACLs restrict them (see
[`config/tailscale-acl.json`](../config/tailscale-acl.json)).

**These VLANs are venue-supplied, not our infrastructure** — each capped at 1 Gbps, each
port expensive. The 4-VLAN/3-theatres-each split below is safe but conservative; the real
bandwidth math supports consolidating to 2 VLANs (6 theatres each) with genuine margin to
spare — see [`docs/bandwidth-analysis.md`](bandwidth-analysis.md) for the full model and
recommendation.

| VLAN | Theatres | Subnets |
|---|---|---|
| 1 | 1, 2, 3 | .2.x, .3.x, .4.x |
| 2 | 4, 5, 6 | .5.x, .6.x, .7.x |
| 3 | 7, 8, 9 | .8.x, .9.x, .10.x |
| 4 | 10, 11, 12 | .11.x, .12.x, .13.x |

## Mothership — `192.168.1.x`

Ubiquiti **Cloud Gateway**; all 4 VLANs terminate here via separate links. Also hosts the
4× "ready room" computers (physical, untouched) and the hardwired WAN.

**Consolidated services server (Unraid).** Everything else that used to be described as
separate mothership boxes — Nextcloud, Restreamer, the VMix instance, BirdDog Central, the
NDI Discovery Server, a self-hosted DERP server, the ATEM ISO ingest pipeline, the VMix
record ingest pipeline, a self-hosted UniFi Controller, self-hosted GLKVM-Cloud, ATEM
Overseer + ATEM Fleet Admin (fleet monitoring and provisioning for the 12 theatre ATEMs),
and now Flock (BirdDog Play fleet manager) — runs on a single physical server instead,
virtualized with Unraid. The server already
exists (no procurement needed) — known so far: **2× gigabit NICs (bonded — see below), a
"decent" discrete GPU.** Full spec (CPU/motherboard, RAM, exact GPU model) is TBD — see
[`docs/open-questions.md`](open-questions.md) and the calculated target minimum spec
(storage pool layout, RAM, CPU, GPU tier, all worked from this box's actual workload) in
[`docs/server-specification.md`](server-specification.md).

| Workload | Runs as | Notes |
|---|---|---|
| VMix instance | Windows VM, GPU passthrough | Windows-only; benefits from hardware encode |
| BirdDog Central | Windows VM (separate from the VMix VM) | Windows-only ([tech specs](https://birddog.tv/central-techspecs/)); kept on its own VM so it can't take down the live VMix instance if it hangs |
| Nextcloud | Docker container | official image + MariaDB + Redis (see [`config/docker-compose.yml`](../config/docker-compose.yml)) |
| Restreamer | Docker container | official `datarhei/restreamer` image |
| NDI Discovery Server | Docker container | see [`docs/streaming-flow.md`](streaming-flow.md) |
| DERP server | Docker container | self-hosted relay fallback — see [`docs/tailscale.md`](tailscale.md) |
| ATEM ISO Ingest | Docker container | pulls all 12 theatres' ATEM ISO recordings via FTP, dual-writing to Nextcloud and the edit-suite NAS in the same pass — see [`docs/atem-iso-ingest.md`](atem-iso-ingest.md) and [`docs/live-editing.md`](live-editing.md) |
| VMix Record Ingest | Docker container | pulls all 4 VMix PCs' recordings via SMB, same dual-write pattern — see [`docs/vmix-record-ingest.md`](vmix-record-ingest.md) |
| UniFi Controller | Docker container | self-hosted UniFi Network Application — local management/backup console for the Cloud Gateway, independent of cloud.ui.com — see [`config/unifi/README.md`](../config/unifi/README.md) |
| GLKVM-Cloud (`rttys` + `coturn`) | 2 Docker containers | self-hosted remote administration (web UI + SSH terminal) for the 14 GL-iNet routers — see [`docs/glkvm-cloud.md`](glkvm-cloud.md) |
| ATEM Overseer | Docker container | fleet monitoring/tally dashboard for all 12 theatres' ATEMs — receives each theatre's monitoring stream, see [`docs/bandwidth-analysis.md`](bandwidth-analysis.md) |
| ATEM Fleet Admin | Docker container | bulk ATEM provisioning — model-aware config forms, live network apply via `atem-connection` over the same Tailscale subnet routing the ISO ingest pipeline uses, or XML+media folder export |
| Flock | Docker container | BirdDog Play fleet manager — LAN discovery, tag-based grouping, BirdUI-parity settings, batch edits; receives each theatre's BirdDog Play preview stream, see [`docs/bandwidth-analysis.md`](bandwidth-analysis.md) |
| Tailscale subnet router | Docker container, host networking | advertises `192.168.1.0/24`; replaces the earlier "Nextcloud host" plan now that Nextcloud itself is a container on this same box |

**Bonded NICs.** Decided: bond the 2 gigabit NICs (802.3ad/LACP) rather than split traffic
across them — SRT bandwidth isn't constant, and LACP's hash-based distribution spreads the
many *simultaneous* flows this box handles (12 theatres' SRT fan-out, each to a different
destination, the 12 incoming Overseer monitoring streams and Flock SRT previews, plus
rclone/Nextcloud/BirdDog Central/NDI Discovery Server/DERP traffic)
across both links by destination-IP/port hash — giving real aggregate headroom for bursty
traffic, not just failover. Note this does **not** speed up any single flow; the benefit
comes from having many distinct flows to hash across.

**Assuming the Cloud Gateway supports LAG** on the ports the Unraid server lands on (only
UDM Pro/SE/Pro Max, UXG Enterprise, and EFG support port aggregation — not base Cloud
Gateway models). If it turns out this one doesn't: drop an intermediate LACP-capable
switch in between and bond through that instead — the bond doesn't care which device
terminates it, only that something in the path speaks LACP, so this is a cheap fallback
rather than a blocker.

One thing that does need doing regardless of which device terminates the bond: **LACP
rate/hash policy must match on both ends.** Ubiquiti gear hardcodes LACP rate `fast` and
hash policy `layer3+4`; Unraid's bonding defaults differ (`slow` rate, layer2 hash) and
need to be set to match, or the bond won't form correctly.

**Why Unraid over TrueNAS SCALE:** both now support Docker and GPU-passthrough VMs, but
this box needs two GPU/Windows-adjacent VMs alongside several containers, and Unraid has
the more mature, better-documented GPU passthrough workflow plus a more polished one-click
container experience (Community Applications) — useful since this may be maintained on-site
by AV staff rather than a Linux admin. Trade-off: Unraid requires a paid license (Lifetime
tier is a $129 one-time cost); TrueNAS SCALE is free. Only VMix needs the passthrough GPU —
BirdDog Central is NDI routing/control, not video encode, so it runs as a plain VM.

**Tailscale note:** Cloud Gateway (UniFi-OS-based) generally can't run Tailscale natively
without an unofficial container hack, so the mothership subnet-router role runs as a
container on the Unraid box instead of the Cloud Gateway itself. See
[`docs/open-questions.md`](open-questions.md).

## VMix nodes (×2)

Each has its own **GL-iNet A-1300** router (same model as the theatre routers) and its
own Tailscale connection — a separate node on the tailnet, not part of the theatre it
physically sits next to, just uplinked near it:

| Node | Uplinks near | Subnet | Contents |
|---|---|---|---|
| VMix Node 1 | Theatre 1 | `192.168.20.x` | 4× BirdDog P400 cameras, 2× VMix PCs |
| VMix Node 2 | Theatre 4 | `192.168.21.x` | 4× BirdDog P400 cameras, 2× VMix PCs |

That makes **14 GL-iNet A-1300s total** across the network — 12 theatre routers plus these
2. Both LAN ports are bridged together on the VMix node routers (unlike the theatre
routers, there's no single traffic-sensitive device here that needs its own dedicated
port the way the ATEM does).

Each VMix PC's own recording is pulled to the mothership the same way the ATEMs'
recordings are — near-real-time, over this node's own dedicated uplink (not the adjacent
theatre's) — see [`docs/vmix-record-ingest.md`](vmix-record-ingest.md).

## Edit suite — `192.168.22.x`

Post-production subsystem at the mothership: 2× MacBook Pro editing workstations, a Mac
mini running the DaVinci Resolve Project Server and Remote Render, and a dedicated
fast-storage NAS, on their own 10GbE LAN — **not** on the Tailscale mesh (same room
as the mothership, no distance for Tailscale to bridge) and not sharing the theatre-facing
network's bandwidth budget. Routed to the mothership LAN only so the ingest containers
can dual-write footage to the edit-suite NAS in the same pull that feeds Nextcloud —
there is no separate recording-pool-to-NAS sync step. Full design, including the storage
and project-server decisions and the DIT physical-media ingest workflow, in
[`docs/live-editing.md`](live-editing.md).

See [`diagrams/topology.svg`](../diagrams/topology.svg) for the full visual layout — every
theatre, every device, every real IP — and [`docs/ip-address-map.md`](ip-address-map.md)
for the same inventory as a text table. Per-device configs: all 14 routers in
[`config/gl-inet/`](../config/gl-inet/), the Cloud Gateway in
[`config/unifi/`](../config/unifi/), and Tailscale in
[`config/tailscale-up-all-devices.sh`](../config/tailscale-up-all-devices.sh).
