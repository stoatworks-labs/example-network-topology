# Why BirdDog Play (not a laptop + VLC) for theatre playback

Each theatre's screen is driven by a **BirdDog Play** — a dedicated, purpose-built NDI/SRT
decoder — rather than a general-purpose laptop running a media player. This documents the
reasoning, alongside the closest realistic alternative.

## Zero-config in the theatre

BirdDog Play needs no on-site setup beyond physical connection: plug it into the theatre
screen and the network, point it at a source, done. No OS to patch, no
application to configure per-session, nothing for on-site staff to babysit beyond power and
a cable. That matters at this scale — 12 theatres, unattended for most of a live event.

## Protocol support: SRT primary, NDI backup, both natively

- **SRT** — the primary path in this design (see [`docs/streaming-flow.md`](streaming-flow.md))
  is bandwidth-efficient by design (long-GOP H.264, see
  [`docs/bandwidth-analysis.md`](bandwidth-analysis.md) for real figures). In this design
  it originates from VMix via the mothership's Restreamer, but the protocol keeps options
  open: the ATEM Mini Extreme ISO also has a **built-in hardware streaming engine** that
  can stream SRT directly over Ethernet with no computer involved
  ([Blackmagic tech specs](https://www.blackmagicdesign.com/products/atemmini/techspecs)),
  unused here but available as a fallback origin. BirdDog Play receives either without
  caring which one is sending.
- **NDI** — the backup path (BirdDog Central → BirdDog Play, via the NDI Discovery Server —
  see [`docs/streaming-flow.md`](streaming-flow.md)) is handled natively too, with no
  separate plugin or configuration step.

## Remote control from the mothership

None of these require physically visiting a theatre — and the division of labour is
deliberate, not three redundant tools:

- **[Flock](https://github.com/stoatworks-labs/flock)** — **the fleet-management tool in
  this design**: LAN discovery, tag-based grouping, full BirdUI-parity settings per
  device, and batch edits across a group (Rust + Docker). Purpose-built for managing many
  BirdDog Play units as one fleet rather than 12 individual devices, which is precisely
  this deployment's shape.
- **BirdUI** — each unit's own web admin, reachable directly, as the per-unit fallback
  (already the mechanism used to configure the NDI Discovery Server setting —
  [`docs/streaming-flow.md`](streaming-flow.md)).
- **BirdDog Central** — retained in the design as a mothership VM
  ([`docs/topology.md`](topology.md)) **for the NDI backup path's sender side, not as a
  management layer** — Flock covers the management job on its own. Central's
  routing/control console exists as a bonus, not a dependency.

## Comparison: BirdDog Play vs. laptop + VLC

The realistic alternative is a laptop in each theatre running VLC, pointed at the same SRT/
NDI sources.

| | BirdDog Play | Laptop + VLC |
|---|---|---|
| Setup | Plug in, done | Install/patch OS, install VLC, configure stream URL per source |
| SRT | Native, purpose-built decode | Native from VLC 3+ ([SRT CookBook](https://srtlab.github.io/srt-cookbook/apps/vlc-media-player.html)) — the one protocol VLC handles cleanly |
| NDI | Native, purpose-built decode | Requires a separate third-party plugin ([NDI for VLC](https://docs.ndi.video/all/using-ndi/ndi-tools/plugins/ndi-for-vlc)); reliably *outputting* VLC's playback as NDI is well-documented, but consistently *receiving and playing* an NDI source as input is far less so |
| Remote management | Flock (fleet-wide) with per-unit BirdUI — purpose-built for this device | Nothing built in — would need RDP/VNC/TeamViewer bolted on, none of it purpose-built for stream monitoring/control |
| Unattended reliability | Broadcast-grade embedded device, designed to run 24/7 unattended | General-purpose OS: updates, driver issues, VLC hangs on a dropped stream sometimes need a manual restart |
| Recovery from a dropped stream | Automatic reconnect | Not guaranteed — depends on VLC settings, may need manual intervention |
| Footprint/power | Small, low power, unobtrusive | Full laptop: bigger, hotter, more power, another thing that can be bumped/closed/updated mid-show |
| Attack surface | Purpose-built embedded device | Full general-purpose OS — much larger surface |
| Cost per unit | Lower, purpose-built | A laptop is not free even if "already owned" — it's now unavailable for anything else, and carries more ongoing maintenance |

## Recommendation

BirdDog Play, as already implemented throughout this design. The laptop + VLC path is
real and technically works for SRT specifically, but loses on every axis that matters for
12 unattended theatres running for the duration of a live event: zero-config deployment,
clean NDI support, purpose-built fleet management (Flock, with per-unit BirdUI), and
broadcast-grade reliability without needing on-site intervention when something drops.
