# Troubleshooting

Known gotchas surfaced during design — check here before assuming something's broken.

## "Theatre can't reach the mothership at all"

- **Routes not approved.** Advertising a route with `--advertise-routes` isn't enough —
  it must be approved in the Tailscale admin console (or via `autoApprovers`). Check
  first; this is the single most common reason a fresh subnet router doesn't work.
- **Check `tailscale status`** on the theatre's A-1300 — confirms whether the peer
  connection is up at all before debugging further.

## "Two theatres can talk to each other" (should be impossible)

- This should never happen if [`config/tailscale-acl.json`](../config/tailscale-acl.json)
  is loaded correctly — theatres can only reach `tag:mothership`. Confirm the ACL is
  actually applied in the admin console, not just present in this repo.
- Remember: physical VLAN grouping provides **zero** isolation on its own — it's cabling
  organization only. If ACLs are missing/misconfigured, cross-theatre reachability is the
  default, not a bug in the VLANs.

## "Tailscale is using DERP relay instead of direct"

- Expected sometimes — see [`docs/tailscale.md`](tailscale.md) for why direct connections
  are likely but not guaranteed here (depends on whether the Cloud Gateway allows
  inter-VLAN UDP).
- Run `tailscale netcheck` to see which DERP region is preferred. If it's not the
  self-hosted `example` region, check: is `derp.example.net` actually resolving? Is the WAN
  port forward (443/tcp, 3478/udp) actually in place? Neither works until both exist —
  see [`docs/open-questions.md`](open-questions.md).
- If the self-hosted DERP is reachable from the mothership's own LAN but not from a theatre, suspect the
  uplink-VLAN firewall block in [`config/unifi/network-config.yaml`](../config/unifi/network-config.yaml)
  catching the hairpin path — see the caveat attached to that rule.

## "The NIC bond won't form / only shows one active link"

- **LACP rate mismatch.** Ubiquiti gear hardcodes LACP rate `fast`; Unraid's bonding
  default is `slow`. Both ends must match — see [`docs/topology.md`](topology.md).
- **Cloud Gateway doesn't support LAG at all** on base (non-Pro/SE/Pro Max) models. If
  so, bond through an intermediate LACP-capable switch instead — already the agreed
  fallback, not a new problem.

## "BirdDog Play isn't finding the NDI backup source"

- Confirm the Discovery Server IP is actually entered in BirdUI's Network panel on *both*
  BirdDog Central and every PLAY unit — one-sided config does nothing.
- Plain mDNS will never work across theatres; if Discovery Server isn't configured, this
  is expected behavior, not a fault. See [`docs/streaming-flow.md`](streaming-flow.md).

## "Ingested files (ATEM or VMix) aren't showing up in Nextcloud"

- Writing to the folder isn't enough — Nextcloud needs `occ files:scan` to index it. Check
  the cron job from `setup-nextcloud-external-storage.sh` is actually installed and
  running, not just printed once during setup.
- If files appear but seem stuck at an old size, check the ingest container's logs — a
  failed FTP/SMB reconnect will silently stall the pull loop rather than crash it.

## "Ingest is falling behind / theatre uplink saturated"

- Confirm the real ATEM bitrate/active-channel count and VMix recording settings —
  the bandwidth math in [`docs/atem-iso-ingest.md`](atem-iso-ingest.md) and
  [`docs/vmix-record-ingest.md`](vmix-record-ingest.md) assumes figures that were never
  verified against real hardware.
- If using the `rclone-mount-rsync` alternative, confirm `rsync --append` is actually
  being used (not falling back to a full re-copy) — check `--itemize-changes` output.

## "A copied ATEM/VMix file won't play"

- Confirmed only "very likely" safe to read mid-write, never empirically tested — see the
  open item in both ingest docs. If it fails, the safest fallback is to only pull once
  recording has fully stopped (loses the near-real-time property, but guarantees a valid
  file).

## "ATEM Overseer / Flock isn't showing a theatre's live preview"

- Confirm the ATEM/BirdDog Play in that theatre is actually configured to originate its
  second monitoring/preview stream, not just its primary program feed — this is a
  genuinely unconfirmed capability, not assumed working out of the box, see
  [`docs/open-questions.md`](open-questions.md) #11.
- Check the stream is actually reaching the container's IP
  (`192.168.1.21` for Overseer, `192.168.1.24` for Flock — see
  [`docs/ip-address-map.md`](ip-address-map.md)) over the tailnet, same routing path as
  every other theatre-to-mothership stream in this design.
- If every other theatre works but one doesn't, suspect that theatre's own A-1300 hitting
  its combined-load ceiling rather than anything Overseer/Flock-side — see the per-router
  finding in [`docs/bandwidth-analysis.md`](bandwidth-analysis.md).

## "GL-iNet static DHCP leases aren't applying"

- Every `REPLACE_WITH_MAC_nn` placeholder in [`config/gl-inet/`](../config/gl-inet/) must
  be swapped for the device's real MAC first — the generated configs ship with
  placeholders deliberately, not real defaults.
