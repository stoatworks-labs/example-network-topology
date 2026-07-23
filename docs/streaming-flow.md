# Streaming flow — SRT / NDI

## Primary path (SRT)

```
VMix PCs (both nodes) --SRT--> Restreamer (mothership) --SRT (fan-out)--> BirdDog Play ×12 (one per theatre)
```

SRT is unicast-by-IP, so this path has no discovery dependency and should route cleanly
over the tailnet.

## Backup path (NDI)

```
BirdDog Central (mothership) --NDI--> BirdDog Play ×12 (one per theatre)
```

**Bandwidth note:** full NDI (not HX) at 1080p50 is ~125 Mbps per stream, roughly constant
regardless of content — 12-22x SRT's figures, and without SRT's "static content is cheap"
discount. Fine for a single theatre falling back — *provided that theatre's ATEM ISO
ingest is paused for the duration*, since NDI plus the ingest together exceed the
theatre's own A-1300 WireGuard ceiling — and a real capacity question if this path ever
has to carry all 12 theatres at once (e.g. a Restreamer failure). See
[`docs/bandwidth-analysis.md`](bandwidth-analysis.md) for the full impact at per-router,
per-VLAN, and mothership-NIC level.

**Caveat, and the fix:** NDI relies on mDNS multicast for discovery, which does not cross
a Tailscale-routed boundary — Tailscale is point-to-point WireGuard and doesn't forward
multicast/mDNS ([still an open feature request](https://github.com/tailscale/tailscale/issues/8884),
not something MagicDNS papers over). Plain local mDNS discovery will not find BirdDog
Central across theatres on its own.

**Plan: run an NDI Discovery Server on the mothership.** NDI 5+ added this specifically
for WAN/VPN scenarios — it's unicast TCP (default port **5959**), so it works fine across
the tailnet with no multicast involved:

- Run the discovery server as a small service on the mothership, alongside BirdDog Central.
- Point BirdDog Central (sender) and all 12 BirdDog Play units (receivers) at that
  server's IP. On Windows/macOS this is the NDI Tools Access Manager "Advanced" tab; on
  Linux it's `~/.ndi/ndi-config.v1.json`.
- Once a sender has a discovery server configured, it stops using mDNS entirely — it's
  visible only to finders pointed at the same server.
- Tailscale MagicDNS can supply a stable hostname for the discovery server's address
  instead of hardcoding its Tailscale IP, if the receiving device's config field accepts
  a hostname — a convenience, not a substitute for the discovery server itself.

**Confirmed on BirdDog Play:** BirdUI (the PLAY's web admin — browse to its IP, default
password `birddog`) has a Network panel with NDI-specific settings including a Discovery
Server toggle. Switch it ON, enter a comma-delimited list of Discovery Server IP
address(es), click APPLY. BirdDog's own docs describe this as the mechanism for locating
NDI sources "on different subnets" — exactly this cross-theatre case — and it supports
multiple servers for failover. Sources: [BirdDog PLAY User Guide](https://birddog.tv/wp-content/uploads/2022/11/BirdDog-PLAY_User-Guide_231003.pdf),
[BirdUI User Guide](https://birddog.tv/wp-content/uploads/2024/04/BirdDog_BirdUI_User-Guide.pdf).
Change the default admin password before the event — BirdUI grants full device config access.

See [`diagrams/streaming-flow.svg`](../diagrams/streaming-flow.svg) — primary path solid,
backup path dashed. For why BirdDog Play is the theatre-side receiver at all (vs. a laptop
+ VLC), see [`docs/birddog-play-rationale.md`](birddog-play-rationale.md).
