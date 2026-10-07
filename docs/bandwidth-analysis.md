# Bandwidth analysis — venue-supplied VLANs

**New constraint that changes the calculus:** the 4 uplink VLANs are not our
infrastructure — they're supplied by the venue over their existing structured cabling,
each hard-capped at **1 Gbps**, and **each VLAN port is expensive**. The goal is minimum
VLAN count at adequate performance, not the reverse. This replaces the earlier framing in
[`docs/open-questions.md`](open-questions.md) (which assumed we controlled VLAN
addressing/count freely) — the *addressing* there is still fine, the *count* now has a
real cost pressure behind it that this doc quantifies.

**Assumption to confirm with the venue:** the 1 Gbps figure is treated here as a standard
switched-Ethernet full-duplex rating (1 Gbps *each direction*, not a shared aggregate) —
true for virtually all modern structured cabling, but worth a one-line confirmation rather
than assuming.

**Revised 2026-10-06.** Research that day found both load-bearing numbers this doc used to
rest on were wrong — the ~10 Mbps-per-ATEM-ISO-stream basis and the A-1300 router's
~170 Mbps ceiling — and two design decisions followed: a **narrower live-ingest scope**
(camera + program by default, see below) and a **different router, the GL.iNet Slate AX
(GL-AXT1800)**. Every derived figure below was recomputed from the planning figures in the
per-traffic table by a script, not adjusted by hand.

## Tailscale/WireGuard overhead

Every figure below that crosses the tailnet (SRT, NDI, ATEM ingest, rclone) is wrapped in
a WireGuard tunnel between the theatre's Slate AX and the mothership's Tailscale container —
that adds a real, quantifiable tax on top of the raw payload. For an IPv4 outer path,
WireGuard's per-packet overhead is 60 bytes (20B IP + 8B UDP + 32B WireGuard header + auth
tag) ([header breakdown](https://lists.zx2c4.com/pipermail/wireguard/2017-December/002201.html)).
That is 4.0% of a 1500B packet — but Tailscale's tunnel MTU is **1280B**, not 1500B, so a
full-size packet inside the tunnel carries 60/1280 ≈ **4.7%** overhead (≈4.4% for a
default 1360B SRT packet). All figures in this doc have a flat 4% folded in, which
understates every tailnet figure by under 1% (e.g. NDI ~130 → ~131 Mbps) — immaterial at
the precision used here, so the figures are left as-is.

**The 1280B tunnel MTU also matters for SRT itself, not just the overhead maths.** SRT's
default payload is 1316B (7 × 188B MPEG-TS packets), i.e. a 1360B IP packet — larger than
Tailscale's 1280B MTU, so every SRT packet would be IP-fragmented (or dropped, if sent with
DF set) on its way into the tunnel. Set the SRT payload size on the senders (VMix PCs,
Restreamer's outputs) to **1128B** (6 × 188B → 1172B IP packet, fits under 1280B). See
[`docs/streaming-flow.md`](streaming-flow.md).

**Presenter internet does NOT get this tax.** It's a separate path — presenter laptops go
straight out to the internet via the Slate AX's normal NAT/WAN, never touching the Tailscale
tunnel at all (see [`docs/tailscale.md`](tailscale.md): only the 14 Slate AX routers and the
mothership run Tailscale; nothing routes presenter traffic through it). It may still share
the same physical VLAN link and the same router (unconfirmed — see the recommendation at
the end of this doc), but it never shares the encrypted tunnel or its overhead.

## Real-world per-traffic-type figures (WireGuard overhead included where it applies)

**The live-ingest scope this doc now sizes for** (the same input map on all 12 ATEMs —
see [`docs/atem-iso-ingest.md`](atem-iso-ingest.md)):

| ATEM input | Source | Pulled live? |
|---|---|---|
| 1 | Camera | **Yes (default)** |
| 2 | Presenter laptop 1 (PowerPoint Main) | Optional — only if router headroom allows (`ATEM_ISO_INPUTS=1,2`) |
| 3 | Laptop 2 (VT Main / second presenter) | Optional (`ATEM_ISO_INPUTS=1,2,3`) |
| 4–8 | Backups / spare | Never live; stays on the ATEM SSD |
| Program recording | — | **Always pulled**; the ATEM's Streaming/record quality set so this file is ~8–10 Mbps |

The ATEM records every input regardless (ISO recording is all-or-nothing per switcher);
anything not pulled live arrives via the physical DIT offload of the ATEM SSD or between
sessions ([`docs/live-editing.md`](live-editing.md)).

Planning figures are given as **low / typical / high**:

| Traffic | Direction | Basis | Figure |
|---|---|---|---|
| SRT, baseline (static/motion-graphics) | Mothership → theatre | 3-6 Mbps encoder for low-motion 1080p H.264 (4.5 Mbps midpoint used), +25% SRT overhead ([Haivision](https://www.haivision.com/blog/all/how-to-configure-srt-settings-video-encoder-optimal-performance/) — 25% is SRT's default *ceiling* for retransmission headroom, not steady-state use, so this is conservative), +4% WireGuard | **~5.8 Mbps** |
| SRT, peak (opening/closing, higher motion) | Mothership → theatre | 6-8 Mbps encoder + 25% overhead + 4% WireGuard | **~10.4 Mbps** |
| **NDI backup, active (1080p50, full — not HX)** | Mothership → theatre | Official NDI spec ([docs.ndi.video](https://docs.ndi.video/all/getting-started/white-paper/bandwidth)) — **roughly constant regardless of content**, unlike SRT's H.264 long-GOP; the "mostly static graphics" discount does not apply here. +4% WireGuard | **~130 Mbps** |
| **ATEM camera ISO, per input** | Theatre → mothership | H.264 VBR, **not user-settable** — Blackmagic's spec is "up to 70 Mb/s" ([tech specs](https://www.blackmagicdesign.com/products/atemmini/techspecs)); only frame rate moves the target (~45 Mbps at 24/25/30p, 70 at 50/60p — [forum](https://forum.blackmagicdesign.com/viewtopic.php?f=4&t=119703)); users report ~30-45 Mbps averages (e.g. ~15 GB/h per source ≈ 33 Mbps — [forum](https://forum.blackmagicdesign.com/viewtopic.php?f=4&t=139572)). 70 = vendor cap | **35 / 45 / 70 Mbps** raw |
| **ATEM laptop (slides) ISO, per input** | Theatre → mothership | **Estimate, unmeasured** — mostly-static slides should encode well under a camera at the same fixed VBR target, but nothing published pins it. One measured file from a real unit replaces this row | **15 / 25 / 40 Mbps** raw |
| **ATEM program recording** | Theatre → mothership | Follows the configurable Streaming quality setting (one test measured ~4.8 Mbps); set to land at ~8-10 Mbps | **10 Mbps** raw |
| **ATEM live ingest, default scope (camera + program)** | Theatre → mothership | (camera + program) + 4% WireGuard | **47 / 57 / 83 Mbps** |
| **ATEM Overseer monitoring stream** | Theatre → mothership | 10 Mbps per theatre (your figure) + 4% WireGuard — flat, doesn't scale with the ingest scope, see [`docs/topology.md`](topology.md) | **~10.4 Mbps** |
| **Flock BirdDog Play preview stream** | Theatre → mothership | 10 Mbps SRT per theatre (your figure) + 4% WireGuard — flat, same treatment as the Overseer stream, see [`docs/topology.md`](topology.md) | **~10.4 Mbps** |
| rclone file sync, steady-state | Theatre → mothership | sporadic post-ingest updates only — see below | **~5 Mbps avg** |
| rclone file sync, worst case | Theatre → mothership | multiple laptops syncing simultaneously | **~15 Mbps** |
| rclone file sync, initial bulk ingest | Theatre → mothership | 10-20 GB/theatre, **one-time** | not a sustained-load concern — see below |
| Presenter internet | Both, shared VLAN link, **no WireGuard tax** | web/slides/occasional demo video — **unconfirmed whether it shares this VLAN or is separate infrastructure** | ~10-25 Mbps allowance |

> **Resolved (2026-10-06): the old "10 Mbps per ISO stream" basis was wrong, and so was
> the router ceiling it was checked against.** This doc previously sized ATEM ingest as
> 5-9 ISO streams × 10 Mbps (~62-94 Mbps per theatre) against the A-1300's ~170 Mbps.
> What the research found:
>
> - **ISO files are ~35-70 Mbps each, and the rate can't be turned down.** The ATEM Mini
>   Extreme ISO (and G2) record each ISO input as H.264 "up to 70 Mb/s"
>   ([Blackmagic tech specs](https://www.blackmagicdesign.com/products/atemmini/techspecs)).
>   There is no ISO bitrate setting — only the frame rate changes the target
>   ([forum](https://forum.blackmagicdesign.com/viewtopic.php?f=4&t=119703); the feature
>   request is still open, [forum](https://forum.blackmagicdesign.com/viewtopic.php?f=4&t=120592)).
>   User reports average ~30-45 Mbps per ISO; older firmware showed 90-120 Mbps, with a
>   silent drop around firmware 9.6.x ([forum](https://forum.blackmagicdesign.com/viewtopic.php?t=208347)) —
>   so check the firmware on the units too. ISO recording is all-or-nothing per switcher
>   (inputs can't be disabled; empty inputs make near-empty files).
> - **"10 Mbps" is realistic for the program file only**, which follows the configurable
>   Streaming quality setting (~4.8 Mbps measured in one test).
> - **The A-1300's 170 Mbps is a kernel-WireGuard figure, not a Tailscale one** — see
>   [the per-router section](#the-per-router-ceiling-why-the-a-1300-was-replaced-by-the-slate-ax).
>   Planning estimate for Tailscale on an A-1300: ~30-70 Mbps combined (unmeasured).
>
> At 45 Mbps × 6 ISOs the old pull-everything plan would have needed ~280 Mbps per theatre
> before Overseer/Flock — nowhere near any travel router running Tailscale. Hence the
> two decisions this revision is built on: **pull live only the camera ISO + program by
> default** (optionally one or two laptop ISOs, set per theatre with `ATEM_ISO_INPUTS_T<n>`),
> and **replace the A-1300 with the Slate AX**. One `ffprobe` (or file size ÷ duration) of
> a real camera and a real laptop ISO file from the actual ATEM, at the event's frame rate
> and firmware, still settles the exact numbers — tracked in
> [`docs/open-questions.md`](open-questions.md).

**Initial bulk ingest isn't a bandwidth risk if scheduled right.** 15 GB at a generously
throttled 100 Mbps takes ~20 minutes; even at a conservative 50 Mbps, ~40 minutes. Run it
during load-in/setup, not concurrent with a live session, and it's a non-issue regardless
of VLAN count. Don't let this drive the VLAN-count decision.

## Per-theatre sustained budget (during a live session, excluding the one-time bulk ingest)

Fixed upstream per theatre, whatever the ingest scope: Overseer (~10.4) + Flock (~10.4) +
rclone (~5) = **~26 Mbps** (~36 with the rclone worst case). The ingest scope sits on top:

| Live scope | Ingest (incl. WG) | Total upstream | Combined through the router (+ SRT down) |
|---|---|---|---|
| **Camera + program (default)** | **47 / 57 / 83** | **73 / 83 / 109** | **~89-119** |
| Camera + 1 laptop + program | 62 / 83 / 125 | 88 / 109 / 151 | ~115-161 |
| Camera + 2 laptops + program | 78 / 109 / 166 | 104 / 135 / 192 | ~141-203 |
| 4 ISOs (2 cameras + 2 laptops) + program | 114 / 156 / 239 | 140 / 182 / 265 | ~188-275 |

All Mbps, low / typical / high. The combined column runs from typical upstream + SRT
baseline (5.8) to high upstream + SRT peak (10.4). The rclone worst case adds ~10 Mbps to
any upstream figure (e.g. 109 → 119 at the default scope's high end). Downstream is SRT plus
presenter internet: **~21 Mbps** = SRT baseline (~5.8 Mbps) + ~15 Mbps presenter;
**35 Mbps** = SRT peak (~10.4 Mbps) + the 25 Mbps presenter ceiling. The laptop rows
inherit the laptop-ISO **estimate** — treat them as less firm than the camera rows.

Upstream is still dominated by ATEM ingest — ~69% of typical upstream at the default
scope, ~81% with both laptops added — with Overseer and Flock the flat secondary
contributors. See [`docs/topology.md`](topology.md) for what those two streams are for.

## The per-router ceiling: why the A-1300 was replaced by the Slate AX

Every byte a theatre sends/receives over the tailnet has to pass through that one router's
crypto, regardless of how much headroom the VLAN has — a **separate, tighter bottleneck**
than the shared VLAN.

**The A-1300's 170 Mbps was never a Tailscale figure.** GL.iNet's number is its *kernel*
WireGuard client-mode benchmark ([GL-A1300 product page](https://www.gl-inet.com/products/gl-a1300/)).
Tailscale does its crypto in Go userspace (`wireguard-go`), and on the A-1300's 32-bit
IPQ4018 (4× Cortex-A7 ~717 MHz, 256 MB RAM, kernel 5.4, firmware stuck at 4.5.x with
Tailscale 1.58) Go has no optimised ChaCha20-Poly1305 assembly. Comparable gaps measured on
other GL.iNet hardware: GL-MT1300 ~90 Mbps kernel WireGuard vs ~20 Mbps Tailscale
([tailscale#10524](https://github.com/tailscale/tailscale/issues/10524)); Beryl AX (64-bit)
300 Mbps WireGuard vs ~150 Mbps each way Tailscale
([GL.iNet forum](https://forum.gl-inet.com/t/max-speed-using-beryl-ax-gl-mt3000-with-tailscale/42826)).
**Planning estimate for Tailscale on an A-1300: ~30-70 Mbps combined (unmeasured).** That
fails even the default scope in normal operation (~89 Mbps combined, typical) — so the
A-1300 was dropped on 2026-10-06.

**The replacement: GL.iNet Slate AX (GL-AXT1800), ×14.** Qualcomm IPQ6000, 4× Cortex-A53 @
1.2 GHz (64-bit, so Go's optimised crypto paths apply), 1× WAN + 2× LAN gigabit — the same
port layout as the A-1300, so the LAN1 → ATEM / LAN2 → switch wiring in
[`docs/topology.md`](topology.md) is unchanged — USB 3.0, WireGuard up to 550 Mbps (vendor,
kernel WireGuard), $119.99 list
([specs](https://www.gl-inet.com/products/gl-axt1800/specs/),
[product page](https://www.gl-inet.com/en-us/products/gl-axt1800)). **Expected Tailscale
throughput ~150-250 Mbps combined — an estimate** extrapolated from the Beryl AX
measurement above; no Slate AX Tailscale benchmark was found. Benchmark one unit (`iperf3
--bidir` from a theatre LAN host to the mothership, direct path, not DERP) before buying 14 —
this is still the single most load-bearing unverified number in the design.

Against that ~150-250 Mbps estimate (percentages at the low / high end of the range):

| Scenario | Upstream | Downstream | Combined | vs. ~150-250 Mbps (est.) |
|---|---|---|---|---|
| Normal, default scope (camera + program), typical | 83.0 Mbps | 5.8 Mbps | 88.8 Mbps | 59% / 36% — comfortable |
| Normal, default scope, high | 109.0 Mbps | 10.4 Mbps | 119.4 Mbps | 80% / 48% |
| Normal, camera + 2 laptops + program, typical | 135.0 Mbps | 5.8 Mbps | 140.8 Mbps | 94% / 56% — fits, thin at the low end |
| Normal, 4 ISOs + program, typical | 181.8 Mbps | 5.8 Mbps | 187.6 Mbps | 125% / 75% — marginal |
| **NDI fallback, this theatre only, default-scope ingest still running (typical)** | 83.0 Mbps | 130.0 Mbps | **213.0 Mbps** | **142% / 85% — only fits if the real figure lands in the upper part of the range** |
| **NDI fallback, ingest paused** (Overseer + Flock + rclone + NDI) | 25.8 Mbps | 130.0 Mbps | **155.8 Mbps** (165.8 with rclone worst case) | **104% / 62%** (111% / 66%) — fits unless the benchmark lands at the very bottom of the estimate |

**Practical mitigation (unchanged in kind):** if a theatre's SRT feed fails and it falls
back to NDI, pause *that theatre's* ATEM ingest for the duration — near-real-time review
footage is a lower priority than the live show staying on air, and the ATEM's own SSD keeps
recording every input regardless. This is a cheap, config-only fallback response, not a
design change. The floor it can't go below is the two monitoring streams plus NDI:
10.4 + 10.4 + 130 = **150.8 Mbps** — which is why the Slate AX benchmark needs to come in
above ~160 Mbps combined for a single-theatre NDI fallback to be safe at all.

**Worked through fully — NDI fallback + ATEM paused, at every level this design has a
bottleneck at**, since "under the ceiling" at one figure doesn't tell the whole story on its
own (default scope, camera + program):

| Level | Without the mitigation (ATEM still ingesting) | With it (ATEM paused) |
|---|---|---|
| **Single theatre's own Slate AX** (upstream + downstream combined, vs. ~150-250 Mbps est.) | 213 Mbps typical / 239 Mbps high — **only fits near the top of the estimate** | 155.8 Mbps realistic / 165.8 Mbps worst case — fits at ≥ ~170 Mbps; over at the very bottom of the estimate |
| **That theatre's VLAN group, upstream side only** (NDI itself doesn't touch upstream — full-duplex, separate capacity) | n/a — this is exactly what the mitigation removes | Drops to just rclone + Overseer + Flock per theatre (25.8-35.8 Mbps) — even a fully-loaded 6-theatre group sits at 15.5-21.5% upstream, nowhere near a concern |
| **Mothership's own bonded NIC, mass-fallback disaster case** (all 12 theatres on NDI at once) | Downstream 1,560 Mbps; upstream ~1,080-1,120 Mbps typical / ~1,390-1,430 Mbps high (incl. VMix) — both sides genuinely loaded | Downstream unchanged at 1,560 Mbps, but **upstream drops to ~310-430 Mbps** — the mitigation's biggest payoff shows up here |
| **Central's own NDI feed in** (the source VMix node's program arriving for redistribution — see [`docs/streaming-flow.md`](streaming-flow.md)) | +130 Mbps inbound per active node program (max +260 if both nodes' programs are being redistributed) — rides the node's uplink, then the mothership NIC inbound | Same +130-260 Mbps — this feed persists through the mitigation; stacked on the unmitigated high-end inbound (~1,433 + 260 ≈ 1,693 Mbps) it stays under the bond's ~2,000 Mbps aggregate counted once. Counted properly it arrives twice (gateway → Tailscale container on `.1.2`, then `.1.2` → Central), see the hairpin note below |

**The one number worth remembering: ~151 Mbps** — the floor a single theatre's router has to
carry during an NDI fallback even with all ingest paused. The Slate AX benchmark has to
clear it with room to spare. Pausing ATEM ingest fleet-wide during a genuine mass NDI
fallback is unambiguously the right call regardless — it cuts the mothership's inbound from
~1,080-1,430 Mbps to ~310-430 Mbps at exactly the moment the network is under most stress.

### Mothership NIC (2× bonded GbE)

Inbound at the mothership = 12 theatres' upstream + the 4 VMix PCs' record ingest (assumed
20-30 Mbps/PC, ~83-125 Mbps with WireGuard — see "VMix nodes' uplinks" below):

| Live scope (all 12 theatres) | Inbound, typical | Inbound, high | vs. ~2,000 Mbps bond |
|---|---|---|---|
| **Camera + program (default)** | **~1,080-1,120 Mbps** | **~1,390-1,430 Mbps** (~1,550 with rclone worst case) | Fits; same order as the previously-documented worst case |
| Camera + 1 laptop + program | ~1,390-1,430 Mbps | ~1,890-1,930 Mbps | Typical fits; high is at the bond's edge |
| Camera + 2 laptops + program | ~1,700-1,750 Mbps | ~2,390-2,430 Mbps | **Over the bond at the high end** — not fleet-wide on 2× GbE |
| 4 ISOs + program | ~2,270-2,310 Mbps | ~3,260-3,300 Mbps | Not viable on 2× GbE |

Outbound in the mass-NDI-fallback case is unchanged at 12 × ~130 = **~1,560 Mbps**. Each
theatre's traffic is one WireGuard flow to the bond's LACP hash (~109 Mbps per theatre at
the default scope's high end), so the hash-imbalance caveat in
[`docs/server-specification.md`](server-specification.md) still applies. Rate actually
landing on the recording pool from live ingest (no WireGuard): ~0.30 TB/h typical /
~0.43 TB/h high at the default scope, ~0.57 / ~0.86 TB/h with both laptops — the rest of each
ATEM's recording arrives later via DIT offload, not over this NIC. Upshot: **laptop ISOs can
be enabled per theatre where a theatre needs them, not fleet-wide**, unless the bond becomes
2× 2.5GbE.

**Mothership-side routing caveat for the NIC figures above:** those figures assume
mothership LAN devices (BirdDog Central VM, the macvlan containers) hand theatre-bound
traffic straight to the Tailscale subnet router on the Unraid host (`192.168.1.2`). If they
instead follow their default gateway and the Cloud Gateway bounces it back to `.2` via a
static route (see `static_routes` in
[`config/unifi/network-config.yaml`](../config/unifi/network-config.yaml)), every such
byte crosses the bond an extra time in each direction — at mass-NDI-fallback scale
(1,560 Mbps out of Central) that alone would exceed the bond's ~2,000 Mbps. Give Central's
VM a direct route to the theatre/VMix subnets via `192.168.1.2`; for the macvlan containers
note that by default the Unraid host can't reach its own macvlan containers at all, unless
"Host access to custom networks" is enabled ([`docs/open-questions.md`](open-questions.md) #18).

**Router options compared** (utilization column = NDI fallback + default-scope ingest +
Overseer + Flock, typical: ~213 Mbps combined):

| Model | WireGuard (vendor, kernel) | Tailscale (combined) | LAN ports | Form factor | ~Price | Utilization |
|---|---|---|---|---|---|---|
| A-1300 (GL-A1300) — **previous choice, rejected 2026-10-06** | [170 Mbps](https://www.gl-inet.com/products/gl-a1300/) | ~30-70 Mbps (est., 32-bit Cortex-A7) | 2 | Pocket travel router | ~$100 | ~300-710% |
| **Slate AX (GL-AXT1800) — chosen** | [550 Mbps](https://www.gl-inet.com/products/gl-axt1800/specs/) | ~150-250 Mbps (est., from Beryl AX) | 2 | Travel router | $119.99 | ~85-142% |
| Beryl AX (GL-MT3000) | [300 Mbps](https://www.gl-inet.com/en-us/products/gl-mt3000) | ~150 Mbps each way ([measured](https://forum.gl-inet.com/t/max-speed-using-beryl-ax-gl-mt3000-with-tailscale/42826)) | **1 only** | Pocket travel router | ~$100-140 | — (port count rules it out) |
| Slate 7 (GL-BE3600) | ~490-540 Mbps (GL.iNet figures differ) | not found | **1 only** | Travel router | — | — (port count rules it out) |
| Flint 2 (GL-MT6000) | [900 Mbps](https://www.gl-inet.com/en-us/products/gl-mt6000) | ~300-450 Mbps (est.) | 5 (2×2.5GbE+4×1GbE, minus WAN) | 233×137×57mm, 761g | ~$170 | ~47-71% |

**Beryl AX and Slate 7 are traps for this design specifically** — better throughput, but
only 1 LAN port, so they can't replicate the dedicated-ATEM-port wiring
([`docs/topology.md`](topology.md)) without an external switch ATEM would then have to
share anyway, undoing exactly the isolation that wiring was for.

**Flint 2 is the headroom option** — ports to spare, comfortable margin even with
ingest running during an NDI fallback — but it's a desktop router (233×137×57mm, 761g;
~6x the volume and ~4x the weight of the A-1300's 118×85×30mm, 181g), no longer
travel-router class for a 14-unit touring kit, at ~40% more per unit than the Slate AX.
Its Tailscale figure is an estimate too. Worth it if the Slate AX benchmark comes in low.

**Fallback if the Slate AX can't be had:** the A-1300 running GL.iNet's *kernel* WireGuard
instead of Tailscale (~120-170 Mbps combined) — enough for the default scope in normal
operation (~89-119 Mbps), but not for an NDI fallback, and it gives up Tailscale's
NAT traversal/ACL model for those links.

## Is the current plan (4 VLANs, 3 theatres each) sufficient?

**Yes, at every ingest scope.** Per-VLAN upstream at the default scope (camera + program):
3 × 83 = **~250 Mbps typical (25% of 1 Gbps)**, 3 × 109 ≈ **~330 Mbps high (33%)**. With both
laptop ISOs added on all three theatres: ~405 Mbps typical / ~577 Mbps high (41-58%). Even
the full 4-ISO scope tops out at ~795 Mbps (80%) — though that scope doesn't fit the routers
anyway. Downstream is lower still. The per-router ceiling above is the one that bites first,
and no VLAN count changes that.

## Consolidating further (fewer, more expensive VLANs handling more theatres each)

Upstream per VLAN, typical / high (excluding the VMix nodes — see their section):

| VLANs | Theatres/VLAN | Camera + program (default) | Camera + 1 laptop + program | Camera + 2 laptops + program | Verdict |
|---|---|---|---|---|---|
| 4 (current) | 3 | 249 / 327 Mbps (25% / 33%) | 327 / 452 Mbps (33% / 45%) | 405 / 577 Mbps (41% / 58%) | Comfortable at every scope |
| 3 | 4 | 332 / 436 Mbps (33% / 44%) | 436 / 602 Mbps (44% / 60%) | 540 / 769 Mbps (54% / 77%) | Comfortable; laptops-everywhere getting warm at the high end |
| **2** | **6** | **498 / 654 Mbps (50% / 65%)** | **654 / 904 Mbps (65% / 90%)** | 810 / 1,153 Mbps (81% / 115%) | **Viable at camera + program; camera + 1 laptop only at typical rates; camera + 2 laptops too tight** |
| 1 | 12 | 996 / 1,308 Mbps (100% / 131%) | 1,308 / 1,807 Mbps | 1,620 / 2,306 Mbps | **Not viable with any live ISO ingest** |

**2 VLANs (6 theatres each) is the furthest safe consolidation** with live ingest kept, and
only at the default scope (or with one laptop ISO if the measured laptop rate comes in at or
below the typical estimate). The Theatre 1-6 group also carries both VMix nodes under a
2-VLAN split, which pushes it hotter — see "VMix nodes' uplinks". This holds for normal
operation (SRT primary) — **see the NDI fallback scenario below**, which is a downstream
constraint and applies regardless of ingest scope.

## If the NDI backup path actually activates — very different math

The bandwidth model above assumes SRT is what's actually flowing downstream. NDI (full,
not HX) is a fundamentally different animal: **~130 Mbps at 1080p50 with WireGuard
overhead, roughly constant regardless of content** ([official NDI spec](https://docs.ndi.video/all/getting-started/white-paper/bandwidth)) —
NDI's compression doesn't get cheaper for static/motion-graphics content the way SRT's
H.264 long-GOP does. That's ~12-22x the SRT figures above, and it changes which scenario
the VLAN-count decision actually needs to survive.

**A single theatre falling back is a non-event at the VLAN level** — 130 Mbps extra on
one theatre's downstream fits comfortably even inside a fully-loaded 6-theatre VLAN group
(though see the per-router finding above — that theatre's own Slate AX is a tighter
constraint than the VLAN). The real VLAN-level question is a **mass fallback**: since
BirdDog Central/NDI is a separate path from Restreamer/SRT, a Restreamer failure (a single
container, single point of failure) would push *every* theatre onto NDI simultaneously —
that's the scenario worth sizing for, not the single-theatre case.

| VLANs | Theatres/VLAN | Downstream if ALL theatres in the group fall back to NDI at once (incl. presenter internet) | Verdict |
|---|---|---|---|
| 4 (current) | 3 | 450 Mbps (45%) | Still comfortable |
| 3 | 4 | 600 Mbps (60%) | Workable, less margin than 4 but not tight |
| **2** | **6** | **900 Mbps (90%)** | **Tight — no real margin left** |
| 1 | 12 | 1800 Mbps (180%) | Not viable at any scale |

(Unchanged by the 2026-10-06 revision — this is all downstream, and the ingest scope only
moves upstream.) A mass NDI fallback at 2 VLANs leaves almost no headroom (90%), while the
current 4-VLAN split stays comfortable (45%).

**Recommendation for this fork:** if the design needs to gracefully survive a mass
simultaneous NDI fallback (Restreamer going down, most plausible trigger), **stay at 3-4
VLANs rather than consolidating to 2**. If a mass fallback event is judged acceptable to
handle operationally instead (e.g. running degraded/reduced-quality NDI, or accepting some
theatres go dark until Restreamer recovers), 2 VLANs remains viable at the default ingest
scope — but that's an explicit choice being made, not a free consequence of the SRT
numbers alone.

## Splitting further instead (more, cheaper-per-theatre but more numerous VLANs)

Going the other direction (6 or 12 VLANs, 1-2 theatres each) buys essentially nothing on
the bandwidth side — the current 4-VLAN plan runs at ~25-33% upstream at the default scope
(~41-58% with both laptop ISOs everywhere) and a comfortable 45% even under a mass NDI
fallback, nowhere near needing more headroom. It also does nothing for the per-router
finding above, since that's a single-router problem, not something more VLANs can fix. The
only genuine benefit of more/smaller VLANs is **fault isolation**: a failed venue port or
switch takes out fewer theatres. Given the explicit cost pressure on VLAN count, the
bandwidth numbers don't support this direction — it's a resilience trade-off to make
consciously if at all, not one the traffic model asks for.

## The highest-leverage lever: real-time ATEM ingest is the dominant cost

ATEM live ingest is ~69% of typical upstream per theatre at the default scope (~76% with one
laptop ISO, ~81% with two) — still the dominant single item, which is exactly why the
2026-10-06 revision narrowed *what* gets pulled live rather than trying to pull everything.
It exists purely for near-real-time review during the event — see
[`docs/atem-iso-ingest.md`](atem-iso-ingest.md)'s "master vs. mirror" framing: **the
ATEM's own SSD remains the authoritative master regardless**, offloaded in full after each
session either way. Each laptop ISO added to `ATEM_ISO_INPUTS` costs ~16-42 Mbps per theatre
(estimate); the camera ISO ~36-73 Mbps.

If VLAN count/cost turns out to be the binding constraint, deferring ATEM ingest to
end-of-session pulls (instead of continuous near-real-time) drops per-theatre upstream from
~83 Mbps typical to **~25.8 Mbps realistic / ~35.8 Mbps worst case** (rclone + Overseer's
10.4 Mbps + Flock's 10.4 Mbps, none of which go away — **unlike ATEM ISO, neither
monitoring stream is deferrable, both are live feeds**) — at which point **1 VLAN for all
12 theatres sits at ~31% realistic / ~43% worst-case utilization**. Still the single biggest
lever available (bigger than any VLAN-topology change), and the only one that makes 1 VLAN
viable for upstream. Losing same-day review access to footage (not the final deliverable)
is the cost. Has nothing to do with the per-router NDI-fallback finding above — that's
purely a downstream/NDI issue.

## VMix nodes' uplinks

Not yet assigned to a VLAN group in the existing docs. Given the cost pressure, they
shouldn't get dedicated VLANs of their own for just 2 nodes — fold each into whichever
group its adjacent theatre already belongs to (Node 1 → Theatre 1's group, Node 2 →
Theatre 4's group). VMix record-ingest bitrate is unconfirmed (see
[`docs/vmix-record-ingest.md`](vmix-record-ingest.md) open items); at an **assumed**
20-30 Mbps/PC each node adds 2 PCs' worth (~42-62 Mbps with WireGuard).

- **4 VLANs:** each node's group (Theatres 1-3, Theatres 4-6) carries one node:
  ~291-311 Mbps typical / ~369-389 Mbps high at the default scope (29-39%); ~447-467 /
  ~618-639 Mbps with both laptop ISOs on (45-64%). Comfortable.
- **2 VLANs (Theatres 1-6 / 7-12):** **both** nodes land in the same group, so it carries
  4 PCs' worth (~83-125 Mbps) on top of its theatres: **~581-623 Mbps typical (58-62%) and
  ~737-779 Mbps high (74-78%)** at the default scope; ~737-779 / ~987-1,028 Mbps
  (74-103%) at camera + 1 laptop. So under a 2-VLAN split the Theatre 1-6 group can't take
  laptop ISOs at the high end — re-check once VMix's real bitrate and the laptop ISO rate
  are measured, or move Node 2 to the other group.

The per-router NDI-fallback caveat bites *harder* here than at the theatres: during any NDI
fallback, the source node's own uplink carries the ~130 Mbps NDI program feed up to BirdDog
Central for redistribution ([`docs/streaming-flow.md`](streaming-flow.md)). With that node's
VMix record ingest paused it's 130 + the ~10-21 Mbps SRT program contribution ≈ 140-151 Mbps
— 93-101% of the Slate AX's estimated ~150 Mbps floor, 56-60% at 250. With record ingest
running alongside it, ~182-213 Mbps — fits only if the benchmark lands in the upper part of
the range. Same pause-the-ingest lever as the theatre-side mitigation, applied at the node.

## Recommendation

- **Confirm the full-duplex assumption with the venue** before finalizing any count.
- **Benchmark Tailscale on one Slate AX before buying 14.** `iperf3 --bidir` from a LAN
  host to the mothership over a direct (non-DERP) path. The ~150-250 Mbps used throughout
  is an estimate extrapolated from the Beryl AX; it needs to clear ~160 Mbps combined for a
  single-theatre NDI fallback (ingest paused) to be safe, and ~215-240 Mbps for one to ride
  through *without* pausing ingest. If it comes in low, the Flint 2 is the headroom option.
- **Measure one real camera ISO and one real laptop ISO file** (`ffprobe`, or size ÷
  duration) at the event's frame rate and firmware. The laptop figure in particular is an
  unmeasured estimate.
- **Run the default live scope — camera ISO + program — on all 12 theatres**
  (`ATEM_ISO_INPUTS=1`, program file at ~8-10 Mbps via the Streaming quality setting).
  Enable laptop ISOs per theatre (`ATEM_ISO_INPUTS_T<n>=1,2` or `1,2,3`) only where a theatre needs them and the
  benchmark leaves room; not fleet-wide on the 2× GbE bond.
- **Set up the per-theatre NDI-fallback mitigation regardless of VLAN count** — pause that
  theatre's ATEM ingest when it falls back to NDI. Without it, one theatre at the default
  scope needs ~213 Mbps combined, over the Slate AX estimate's low end; with it, ~156 Mbps.
- **VLAN count: 4 VLANs remain comfortable at every ingest scope; 2 VLANs are viable at
  camera + program (50-65% upstream), or camera + 1 laptop at typical rates (65%)**, but
  re-check the Theatre 1-6 group with both VMix nodes in it (up to ~78% high at the default
  scope) and the mass-NDI fork below. 1 VLAN is not viable with any live ISO ingest (~100%
  typical at the default scope) — only with ingest deferred to end-of-session.
- **Decide how much a mass NDI fallback needs to survive at full quality** — the actual
  fork in the VLAN-count recommendation:
  - If a Restreamer failure pushing all 12 theatres onto NDI simultaneously must keep
    working at full 1080p50 quality: **stay at 3-4 VLANs**. 2 VLANs puts that scenario at
    90% utilization with no real margin.
  - If that event is acceptable to handle operationally instead: **2 VLANs (6 theatres
    each)** at the default ingest scope halves VLAN cost and keeps real-time camera +
    program ingest.
- **Fold both VMix nodes into their adjacent theatre's VLAN group** rather than requesting
  dedicated VLANs for them, but re-check their real bitrate against the margins above once
  it's confirmed.
- **Resolve the presenter-internet question** (shared with production VLANs or separate
  venue circuit) before treating any of the above as final — it's folded into the
  downstream figures above as a conservative shared-infrastructure assumption, and
  downstream isn't the binding constraint under normal SRT operation, but it should still
  be confirmed.
