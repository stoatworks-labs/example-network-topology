# Example Network Topology

> **AI-assisted project.** This design and its documents were produced with
> [Claude](https://claude.com/claude-code) (Anthropic), directed and reviewed by
> a human author. It's a design, not a deployment: the throughput figures are
> real and cited and the configs are generated and ready to apply, but **nothing
> here has been built**. See
> [`docs/open-questions.md`](docs/open-questions.md) for what still needs
> real-world input.

A complete, fully worked network design for a 12-theatre live event. Every theatre streams
its program feed and syncs its files back to a central "mothership", all riding over a single
Tailscale mesh, with no reliance on venue Wi-Fi or a conference-provided network.

**This is an anonymised reference design**, published as a worked example of the whole
process: topology, bandwidth modelling, hardware selection with the reasoning, generated
configs and a deployment runbook. It's a real design for a real event with the identifying
details taken out. All domains are placeholders on the IANA-reserved `example.net`
(substitute your own), and nothing here names the event, client or venue. Product
names, prices and throughput figures are real and cited.

**Status: design finalised, nothing built yet.** Every hardware decision is locked in,
every device has a real IP, throughput has been checked against real-world figures and the
venue's actual VLAN constraints, and the Tailscale/GL-iNet/UniFi configs are generated and
ready to apply. See [`docs/open-questions.md`](docs/open-questions.md) for the handful of
things that still need real-world input before this goes from design to build, or
[`docs/deployment-runbook.md`](docs/deployment-runbook.md) for the full ordered build
sequence.

---

## The shape of it

12 theatres, each on its own isolated subnet, connect back to one mothership over Tailscale.
The physical uplink cabling is grouped 3 theatres to a VLAN purely for cable management. The
VLANs don't provide isolation themselves; **Tailscale ACLs do**. Every theatre can reach the
mothership, but never another theatre, and never a VMix node. Two extra "VMix nodes" hang off
Theatre 1 and Theatre 4, each with its own cameras, its own router and its own place on the
tailnet.

![Full network topology, showing the mothership, all 12 theatres with every internal device and IP, and both VMix nodes](diagrams/topology.svg)

Every box in that diagram is a real device with a real address, 133 of them in total,
counting the live-editing suite's own four.
[`docs/ip-address-map.md`](docs/ip-address-map.md) has the same inventory as a plain text
table, if that's easier to search or paste from.

## Streaming: SRT primary, NDI backup

Each theatre's **BirdDog Play** receives the event's program feed two ways:

![SRT/NDI streaming flow — VMix PCs to Restreamer to BirdDog Play (primary, solid), BirdDog Central through the NDI Discovery Server to BirdDog Play (backup, dashed)](diagrams/streaming-flow.svg)

- **Primary: SRT**, unicast by IP from the mothership's Restreamer straight to each
  theatre's BirdDog Play. It doesn't need any discovery mechanism, so it's the more dependable
  path, and it can come straight from the ATEM's own built-in hardware streaming engine or
  from VMix, with no computer needed either way.
- **Backup: NDI**, from BirdDog Central. NDI normally discovers sources over local mDNS
  multicast, which Tailscale can't carry between theatres, so both ends register with a
  self-hosted **NDI Discovery Server** instead. That's a unicast-TCP service built into NDI 5+
  for this WAN/VPN case. Confirmed working on BirdDog Play's own firmware (BirdUI's Network
  panel has a Discovery Server field built in).

**Why BirdDog Play at all, rather than a laptop running VLC?** No on-site config at all,
native dual-protocol support, broadcast-grade unattended reliability, and central management
from the mothership. [Flock](https://github.com/stoatworks-labs/flock) (a fleet manager built
for this very device) is the fleet-management tool, with per-unit BirdUI as the fallback.
BirdDog Central stays as well, but for a different job: it's the sender side of the NDI backup
path above, not a management requirement. Full comparison in
[`docs/birddog-play-rationale.md`](docs/birddog-play-rationale.md).

## File sync: rclone up, WebDAV local

![File sync flow — theatre laptops rclone to Nextcloud over Tailscale, ready room PCs mount Nextcloud via local WebDAV](diagrams/file-sync-flow.svg)

Theatre laptops (PowerPoint and VT, main and backup, 48 across all 12 theatres) each run
`rclone`, syncing their theatre's folder up to Nextcloud over the tailnet. The mothership's
4 ready-room PCs skip rclone entirely and mount Nextcloud directly over local WebDAV, since
they're already on its LAN.

## ATEM ISO ingest: near-real-time, no manual chunking

Each theatre's ATEM Mini Extreme ISO records up to 9 H.264 streams (8 camera ISOs +
program) to a USB SSD, and unlike most of this design there's no laptop involved: the
mothership pulls straight from the ATEM's **built-in FTP server** over Tailscale subnet
routing, transferring only the bytes added since the last check. That matters because
the file is *always growing*. A naive whole-file re-sync on a schedule doesn't survive
the maths for a real session (a 3-hour, 6-stream recording is 50-80GB, and re-uploading that
*whole thing* every 10 minutes takes longer than 10 minutes, so it falls further and further
behind). There are two documented ways to get that incremental transfer: FTP's own
`REST`/resume command directly (the default, since plain rsync can't be used for this leg: it
needs SSH or an rsync daemon and the ATEM only speaks FTP), or `rclone mount` (presenting the
ATEM's FTP share as a local path) paired with `rsync --append`, which transfers only the new
tail without needing rsync's usual full-file checksum pass. Either way, the pull writes
straight into the folder Nextcloud has mounted as External Storage, so there's no second
upload step and no need to slice up the video file itself. Full design in
[`docs/atem-iso-ingest.md`](docs/atem-iso-ingest.md).

## VMix record ingest: same mechanism, a Windows SMB share instead

The 4 VMix PCs (2 per node) get the same treatment, just pointed at a Windows SMB
share instead of an FTP server. SMB is a proper network filesystem protocol, so mounting
it is the natural way to get at it here, and if anything it's a better fit than the ATEM's
FTP-only case rather than a stretch of the same pattern. `rclone mount` presents each PC's
share as a local path, and `rsync --append` transfers only the new tail, for the same reasons
as the ATEM ingest's alternative approach. Each VMix node has its own dedicated A-1300 uplink
(not shared with the theatre it physically sits near), so this traffic never competes with
that theatre's ATEM ingest or SRT feed. Full design in
[`docs/vmix-record-ingest.md`](docs/vmix-record-ingest.md).

## Self-hosted admin tooling: UniFi Controller + GLKVM-Cloud

Two self-hosted services on the consolidated server, both following the same rule as the
rest of this design: no depending on a vendor's own cloud to manage this design's own
infrastructure.

- **UniFi Controller** (self-hosted UniFi Network Application) gives a local, independent
  management console for the Cloud Gateway, rather than relying on `cloud.ui.com`. The
  Cloud Gateway ships with its own built-in controller and works fine without this, so
  it's optional, but not depending on a vendor cloud to run the mothership's own router
  fits the pattern everything else here follows.
- **GLKVM-Cloud** gives centralised, browser-based SSH terminal and web-admin proxy access
  to all 14 GL-iNet routers at once, instead of 14 separate sessions. It uses GLKVM-Cloud's
  documented support for embedded OpenWrt devices, not its flagship KVM-hardware features
  (there's no physical KVM unit anywhere in this design). The full design, including a
  real WAN-port-forward collision this turned up with the DERP server and how it was
  resolved, is in [`docs/glkvm-cloud.md`](docs/glkvm-cloud.md).

## Fleet management: ATEM Overseer + Fleet Admin, and Flock

Three more mothership services, this time for the theatre hardware itself rather than the
network. They're all separate projects
([`atem-overseer`](https://github.com/stoatworks-labs/atem-overseer),
[`atem-fleet-admin`](https://github.com/stoatworks-labs/atem-fleet-admin),
[`flock`](https://github.com/stoatworks-labs/flock)), not built from source in this repo:

- **ATEM Overseer** is a fleet-wide monitoring/tally dashboard. Every theatre's ATEM
  sends it a dedicated low-bitrate monitoring stream (10 Mbps, included in the bandwidth
  model below), giving one central multiview of all 12 theatres instead of walking
  to each one.
- **ATEM Fleet Admin** sets up lots of ATEMs at once from model-aware config forms,
  either pushed live over the network (reaching all 12 theatres the same way ATEM ISO
  Ingest does, through Tailscale subnet routing, with no separate path needed) or exported
  as loadable XML + a media folder.
- **Flock** does the same fleet-manager job as ATEM Fleet Admin, but for the 12 theatres'
  BirdDog Play units: LAN discovery, tag-based grouping, BirdUI-parity settings, batch
  edits. Each BirdDog Play also sends Flock its own 10 Mbps SRT preview stream, treated the
  same as Overseer's and also included in the bandwidth model below.

## Bandwidth: real numbers, right-sized VLANs

The 4 uplink VLANs turned out to be **venue-supplied rather than the production's own
infrastructure**: 1 Gbps each, with expensive ports, which flips the goal from "isolate
cleanly" to "fewest VLANs at adequate performance". The full model is in
[`docs/bandwidth-analysis.md`](docs/bandwidth-analysis.md), built on real figures: SRT at
~5.8-10.4 Mbps via long-GOP H.264 + SRT/WireGuard overhead; ATEM ISO ingest at ~62-94 Mbps,
which together with the ATEM Overseer and Flock monitoring/preview streams (~10.4 Mbps
apiece) dominates per-theatre upstream; and full NDI at 1080p50, a very different ~130 Mbps
more or less regardless of content. The headlines:

- The current 4-VLAN plan runs at 27-39% utilisation under normal operation. That's still
  comfortable, though real-time ATEM ingest plus both monitoring streams have eaten a fair
  chunk of what used to be a much wider margin.
- **Consolidating to 2 VLANs** still works, but with a properly eroded margin (53-78%,
  down from 41-65% before either monitoring stream existed) for normal SRT-primary
  operation, and it's worth actively re-weighing now, not just noting. A **mass NDI fallback**
  (e.g. a Restreamer failure pushing all 12 theatres onto NDI at once) pushes 2 VLANs to
  90% with no room left; 3-4 VLANs stay comfortable through the same event.
- **1 VLAN no longer works with real-time ATEM ingest, full stop.** It now goes over
  capacity under normal expected load (106%), not just on an unlucky worst-case day.
  Moving ATEM ingest to end-of-session pulls (rather than real time) is now required to
  make 1 VLAN viable at all, rather than a nice-to-have lever.
- **A separate finding that was missed at first**: each theatre's own A-1300 has a tighter
  ceiling (~170 Mbps) than the shared VLAN, so a theatre running ATEM ingest and an NDI
  fallback at the same time can exceed *its own router's* capacity whatever the VLAN count.
  The fix is to pause that theatre's ATEM ingest during an NDI fallback (cheap, config-only).
  That still works with both monitoring streams added, but with less spare margin than before.
  A higher-throughput GL-iNet model would also fix it, but not cleanly; see the doc for
  why.

## Why Tailscale avoids DERP relay here

Every device in this design (all 12 theatres, both VMix nodes, the mothership) sits
behind the *same* shared venue internet connection. That's an unusually favourable setup
for Tailscale: direct connections are likely either over the true private LAN path or via
a NAT hairpin through that one shared public IP, with public DERP relay only as a last
resort. As extra insurance, a self-hosted DERP server (reachable at
`derp.example.net:443`) runs on the mothership itself, so even relayed traffic never
leaves the venue. Full reasoning in [`docs/tailscale.md`](docs/tailscale.md).

## Hardware, confirmed

| Role | Hardware | Why |
|---|---|---|
| Mothership router | Ubiquiti **Cloud Gateway** | Can't run Tailscale natively — that role moves to a container on the services server instead |
| Consolidated services server | **Unraid**, single physical box (already on hand) | Hosts BirdDog Central as the design's only Windows VM (no GPU passthrough anywhere — the mothership VMix VM was removed, its role never established; theatre program feeds originate from the VMix node PCs), plus Nextcloud/Restreamer/NDI Discovery Server/DERP/ATEM ISO Ingest/VMix Record Ingest/UniFi Controller/GLKVM-Cloud/ATEM Overseer/ATEM Fleet Admin/Flock as Docker containers. Chosen over TrueNAS SCALE for its polished container UX (Community Applications). Calculated target spec (storage pools, RAM, CPU, NIC validation — no GPU required) in [`docs/server-specification.md`](docs/server-specification.md) |
| Theatre + VMix node routers | GL-iNet **A-1300** (Slate Plus) ×14 | 12 theatre routers + both VMix node routers, same model throughout. ~170 Mbps WireGuard, comfortable headroom for normal operation (~55% combined); 2 LAN ports let the ATEM Mini Extreme ISO sit on its own dedicated port, away from the rest of the room's traffic — it carries the heaviest sustained load (near-real-time ISO ingest). Its own ceiling is the tighter constraint during an NDI fallback though (128% combined with ATEM ingest, resolved by pausing that theatre's ingest during the fallback) — margin worth watching if any further theatre-to-mothership stream ever gets added, see [`docs/bandwidth-analysis.md`](docs/bandwidth-analysis.md). Full case for GL-iNet + Tailscale specifically — segmentation, multi-WAN, pay-per-device WiFi economics, other uses beyond this event, and the same ceiling reasoning — in [`docs/gl-inet-rationale.md`](docs/gl-inet-rationale.md) |
| Theatre playback | **BirdDog Play** ×12 | Zero-config, native SRT+NDI, centrally fleet-managed — see above |
| Server NICs | **Bonded**, 802.3ad/LACP | SRT bandwidth isn't constant — LACP spreads the many simultaneous flows this box handles (12 theatres' SRT fan-out, rclone, Nextcloud, DERP) across both links for real aggregate headroom |

See [`docs/open-questions.md`](docs/open-questions.md) for the reasoning behind every one
of these, including the couple of things assumed rather than confirmed (and the fallback
if an assumption turns out wrong).

## Live editing: a separate subsystem, not the theatre network

2× MacBook Pro editing workstations plus dedicated fast storage at the mothership,
editing event content as it comes in rather than waiting until after the event. They're on
their **own dedicated 10GbE LAN** (`192.168.22.x`) on purpose, not part of the Tailscale mesh
or the theatre-facing network the rest of this repo is sized for. Editing needs sustained
multi-gigabit throughput per editor, and putting that on the existing bonded 1GbE would
either starve the editors or risk contention with the live ingest pipelines still running
during the event.

Key decisions, each one evaluated rather than assumed:

- **Dedicated NAS, not Nextcloud's own storage.** The same rclone/rsync pull that
  ingests each theatre's ATEM/VMix footage into Nextcloud writes a second copy straight
  to the edit-suite NAS at the same time, with no chained re-sync. That keeps editing
  entirely separate from the live show's infrastructure.
- **A dedicated Mac mini running both the Resolve Project Server and Remote Render.** It's
  needed because the whole workflow below is one shared show project both editors work
  on, not two independent copies (confirmed **not** possible on a Blackmagic Cloud
  Store appliance itself, which is storage-only). Blackmagic don't document combining both
  roles on one box as forbidden, but there's not much precedent for it in practice. See
  Decision 2 in [`docs/live-editing.md`](docs/live-editing.md) for the full honesty-check.
- **Blackmagic Cloud's internet sync service: not needed here.** It's a separate
  product from the Cloud Store hardware, built for cross-site collaboration, and this is a
  single-venue setup with no second site to sync with.
- **A pre-built Resolve project structure, generated by
  [resolve-configurator](https://github.com/stoatworks-labs/resolve-configurator)**, a
  companion project to this design. It scaffolds a bin per theatre-day and an empty
  timeline per session ahead of time, and writes the exact smart-bin rules as a recipe you
  apply once (Resolve's own scripting API can't create real smart bins). Once footage
  lands on the NAS and that recipe's been applied, each session's bin fills itself with just
  its own clips, and editors open a session, drag in, top-and-tail, export.

It also covers a DIT (Digital Imaging Technician) ingest workflow for physical media to go
alongside it (the ATEM's own USB SSD and any standalone camera cards), comparing
ShotPut Pro, OffShoot, Silverstack, and the companion tools FoolCat (camera reports) and
o/PARASHOOT (safe card reformatting). Full design in
[`docs/live-editing.md`](docs/live-editing.md).

## Subnet map

Mothership on `192.168.1.x`; theatres run contiguously from `.2.x` through `.13.x`, grouped 3
per physical VLAN purely for uplink cabling.

| Theatre | Subnet | VLAN (uplink grouping) |
|---|---|---|
| 1 | 192.168.2.x | VLAN 1 |
| 2 | 192.168.3.x | VLAN 1 |
| 3 | 192.168.4.x | VLAN 1 |
| 4 | 192.168.5.x | VLAN 2 |
| 5 | 192.168.6.x | VLAN 2 |
| 6 | 192.168.7.x | VLAN 2 |
| 7 | 192.168.8.x | VLAN 3 |
| 8 | 192.168.9.x | VLAN 3 |
| 9 | 192.168.10.x | VLAN 3 |
| 10 | 192.168.11.x | VLAN 4 |
| 11 | 192.168.12.x | VLAN 4 |
| 12 | 192.168.13.x | VLAN 4 |

VMix Node 1 (off Theatre 1): `192.168.20.x`. VMix Node 2 (off Theatre 4): `192.168.21.x`.
See [`docs/bandwidth-analysis.md`](docs/bandwidth-analysis.md) for whether this 4-VLAN
grouping is the right number to actually build, or whether to consolidate.

## Operations: building it, running it, and the road not taken

Three docs turn the design into something an on-site crew can actually work through:

- [`docs/deployment-runbook.md`](docs/deployment-runbook.md): the full ordered build
  sequence, Phase 0 (confirmations) through Phase 7 (pre-event verification), with each step
  linking back to the doc that has the detail. This is the one to have open on build day.
- [`docs/troubleshooting.md`](docs/troubleshooting.md): the gotchas that turned up *during
  design* (unreachable theatres, DERP relay when direct was expected, NIC bonds that
  won't form, ingest falling behind, missing monitoring previews), each as
  symptom → cause → fix, so nobody has to rediscover them under show pressure.
- [`docs/topology-alternative-tailscale-switches.md`](docs/topology-alternative-tailscale-switches.md):
  the road not taken. Plain switches + Tailscale on generic Linux boxes instead of
  GL-iNet routers. It's documented with working configs
  ([`config/alt-tailscale-switch/`](config/alt-tailscale-switch/)) so the decision can be
  revisited with evidence, but I don't recommend it, and the doc explains why.

## Before build — open items

The design's finalised. These are the headline items that still need real-world input before the config in this repo gets applied (the complete list, including a few smaller ones, is in [`docs/open-questions.md`](docs/open-questions.md); the ordered build sequence is [`docs/deployment-runbook.md`](docs/deployment-runbook.md)).

- [ ] Check the existing consolidated services server against the calculated target spec in [`docs/server-specification.md`](docs/server-specification.md) (CPU/RAM headroom, storage pool layout; there's no GPU requirement any more).
- [ ] Add the `derp.example.net` DNS record for the self-hosted DERP server.
- [ ] Verify the DERP hairpin isn't caught by the uplink-VLAN firewall block before relying on it.
- [ ] Confirm the real ATEM ISO bitrate/active-channel count and empirically verify partial-file playability.
- [ ] Confirm what VMix is actually recording and set up real SMB shares/credentials on all 4 VMix PCs.
- [ ] Confirm the final VLAN count with the venue, and decide whether a mass-NDI-fallback event needs to survive at full quality (that decides 3-4 vs. 2 VLANs). See [`docs/bandwidth-analysis.md`](docs/bandwidth-analysis.md).
- [ ] Add the `kvm.example.net` DNS record and confirm `GLKVM_ACCESS_IP`'s exact format for the WAN-remapped GLKVM-Cloud ports. See [`docs/glkvm-cloud.md`](docs/glkvm-cloud.md).
- [ ] Confirm ATEM Overseer's, ATEM Fleet Admin's and Flock's real container images, and whether the ATEM/BirdDog Play can actually originate their monitoring/preview streams alongside their primary feeds. See [`docs/open-questions.md`](docs/open-questions.md) #11.
- [ ] Implement the second write destination (the edit-suite NAS) in the actual ingest scripts. It's documented in [`docs/live-editing.md`](docs/live-editing.md) but isn't a code change yet. See [`docs/open-questions.md`](docs/open-questions.md) #15.
- [ ] Verify the NDI backup path's settled redistribution model, VMix node NDI → BirdDog Central → theatre PLAYs (Restreamer can't emit NDI and Central can't ingest SRT, both confirmed), including that Central really re-originates the stream rather than pointing receivers at the source. See [`docs/streaming-flow.md`](docs/streaming-flow.md), [`docs/open-questions.md`](docs/open-questions.md) #16.
- [ ] Decide how much footage the live-editing subsystem needs access to, confirm the Mac mini's combined Project Server + Remote Render role holds up under real load, and whether any standalone cameras are in scope. See [`docs/live-editing.md`](docs/live-editing.md), [`docs/open-questions.md`](docs/open-questions.md) #12-14.

## Everything in this repo

**Design docs**
- [`docs/topology.md`](docs/topology.md): the full network layout: subnets, VLAN grouping, mothership, VMix nodes, theatre wiring
- [`docs/server-specification.md`](docs/server-specification.md): the calculated minimum spec for the consolidated server (storage pools, RAM, CPU, NIC validation; GPU no longer required)
- [`docs/ip-address-map.md`](docs/ip-address-map.md): every device on the network, with its real IP (133 devices, including the live-editing subsystem's NAS, 2 MacBook Pros, and Project Server/Remote Render Mac mini)
- [`docs/streaming-flow.md`](docs/streaming-flow.md): the SRT/NDI streaming path, and the NDI Discovery Server plan
- [`docs/birddog-play-rationale.md`](docs/birddog-play-rationale.md): why BirdDog Play over a laptop + VLC for theatre playback
- [`docs/gl-inet-rationale.md`](docs/gl-inet-rationale.md): why GL-iNet + Tailscale for segmentation/routing, multi-WAN/pay-per-device WiFi economics, and other uses (LED processors, mixing desks, mesh) beyond this event
- [`docs/live-editing.md`](docs/live-editing.md): the post-production subsystem at the mothership: dedicated NAS/network, Resolve collaboration decisions, the resolve-configurator-driven edit workflow, a DIT ingest tool comparison
- [`docs/file-sync-flow.md`](docs/file-sync-flow.md): rclone + WebDAV sync to Nextcloud
- [`docs/atem-iso-ingest.md`](docs/atem-iso-ingest.md): near-real-time ATEM ISO ingest into Nextcloud, no manual chunking
- [`docs/vmix-record-ingest.md`](docs/vmix-record-ingest.md): the same mechanism, aimed at each VMix PC's SMB share
- [`docs/glkvm-cloud.md`](docs/glkvm-cloud.md): self-hosted GLKVM-Cloud for centralised remote administration of the 14 GL-iNet routers
- [`docs/bandwidth-analysis.md`](docs/bandwidth-analysis.md): real-world throughput maths against the venue's 1 Gbps VLANs, and how many are actually needed
- [`docs/tailscale.md`](docs/tailscale.md): the DERP-avoidance reasoning, the self-hosted DERP server, verification commands
- [`docs/open-questions.md`](docs/open-questions.md): every decision made, how it was reached, and what's still open
- [`docs/topology-alternative-tailscale-switches.md`](docs/topology-alternative-tailscale-switches.md): the plain switch + Tailscale-on-Linux alternative to GL-iNet, not recommended but documented
- [`docs/deployment-runbook.md`](docs/deployment-runbook.md): an ordered build checklist pulling every doc and config together into one sequence
- [`docs/troubleshooting.md`](docs/troubleshooting.md): known gotchas that turned up during design, symptom → cause → fix

**Diagrams** ([`diagrams/`](diagrams/)): topology (full device inventory), streaming-flow, file-sync-flow, live-editing-dataflow (dual-write into the edit suite), and live-editing-project-structure (resolve-configurator → smart-bin recipe → editor workflow), all as standalone SVGs

**Offline exports** ([`export/`](export/)): every doc as a self-contained HTML file and an A4 PDF, plus a combined `full-documentation` version of each. See [`export/README.md`](export/README.md)

**Generated configs**
- [`config/docker-compose.yml`](config/docker-compose.yml): the entire consolidated server's Docker stack in one file, see [`config/README.md`](config/README.md)
- [`config/tailscale-acl.json`](config/tailscale-acl.json): ACL policy (cross-theatre isolation) + the self-hosted DERP region
- [`config/tailscale-up-commands.sh`](config/tailscale-up-commands.sh): a per-role `tailscale up` template
- [`config/tailscale-up-all-devices.sh`](config/tailscale-up-all-devices.sh): the same, filled in for all 15 tailnet nodes
- [`config/gl-inet/`](config/gl-inet/): UCI network config for all 14 routers (12 theatres + 2 VMix nodes), generated from templates
- [`config/unifi/`](config/unifi/): Cloud Gateway VLAN/DHCP/firewall/port-forward reference
- [`config/atem-iso-ingest/`](config/atem-iso-ingest/): the FTP-pull ingest script (and the rclone+rsync alternative) plus Nextcloud External Storage setup
- [`config/vmix-record-ingest/`](config/vmix-record-ingest/): the same rclone+rsync combo, aimed at each VMix PC's SMB share
- [`config/glkvm-cloud/`](config/glkvm-cloud/): the self-hosted GLKVM-Cloud docker-compose stack (`rttys` + `coturn`)
- [`config/alt-tailscale-switch/`](config/alt-tailscale-switch/): configs for the plain-switch/generic-Linux alternative, not recommended but documented

## Trademarks

**NDI® is a registered trademark of Vizrt NDI AB.** See <https://ndi.video>.
Other product and company names mentioned in this documentation are the
trademarks of their respective owners. This project is not affiliated with or
endorsed by any of them.
