# Open questions

## Resolved

- **Subnet numbering.** Spec said 12 theatres on "192.168.2-12.x", which is only 11
  subnets. Confirmed mapping: mothership on `.1.x`, Theatre 1 → `.2.x` ... Theatre 12 →
  `.13.x` (contiguous after mothership). Used throughout this repo.

- **Mothership router: Ubiquiti Cloud Gateway.** Cloud Gateway (UniFi-OS-based, same
  family as the Dream Machine) generally can't run Tailscale natively without an
  unofficial container hack. Decision: the mothership subnet-router role runs as a
  container on the consolidated services server instead of the Cloud Gateway itself —
  see [`docs/topology.md`](topology.md).

- **Mothership service consolidation: single physical server running Unraid.** Nextcloud,
  Restreamer, BirdDog Central, and the NDI Discovery Server all move
  onto one box instead of being separate machines — the router and the 4 ready-room
  PCs stay physical. BirdDog Central is Windows-only, so it runs as
  the design's one Windows VM — routing/control, not encode, no GPU needed. (An earlier
  revision also carried a mothership VMix instance VM with a passthrough GPU; it was
  removed — see #10 below.) Everything else (Nextcloud, Restreamer, NDI Discovery
  Server, Tailscale subnet
  router) runs as Docker containers. Chose **Unraid over TrueNAS SCALE** for its
  polished one-click container experience (the original GPU-passthrough-maturity
  tiebreaker no longer applies with the VMix VM gone),
  accepting a license cost that TrueNAS (free) doesn't have — as of 2026 Unraid sells
  Starter ($49, up to 6 storage devices) and Unleashed ($109, unlimited) with one year of
  updates then an optional $36/yr, or Lifetime ($249, updates included)
  ([Unraid pricing](https://unraid.net/blog/new-pricing)). The old "$129 Lifetime" figure
  was the pre-2024 Pro price. This build's pools are 6 drives with the mirrored
  recording pool, 8 with RAID-Z1, so Starter is at or over its limit — Unleashed or
  Lifetime. See [`docs/topology.md`](topology.md) for the full breakdown.

- **Theatre router: GL-iNet A-1300 (Slate Plus).** Published client-mode WireGuard
  throughput ≈ 170 Mbps ([GL.iNet A-1300 datasheet](https://static.gl-inet.com/www/images/products/datasheet/a1300_datasheet_20230602.pdf)).
  Each theatre's router only ever carries *its own* theatre's traffic — one incoming SRT
  feed to that theatre's BirdDog Play plus up to 4 laptops' rclone sync — not the
  aggregate across all 12 theatres (that 12x aggregate converges at the mothership's WAN
  link and Restreamer, not at any single theatre router). So the real per-router budget is
  roughly 1× SRT bitrate (~8–50 Mbps depending on resolution/codec) + bursty rclone
  traffic from up to 4 laptops — comfortably inside the A-1300's 170 Mbps headroom.
  *(Caveat: that traffic list predates ATEM ISO ingest and the Overseer/Flock monitoring
  streams, all of which now ride the same router. The current per-router model —
  ~55% of the ceiling in normal operation, 128% during an NDI fallback with ingest
  running, and 98% at worst case during an NDI fallback *with that theatre's ingest
  paused* (the mitigation) — is in [`docs/bandwidth-analysis.md`](bandwidth-analysis.md)'s "check the
  A-1300's own ceiling" section; the router choice still stands, but "comfortably" no
  longer describes the margin.)*

- **VMix node routers: also GL-iNet A-1300.** Same model as the 12 theatre routers — 14
  A-1300s total across the network. Both LAN ports bridge together (no dedicated-port
  split needed here, unlike the theatre routers' BirdDog Play case). Configs generated:
  [`config/gl-inet/vmix-node-1.uci`](../config/gl-inet/vmix-node-1.uci) and
  [`vmix-node-2.uci`](../config/gl-inet/vmix-node-2.uci).

- **NDI backup path discovery.** Confirmed Tailscale can't help directly — it's
  point-to-point WireGuard and doesn't forward multicast/mDNS (a still-open Tailscale
  feature request, not something MagicDNS works around). Plan: run an **NDI Discovery
  Server** on the mothership (unicast TCP, default port 5959 — built into NDI 5+
  specifically for WAN/VPN cases like this), and point BirdDog Central plus all 12
  BirdDog Play units at it. See [`docs/streaming-flow.md`](streaming-flow.md) for the
  full plan.

- **BirdDog Play Discovery Server support — confirmed.** BirdUI (PLAY's web admin) has a
  Network panel with an NDI Discovery Server toggle: switch it on, enter a
  comma-delimited list of server IP(s), apply. BirdDog's own docs describe this as the
  mechanism for finding sources "on different subnets." Sources:
  [BirdDog PLAY User Guide](https://birddog.tv/wp-content/uploads/2022/11/BirdDog-PLAY_User-Guide_231003.pdf),
  [BirdUI User Guide](https://birddog.tv/wp-content/uploads/2024/04/BirdDog_BirdUI_User-Guide.pdf).
  Default admin password (`birddog`) should be changed on all 12 units before the event.

- **Consolidated server: hardware already on hand.** Physical box already exists — no
  procurement needed. Known so far: 2× gigabit NICs, a "decent" discrete GPU. Full spec
  (CPU/motherboard, RAM, exact GPU model) to be confirmed later — a calculated **target**
  minimum spec to check it against (storage pool layout/sizing, RAM, CPU, GPU tier, NIC
  validation, all worked from this box's actual workload rather than guessed) is now in
  [`docs/server-specification.md`](server-specification.md).

- **Full device inventory + configs generated.** Every device on the network now has a
  concrete IP — see [`docs/ip-address-map.md`](ip-address-map.md) (133 devices total) and
  the redrawn [`diagrams/topology.svg`](../diagrams/topology.svg). Configs generated to
  match: [`config/gl-inet/`](../config/gl-inet/) (UCI network config for all 14 routers —
  12 theatres + 2 VMix nodes), [`config/tailscale-up-all-devices.sh`](../config/tailscale-up-all-devices.sh)
  (all 15 tailnet nodes instantiated), and [`config/unifi/`](../config/unifi/) (Cloud
  Gateway VLANs/DHCP/firewall reference).

  Two things introduced *during config generation* that weren't decided before — flagged
  here since they're new, not previously confirmed:
  - **Uplink VLAN transit addressing** (`10.10.1-4.0/24`, VLAN tags 101–104) for the 4
    physical VLAN groups' GL-iNet WAN ports. Doesn't affect anything inside the theatres
    (still NAT'd behind each A-1300) or Tailscale (rides over whatever WAN IP is handed
    out) — purely a Cloud Gateway-side detail. Change freely.
  - **Docker networking mode per mothership service**: Nextcloud/Restreamer/NDI Discovery
    Server/DERP server assigned dedicated IPs via macvlan; Tailscale subnet router uses
    host networking (required for route advertisement, shares the Unraid host's `.2`).
    Both are standard Unraid patterns, not unusual choices, but worth confirming once
    you're actually configuring Docker on the box.

- **2 gigabit NICs: bonded (802.3ad/LACP), not split.** SRT bandwidth isn't constant, and
  this box handles many simultaneous flows (12 theatres' SRT fan-out to distinct
  destinations, plus rclone/Nextcloud/BirdDog Central/NDI Discovery Server/DERP traffic) —
  LACP's hash-based distribution spreads those across both links for real aggregate
  headroom, rather than a static split that leaves one NIC idle whenever traffic doesn't
  match the assumed pattern. See [`docs/topology.md`](topology.md) for the full reasoning,
  the Unraid setup steps, and the LACP rate/hash-policy gotcha with Ubiquiti gear.

- **Self-hosted DERP server added.** Runs as a Docker container on the
  Unraid box (`192.168.1.16`), registered with the tailnet as DERP region 900,
  `RegionCode: "example"`, hostname `derp.example.net`, port **443** (matches Tailscale's own
  DERP fleet, most firewall-friendly choice) — see
  [`config/tailscale-acl.json`](../config/tailscale-acl.json). Kept `OmitDefaultRegions:
  false` so Tailscale's public DERP regions remain available as a fallback if this one
  goes down. See [`docs/tailscale.md`](tailscale.md) for the full setup (container flags,
  port forward, cert handling).

- **Cloud Gateway assumed to support LAG.** *(A working assumption, not a confirmed fact —
  still to verify, see #17.)* Proceeding on that assumption rather than
  confirming the exact model first. Fallback already agreed if it turns out not to:
  drop an intermediate LACP-capable switch in between and bond the Unraid server's NICs
  through that instead of directly into the Cloud Gateway — the bond itself doesn't care
  which device terminates it, only that *something* in the path speaks LACP.

- **ATEM ISO ingest architecture decided, two documented approaches.** Each ATEM's
  built-in FTP server (confirmed live-accessible during recording) is pulled continuously
  by a new Unraid container (`192.168.1.17`) over Tailscale subnet routing. Plain rsync
  can't connect to the ATEM at all (no SSH/rsync daemon), and a naive whole-file re-sync
  is ruled out by the bandwidth math for any real session length — so genuinely
  incremental transfer is required, achieved either via **FTP's `REST`/resume command
  directly** ([`pull-iso.py`](../config/atem-iso-ingest/pull-iso.py), the default — fewer
  moving parts) or via **`rclone mount` + `rsync --append`**
  ([`rclone-mount-rsync/`](../config/atem-iso-ingest/rclone-mount-rsync/) — off-the-shelf
  tools, at the cost of 12 FUSE mounts to supervise). Both write directly into Nextcloud's
  External Storage (Local) mount, so there's no separate upload step and no need to
  slice/chunk the video file itself either way. Full comparison in
  [`docs/atem-iso-ingest.md`](atem-iso-ingest.md).

- **VMix record ingest added, same mechanism as the ATEM ingest.** All 4 VMix PCs'
  recordings pulled by a new Unraid container (`192.168.1.18`) via `rclone mount` +
  `rsync --append`, targeting each PC's Windows SMB share instead of an FTP server. SMB
  is a native network filesystem protocol, so this is arguably a better fit for a
  mount-based approach than the ATEM's FTP-only case was, not a stretch of the same
  pattern. Each VMix node has its own dedicated A-1300 uplink (not shared with the
  theatre it sits near), so this traffic never competes with that theatre's ATEM ingest
  or SRT feed. Full design in [`docs/vmix-record-ingest.md`](vmix-record-ingest.md),
  tooling in [`config/vmix-record-ingest/`](../config/vmix-record-ingest/).

- **Self-hosted UniFi Controller added to the consolidated server.** A UniFi Network
  Application container (`192.168.1.19`) joins the rest of the Docker stack, same
  self-hosted-over-cloud.ui.com rationale already used for DERP. The Cloud Gateway has
  its own built-in controller and doesn't require this — adopting it in is optional,
  purely a local/independent management console, not a change to any traffic path in
  [`config/unifi/network-config.yaml`](../config/unifi/network-config.yaml). See
  [`config/unifi/README.md`](../config/unifi/README.md).

- **Self-hosted GLKVM-Cloud added for centralized administration of the 14 GL-iNet
  routers.** No physical KVM hardware involved — this uses GLKVM-Cloud's separately
  documented HTTP/HTTPS web-proxy and device-management support for embedded OpenWrt
  devices (which the A-1300s are), giving one browser-based SSH terminal + web-admin
  proxy for all 14 routers instead of 14 separate sessions. Same
  self-hosted-over-vendor-cloud rationale as DERP and the UniFi Controller, avoiding
  GL.iNet's own `glkvm.com`. Two containers (`rttys` on `192.168.1.20`, `coturn` on
  `192.168.1.22`); router registration rides the existing tailnet (routers already accept
  routes to `192.168.1.0/24`), no WAN exposure needed for that part. Surfaced a real
  conflict during design: GLKVM-Cloud's documented ports (`443/tcp`, `3478/tcp+udp`)
  collide with the DERP server's existing WAN forwards on those same numbers — resolved
  by forwarding different WAN-side port numbers (`8443`, `3479`) to GLKVM-Cloud's
  unchanged internal ports (for the admin's own browser access), rather than moving DERP
  off 443 and losing its firewall-friendliness rationale. Not yet confirmed against a real
  deployment: whether `GLKVM_ACCESS_IP` (the env var that tells the app what address to
  hand back to clients) accepts this WAN-side remap cleanly, or whether `coturn` needs its
  own separate external-address setting — also unclear whether `coturn`/TURN is needed at
  all for the SSH-terminal/web-proxy features actually in use here, versus only for
  GLKVM-Cloud's KVM-specific remote-desktop feature, which doesn't apply to routers. Full
  design in [`docs/glkvm-cloud.md`](glkvm-cloud.md), stack in
  [`config/glkvm-cloud/`](../config/glkvm-cloud/).

- **Bandwidth modeled against venue-supplied VLANs — 2 VLANs (not 4) recommended, but
  reconsider given how thin that margin has gotten.** The 4 uplink VLANs turned out to
  be venue-supplied, 1 Gbps each, with expensive ports — changes the goal from "isolate
  cleanly" to "minimize VLAN count at adequate performance." Real numbers (last updated
  after adding the Flock BirdDog Play preview stream, ~10.4 Mbps/theatre, on top of ATEM
  Overseer's — see below): per-theatre upstream is dominated by ATEM ISO ingest
  (~62 Mbps realistic of ~88 Mbps total) — at the current 3-theatres-per-VLAN split,
  that's ~27% utilization, with room to consolidate to 2 VLANs (6 theatres each,
  ~53% realistic / 78% worst-case) before it stops being comfortable; **1 VLAN for all 12
  theatres now exceeds capacity even at realistic load (106%)**, not just worst case —
  it's only viable at all if ATEM ingest is deferred to end-of-session pulls instead of
  real-time. Full model in [`docs/bandwidth-analysis.md`](bandwidth-analysis.md).
  *(Note for the 2-VLAN option: both VMix nodes uplink next to Theatres 1 and 4, so under
  a 2-VLAN split they both land in the Theatre 1-6 group, which then runs ~86-90% at
  worst case rather than 78% — see that doc's "VMix nodes' uplinks" section.)*

- **ATEM Overseer + ATEM Fleet Admin added to the mothership.** Two of the user's own
  separate projects, deployed as Docker containers (`192.168.1.21` and `192.168.1.23`)
  alongside everything else — Overseer for fleet-wide monitoring/tally (every theatre's
  ATEM sends it a dedicated 10 Mbps monitoring stream, folded into the bandwidth model
  above as a flat per-theatre addition that doesn't scale with ATEM channel count), Fleet
  Admin for bulk provisioning (reaching all 12 theatres' ATEMs the same way ATEM ISO
  Ingest does, over the existing Tailscale subnet routing). Neither is built from source
  in this repo — `config/docker-compose.yml` uses placeholder image references pending
  confirmation of each project's actual published container image.

- **Flock added to the mothership.** A third of the user's own projects, deployed
  alongside the other two (`192.168.1.24`) — the BirdDog Play fleet manager already
  referenced elsewhere in this design (LAN discovery, tag-based grouping, BirdUI-parity
  settings, batch edits — see [`docs/birddog-play-rationale.md`](birddog-play-rationale.md)).
  Each theatre's BirdDog Play sends Flock a 10 Mbps SRT preview stream (confirmed by the
  user, not assumed), folded into the bandwidth model the same way as the Overseer stream
  — another flat per-theatre addition. Same not-built-from-source caveat as Overseer/Fleet
  Admin above.

- **Live editing subsystem added — new `192.168.22.0/24` subnet, own 10GbE LAN, not on
  the Tailscale mesh.** 2× MacBook Pro editing workstations plus dedicated fast storage
  at the mothership, editing event content as it arrives rather than after the event.
  Deliberately separate from the theatre-facing network — different traffic pattern
  (sustained multi-gigabit editing I/O vs. the bursty low-bitrate streams everything
  else here is sized for) and a genuinely different failure domain. Key decisions made:
  dedicated NAS (not Nextcloud's own storage), dual-write from the same rclone/rsync pull
  already built for ingest rather than a chained re-sync; a dedicated Mac mini running
  both the Resolve Project Server and Remote Render (needed because
  [resolve-configurator](https://github.com/stoatworks-labs/resolve-configurator) builds
  one shared show project both editors work against, not independent copies — confirmed
  **not** possible on a Blackmagic Cloud Store appliance itself, storage-only, no general
  compute); Blackmagic Cloud's internet sync service not needed for a single-venue setup.
  Full design, including the ATEM-pull-to-finished-edit workflow and the DIT
  physical-media ingest tool comparison (ShotPut Pro/OffShoot vs. Silverstack vs.
  FoolCat/o/PARASHOOT as companion tools), in [`docs/live-editing.md`](live-editing.md).

## Still open — verify before building

0. **Measure a real ATEM ISO file's bitrate at the event frame rate — before anything
   else in this list.** *(Numbered 0, not 1, so the long-standing #1-#20 references
   across the repo stay valid.)* The bandwidth model uses 10 Mbps per ISO stream; Blackmagic
   specifies the ATEM Mini Extreme ISO's ISO recordings as H.264 at up to 70 Mb/s (1080p60,
   VBR). If a real file (`ffprobe`, or size ÷ duration) comes in anywhere near that,
   **real-time ISO ingest doesn't fit**: ~364-437 Mbps per theatre for 6 streams (229-272%
   of the A-1300's ~170 Mbps), ~1.2-1.4 Gbps per 3-theatre VLAN, and the 8 TB recording
   pool fills in ~3.5-4 hours. Then decide between: a live pull of the program recording
   only (plus at most one or two key ISOs) with the rest by physical DIT offload
   ([`docs/live-editing.md`](live-editing.md)); ISO pulls between sessions; or faster
   routers and more VLANs. Full recomputed table in the callout in
   [`docs/bandwidth-analysis.md`](bandwidth-analysis.md); knock-on caveat in
   [`docs/server-specification.md`](server-specification.md).

1. **Check the existing server's real spec against the calculated target in
   [`docs/server-specification.md`](server-specification.md).** In particular: does it
   have validated (not merely tolerated) ECC support, enough PCIe lanes for the two
   NVMe pools (up to 6 drives) plus the 10GbE edit-LAN NIC, and enough RAM/cores (target: 12 cores/24 threads, 64-96 GB RAM) to
   run the BirdDog Central Windows VM plus 12 Docker containers concurrently
   without contention during a live event. (GPU passthrough/IOMMU checks dropped from
   this list — nothing needs them since the VMix VM was removed, see #10.)

2. **Actually register/point `derp.example.net`** (or substitute whatever domain/DDNS host
   you end up controlling) at the mothership's public IP, and confirm the WAN port forward
   (443/tcp, 3478/udp) is in place before relying on it — the name and port are picked,
   but nothing resolves until the DNS record and port forward both exist. Upstream's
   `derper` guide also says to permit **80/tcp** (the design forwards only 443 + 3478 —
   decide whether to add it), and that there is no published `derper` package/image:
   `config/docker-compose.yml` now builds it from source, and `-verify-clients` wants
   `derper` and the subnet router's `tailscaled` built from the same release
   ([derper README](https://github.com/tailscale/tailscale/blob/main/cmd/derper/README.md)).

3. **Verify the DERP hairpin path doesn't get caught by the uplink-VLAN firewall block.**
   [`config/unifi/network-config.yaml`](../config/unifi/network-config.yaml) blocks the 4
   uplink VLANs from reaching Mothership-LAN directly (defense-in-depth for cross-theatre
   isolation) — that should be a different path from the DERP hairpin (which arrives via
   the WAN zone after NAT, not directly from an Uplink-VLAN zone), but exact zone/hairpin
   behavior is Cloud-Gateway-firmware-specific. Confirm with `tailscale netcheck` on a
   theatre router once built, before assuming the self-hosted DERP server is actually reachable.

4. **Confirm the real ATEM ISO bitrate/active-channel count, and empirically verify
   partial-file playability.** The bandwidth plan above uses 10 Mbps/stream and an
   assumed 4-6 active channels — the bitrate is now the top open item (#0, vendor spec is
   up to 70 Mb/s per ISO); the active-channel count still needs checking here.
   Whether a file copied mid-recording is genuinely valid (rather than just "very likely,
   given Blackmagic's marketed edit-while-recording capability") should be tested against
   a real unit before relying on it operationally. See
   [`docs/atem-iso-ingest.md`](atem-iso-ingest.md) for the full open-items list, including
   confirming the ATEM's actual FTP credentials/file layout and tuning the pull/scan
   intervals and Nextcloud version-retention settings once this is running for real.

5. **Confirm what VMix is actually recording, and set up real SMB shares/credentials.**
   Neither the recording mode (program mix vs. per-input ISO) nor bitrate/codec, nor the
   actual share name/folder path/account on the 4 VMix PCs, is assumed here — see
   [`docs/vmix-record-ingest.md`](vmix-record-ingest.md) for the full open-items list.

6. **Confirm with the venue: final VLAN count, the full-duplex-1Gbps assumption, and
   whether presenter internet shares the production VLANs or is separate infrastructure.**
   [`docs/bandwidth-analysis.md`](bandwidth-analysis.md) recommends 2 VLANs over the
   current 4, but that's a real cost/procurement decision, not something this repo can
   finalize alone. If real-time ATEM ingest turns out incompatible with the venue's final
   VLAN allocation, deferring it to end-of-session pulls is the fallback — same doc.

7. **Confirm the WAN-remapped GLKVM-Cloud ports (`8443`, `3479`) work end-to-end.**
   Partly answered from upstream's own entrypoint and templates
   ([`docker-compose/`](https://github.com/gl-inet/glkvm-cloud/tree/main/docker-compose)):
   `GLKVM_ACCESS_IP` is written into `rttys`'s `webrtc-ip` *and* `coturn`'s
   `external-ip`, and its auto-detect fallback only accepts IPv4 — so it should be the
   venue's **public IPv4**, not the `kvm.example.net` hostname. `coturn` gets its
   external address from that same variable (no separate setting needed), and `TURN_PORT`
   is both the port `rttys` advertises and the port `coturn` listens on, so the compose
   files now set it per container (`3479` advertised, `3478` listened). Still untested:
   whether the web UI behaves on `:8443`, and what happens if the public IP isn't static. See
   [`docs/glkvm-cloud.md`](glkvm-cloud.md) for the fallback (second public IP or an
   SNI-routing reverse proxy) if the plain env var doesn't cover it. Also confirm whether
   `coturn` is needed at all for the SSH-terminal/web-proxy features actually in use here
   — it may only matter for GLKVM-Cloud's KVM-specific remote-desktop feature, unused
   since there's no KVM hardware in this design.

8. **New assumptions introduced by [`config/docker-compose.yml`](../config/docker-compose.yml)**,
   none confirmed against a real deployment: the NDI Discovery Server image
   (`pnxr/ndi-discovery-minimal`, a third-party community build, not NDI/NewTek-published
   — Docker Hub shows it last pushed 2022-09-18 on NDI SDK 5.5, so treat it as
   unmaintained and pin/fork or replace it), the MongoDB version the UniFi Controller needs
   (drifts with the controller image's own version, not fixed here), and MariaDB + Redis
   as Nextcloud's DB/cache backend (chosen over SQLite — this box has a lot of concurrent
   writers across 12 theatres' rclone syncs plus both ingest pipelines, which official
   Nextcloud guidance says SQLite handles poorly; not benchmarked here either way).

9. **Confirm actual event duration (day count × active-recording hours/day)** before
   treating the 8 TB recording pool in
   [`docs/server-specification.md`](server-specification.md) as settled — that document
   calculates it covers roughly 15-21 hours of continuous worst-to-realistic-case
   load (~1.5-2.5 typical event days) — at the 10 Mbps/stream basis; only ~3.5-4 hours if
   ISO files are near Blackmagic's spec (#0), but this repo doesn't establish the event's real
   length anywhere. If it runs longer without a periodic archive-off step, either the
   pool needs to grow or an offload step needs adding to the ingest design.

10. **Resolved — by removal.** This slot used to ask what the mothership's own VMix
    instance VM actually did (its role was never established anywhere in this repo,
    unlike the well-documented VMix *node* PCs). The answer arrived as a design change:
    **the mothership VMix VM was removed entirely.** The theatre program feeds originate
    from the VMix node PCs via Restreamer (`docs/streaming-flow.md`), which never
    depended on it. Knock-ons all applied: no GPU/passthrough/IOMMU requirement remains
    anywhere in the spec, RAM/CPU budgets dropped (see
    `docs/server-specification.md`), BirdDog Central is now the design's only VM, and
    the device count is 133. (Number kept so cross-references to #11-#15 stay stable.)

11. **Confirm ATEM Overseer's, ATEM Fleet Admin's, and Flock's actual published container
    images** (or that they need to be built from source instead) before deploying
    `config/docker-compose.yml` — all three use placeholder `ghcr.io/...` references.
    Also confirm the actual mechanism behind both monitoring streams
    `docs/bandwidth-analysis.md` takes as given inputs, not verified against real
    hardware: Overseer's 10 Mbps ATEM stream (does the ATEM Mini Extreme ISO genuinely
    support two independent simultaneous stream outputs — its own hardware streaming
    engine feeding both Restreamer and Overseer at once?), and Flock's 10 Mbps BirdDog
    Play preview stream (same question for BirdDog Play — decoding its primary program
    feed while simultaneously *originating* a second SRT stream back to Flock is a
    different capability than the receive-only role it plays everywhere else in this
    design).

12. **Decide how much of the event's footage the live-editing subsystem actually needs
    access to** — the full 8TB recording pool, or a curated subset — before sizing the
    edit-suite NAS in [`docs/live-editing.md`](live-editing.md) Decision 1.

13. **Confirm combining Project Server and Remote Render on one Mac mini holds up under
    real load** — [`docs/live-editing.md`](live-editing.md) Decision 2 treats this as
    architecturally sound but thinly documented by both Blackmagic and practitioners;
    worth a real pre-event test, not just a design-time assumption.

14. **Confirm whether this event uses any standalone cameras with SD/CFexpress cards**
    beyond the NDI-fed BirdDog P400s — affects whether the DIT physical-media ingest
    workflow in [`docs/live-editing.md`](live-editing.md) has real camera cards to
    process beyond the ATEM's own USB SSD, and whether Silverstack's deeper
    metadata/lens-data feature set becomes worth its cost over ShotPut Pro/OffShoot.

15. **Implement the second write destination in the actual ingest scripts.**
    [`docs/live-editing.md`](live-editing.md) documents `pull-iso.py` and
    `mount-and-sync.sh` writing to the edit-suite NAS alongside Nextcloud — that's a real
    code change neither script has yet
    ([`config/atem-iso-ingest/pull-iso.py`](../config/atem-iso-ingest/pull-iso.py),
    [`config/vmix-record-ingest/mount-and-sync.sh`](../config/vmix-record-ingest/mount-and-sync.sh)
    currently write one destination each). Not done as part of documenting the design.

16. **Verify the settled NDI-redistribution feed into BirdDog Central.** The mechanism
    is decided ([`docs/streaming-flow.md`](streaming-flow.md)): the source VMix node
    PC's native NDI output → NDI Discovery Server registration → Central receives over
    that node's uplink (fallback-only ~130 Mbps against the ~170 Mbps ceiling, with
    that node's record ingest paused for the duration) → Central re-sends to the
    theatre PLAYs. The alternatives were researched and ruled out: Restreamer cannot
    emit NDI (upstream FFmpeg removed NDI in 2019 over a NewTek GPL violation; datarhei
    confirmed no NDI in their build and declined on licensing grounds —
    [discussion #391](https://github.com/datarhei/restreamer/discussions/391)), and
    Central cannot ingest SRT (NDI-only per its
    [own user guide](https://birddog.tv/wp-content/uploads/2022/09/BirdDog-Central-2.0_User-Guide.pdf)).
    What remains is verification, not design: confirm VMix's NDI output registers with
    the discovery server and Central picks it up across the tailnet; confirm Central's
    re-transmit actually re-originates the stream (rather than pointing receivers at
    the original source, which would bypass the mothership and break both the ACL model
    and the bandwidth math); and measure the node uplink during a rehearsed fallback
    against the modelled ~130 Mbps.

17. **Confirm the Cloud Gateway's exact model — LAG support *and* routing capacity.**
    Listed as a resolved assumption above, but nothing in this repo confirms it, and
    [`docs/deployment-runbook.md`](deployment-runbook.md) Phase 0 still treats it as a
    to-do. Port aggregation is only supported on the UDM Pro / SE / Pro Max, UXG
    Enterprise and EFG ([Ubiquiti](https://help.ui.com/hc/en-us/articles/360007279753)) —
    a literal "Cloud Gateway" (UCG Ultra/Max/Fiber) has none. Separately, every theatre
    packet is *routed* by this box from an uplink VLAN onto Mothership-LAN: on a UDM Pro
    the LAN switch reportedly reaches the CPU over a single 1 Gbps link, capping
    inter-VLAN routing near 1 Gbps whatever the bond does — below the ~1,493 Mbps worst-case
    inbound in [`docs/server-specification.md`](server-specification.md). Check the real
    unit's inter-VLAN throughput, and which ports the uplink VLANs and the server land on.

18. **Finish and verify the mothership-side routing path into the tailnet, and the ACL
    rules for it.** Everything on the mothership that talks to a theatre (both ingest containers,
    Fleet Admin, Restreamer, Overseer, Flock, GLKVM-Cloud, and the BirdDog Central VM) does
    so through the subnet router at `192.168.1.2`. The outbound leg is now specified
    (gateway static routes); the rest is not yet proven:
    - **Macvlan containers can't exchange traffic with their own host** — the same
      isolation Unraid applies by default (the host can't reach its own macvlan containers
      unless "Host access to custom networks" is on). A container using
      `192.168.1.2` as its next hop, or the host forwarding a decrypted reply to a
      container, both hit it. And by default the subnet router SNATs tailnet traffic to
      `192.168.1.2`, so even theatre-initiated streams arrive "from the host" and the
      container's reply has to get back to it. Candidate fixes: Unraid's "Host access to
      custom networks" (check that it covers a compose-created macvlan network, not just
      Unraid's own), or moving the subnet router off host networking.
    - **Static routes on the Cloud Gateway** (`192.168.2-13.0/24`, `.20`, `.21` →
      `192.168.1.2`) are now in
      [`config/unifi/network-config.yaml`](../config/unifi/network-config.yaml). They solve
      the outbound next hop, but every packet from a container or the VM crosses the bond
      twice — see the NIC section of
      [`docs/server-specification.md`](server-specification.md) — and they don't solve
      the *return* leg: the host delivers replies to `192.168.1.13-.24` on-link, which
      macvlan isolation drops unless host access is on.
    - **ACL: now names the subnets in both directions.**
      [`config/tailscale-acl.json`](../config/tailscale-acl.json) previously granted only
      `tag:mothership → tag:theatre:*`; a tag matches the tagged nodes' own tailnet
      addresses, not the `/24`s they advertise, so `192.168.1.17 → 192.168.2.2` (and a
      theatre router registering with GLKVM-Cloud at `192.168.1.20`) would have been
      denied. It now lists every `/24` as a host alias, as source and destination, with
      theatre ranges only ever paired with the mothership range. Still to do: confirm
      against current Tailscale docs, decide on `--snat-subnet-routes=false` (Tailscale's
      site-to-site guide sets it so the far end sees real source addresses), and re-test
      cross-theatre isolation once built.
    - `config/docker-compose.yml`'s subnet router previously ran in the Tailscale image's
      default **userspace** mode, which can't forward LAN → tailnet traffic at all; it is
      now set to kernel mode (`TS_USERSPACE=false`).

19. **Benchmark Tailscale's real throughput on an A-1300.** The ~170 Mbps every
    per-router figure in [`docs/bandwidth-analysis.md`](bandwidth-analysis.md) is checked
    against is GL.iNet's *kernel* WireGuard client figure; Tailscale on GL.iNet firmware
    runs its own userspace `wireguard-go` engine, historically well below that on this
    class of CPU. Run `iperf3` bidirectionally (`--bidir`) between a theatre LAN host and
    the mothership, through Tailscale, before trusting any of the 92-128% per-router
    utilization figures — if the real ceiling is lower, the NDI-fallback mitigation may
    not be enough.

20. **Set the SRT payload size to 1128 bytes** on the VMix node PCs' SRT outputs and on
    Restreamer's outputs. SRT's default 1316-byte payload makes a 1360-byte IP packet,
    above Tailscale's 1280-byte tunnel MTU, so every SRT packet would fragment or drop;
    1128 bytes (6 × 188-byte TS packets) gives a 1172-byte packet that fits — see
    [`docs/bandwidth-analysis.md`](bandwidth-analysis.md).

21. **Confirm which ATEM Mini Extreme ISO model is on site — original or G2.** The ingest
    design assumes FTP is the only way in; check whether the model in use exposes its
    recording media as a network drive as well (reported for the G2), which would change
    the cheapest ingest path. Confirm against the unit, not the product page alone.

22. **`pull-iso.py` doesn't recurse into subfolders.** It lists `ATEM_FTP_REMOTE_DIR`
    only, non-recursively (flagged as a known gap in
    [`config/atem-iso-ingest/pull-iso.py`](../config/atem-iso-ingest/pull-iso.py)
    itself), while ATEM ISO recordings are written into per-recording project folders.
    Needs a recursive walk once the real FTP layout is confirmed on a unit (#4).

23. **Reconcile the smart-bin path filter with the NAS layout.** The Resolve smart-bin
    recipes in [`docs/live-editing.md`](live-editing.md) filter clips by record-drive
    path, but the ingest dual-write lands them under `TheatreN/ISO/` on the NAS — the
    filter has to match the path the ingest actually writes, not the ATEM's own drive
    name.

24. **Give the Unraid server a 10GbE port and an address on `192.168.22.0/24`** for the
    edit-suite dual-write (as [`docs/live-editing.md`](live-editing.md) and the NIC
    section of [`docs/server-specification.md`](server-specification.md) require). Not
    yet in [`docs/ip-address-map.md`](ip-address-map.md), and the hardware isn't
    confirmed on the on-hand box (#1).
