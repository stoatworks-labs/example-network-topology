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

## Tailscale/WireGuard overhead

Every figure below that crosses the tailnet (SRT, NDI, ATEM ingest, rclone) is wrapped in
a WireGuard tunnel between the theatre's A-1300 and the mothership's Tailscale container —
that adds a real, quantifiable tax on top of the raw payload. For IPv4 at full-size (1500B)
packets, WireGuard's header overhead is 60 bytes (20B IP + 8B UDP + 32B WireGuard header) —
**~4.0%** ([header breakdown](https://lists.zx2c4.com/pipermail/wireguard/2017-December/002201.html)).
All figures in this doc already have that 4% folded in.

**Presenter internet does NOT get this tax.** It's a separate path — presenter laptops go
straight out to the internet via the A-1300's normal NAT/WAN, never touching the Tailscale
tunnel at all (see [`docs/tailscale.md`](tailscale.md): only the 14 A-1300s and the
mothership run Tailscale; nothing routes presenter traffic through it). It may still share
the same physical VLAN link and the same router (unconfirmed — see the recommendation at
the end of this doc), but it never shares the encrypted tunnel or its overhead.

## Real-world per-traffic-type figures (WireGuard overhead included where it applies)

| Traffic | Direction | Basis | Figure |
|---|---|---|---|
| SRT, baseline (static/motion-graphics) | Mothership → theatre | 3-6 Mbps encoder for low-motion 1080p H.264, +25% SRT overhead ([Haivision](https://www.haivision.com/blog/all/how-to-configure-srt-settings-video-encoder-optimal-performance/)), +4% WireGuard | **~5.8 Mbps** |
| SRT, peak (opening/closing, higher motion) | Mothership → theatre | 6-8 Mbps encoder + 25% overhead + 4% WireGuard | **~10.4 Mbps** |
| **NDI backup, active (1080p50, full — not HX)** | Mothership → theatre | Official NDI spec ([docs.ndi.video](https://docs.ndi.video/all/getting-started/white-paper/bandwidth)) — **roughly constant regardless of content**, unlike SRT's H.264 long-GOP; the "mostly static graphics" discount does not apply here. +4% WireGuard | **~130 Mbps** |
| ATEM ISO ingest, realistic | Theatre → mothership | 5-7 active streams × 10 Mbps (your figures) + 4% WireGuard | **~62 Mbps** |
| ATEM ISO ingest, worst case | Theatre → mothership | all 9 streams × 10 Mbps + 4% WireGuard | **~94 Mbps** |
| **ATEM Overseer monitoring stream** | Theatre → mothership | 10 Mbps per theatre (your figure) + 4% WireGuard — flat, doesn't scale with ATEM channel count like ISO ingest does, see [`docs/topology.md`](topology.md) | **~10.4 Mbps** |
| **Flock BirdDog Play preview stream** | Theatre → mothership | 10 Mbps SRT per theatre (your figure) + 4% WireGuard — flat, same treatment as the Overseer stream, see [`docs/topology.md`](topology.md) | **~10.4 Mbps** |
| rclone file sync, steady-state | Theatre → mothership | sporadic post-ingest updates only — see below | **~5 Mbps avg** |
| rclone file sync, worst case | Theatre → mothership | multiple laptops syncing simultaneously (was already implicit in the per-theatre worst-case upstream total below; made explicit here) | **~15 Mbps** |
| rclone file sync, initial bulk ingest | Theatre → mothership | 10-20 GB/theatre, **one-time** | not a sustained-load concern — see below |
| Presenter internet | Both, shared VLAN link, **no WireGuard tax** | web/slides/occasional demo video — **unconfirmed whether it shares this VLAN or is separate infrastructure** | ~10-25 Mbps allowance |

**Initial bulk ingest isn't a bandwidth risk if scheduled right.** 15 GB at a generously
throttled 100 Mbps takes ~20 minutes; even at a conservative 50 Mbps, ~40 minutes. Run it
during load-in/setup, not concurrent with a live session, and it's a non-issue regardless
of VLAN count. Don't let this drive the VLAN-count decision.

## Per-theatre sustained budget (during a live session, excluding the one-time bulk ingest)

| | Realistic | Worst case |
|---|---|---|
| Upstream (theatre → mothership) | **~88 Mbps** | ~129 Mbps |
| Downstream (mothership → theatre) | **~21 Mbps** | 35 Mbps |

Upstream is dominated by ATEM ISO ingest, with Overseer's and Flock's monitoring/preview
streams together now a real secondary contributor rather than noise — **~88 Mbps** breaks
down as ATEM ISO (~62 Mbps) + Overseer (~10.4 Mbps) + Flock (~10.4 Mbps) + rclone
(~5 Mbps); **~129 Mbps** worst case as ATEM ISO (~94 Mbps) + Overseer (~10.4 Mbps) +
Flock (~10.4 Mbps) + rclone worst-case (~15 Mbps). Both monitoring streams are flat
regardless of ATEM channel count, unlike ISO ingest — see [`docs/topology.md`](topology.md)
for what they're for.

## New finding: check the A-1300's own ceiling, not just the shared VLAN

The GL-iNet A-1300's own published WireGuard throughput (~170 Mbps, see
[`docs/open-questions.md`](open-questions.md)) is a **separate, tighter bottleneck** from
the shared VLAN — every byte a theatre sends/receives over the tailnet has to pass through
that one router's crypto engine, regardless of how much headroom the VLAN itself has.

| Scenario | Upstream | Downstream | Combined | vs. ~170 Mbps ceiling |
|---|---|---|---|---|
| Normal (SRT active) | 88.2 Mbps | 5.8 Mbps | 94.0 Mbps | 55% — still comfortable, though the two monitoring streams together have eaten roughly a fifth of the headroom this used to have (was 43%) |
| **NDI fallback, this theatre only, ATEM still ingesting** | 88.2 Mbps | 130.0 Mbps | **218.2 Mbps** | **128% — exceeds the router's own ceiling** (was 116% before Overseer, 122% with just Overseer) |

This holds **regardless of VLAN consolidation** — it's not a VLAN-count problem at all,
it's a single-router problem that shows up the moment one theatre's ATEM ingest and NDI
fallback run at the same time; Overseer and Flock's streams each widen that gap further,
since both are genuinely new loads riding the same router regardless of what else is
happening — and unlike ATEM ISO ingest, neither is something you'd necessarily want to
pause during the exact moment (an NDI fallback) when knowing what's actually on screen
matters most. Two caveats worth being honest about: the 170 Mbps figure is a vendor
single-direction benchmark, not a confirmed simultaneous-bidirectional rating (flagged
already in `docs/open-questions.md`), and even under a more favorable per-direction
reading, NDI alone (130 Mbps) is still 76% of that ceiling on its own, with little room
left for anything else sharing the same crypto engine.

**Practical mitigation:** if a theatre's SRT feed fails and it falls back to NDI, pause or
throttle *that theatre's* ATEM ISO ingest for the duration — near-real-time review footage
is a lower priority than the live show staying on air, and the ATEM's own SSD keeps
recording the full-quality master regardless of whether the ingest pipeline is running.
This is a cheap, config-only fallback response, not a design change. **Still sufficient on
its own, but with noticeably less margin than before both monitoring streams existed** —
pausing just the ATEM ISO ingest leaves Overseer (10.4 Mbps) + Flock (10.4 Mbps) + rclone
+ NDI (130 Mbps) at roughly **92% of the router's ceiling** (was 86% with just Overseer,
79% before either existed). Still under the ceiling, but the margin this mitigation buys
back has shrunk each time a new monitoring stream was added — worth watching if a fourth
one is ever proposed, since this specific fallback stops working once the two monitoring
streams alone plus NDI exceed 170 Mbps on their own (they don't yet: 10.4+10.4+130=150.8,
89% — comfortable headroom even before rclone is added back in).

**Worked through fully — NDI fallback + ATEM paused, at every level this design has a
bottleneck at**, since "still under the ceiling" at one figure doesn't tell the whole
story on its own:

| Level | Without the mitigation (ATEM still ingesting) | With it (ATEM paused) |
|---|---|---|
| **Single theatre's own A-1300** (upstream + downstream combined, vs. 170 Mbps) | 218.2 Mbps — **128%, exceeds the ceiling** | 155.8 Mbps realistic (**92%**) / **165.8 Mbps worst case (97%)** — both under, but worst case leaves only ~7 Mbps of headroom |
| **That theatre's VLAN group, upstream side only** (NDI itself doesn't touch upstream — full-duplex, separate capacity) | n/a — this is exactly what the mitigation removes | Drops to just rclone + Overseer + Flock per theatre (25.8-35.8 Mbps) — even a fully-loaded 6-theatre group sits at 15.5-21.5% upstream, nowhere near a concern |
| **Mothership's own bonded NIC, mass-fallback disaster case** (all 12 theatres on NDI at once) | Downstream 1,560 Mbps + upstream ~1,553 Mbps worst case — both sides genuinely loaded | Downstream unchanged at 1,560 Mbps (NDI doesn't care about the ATEM side), but **upstream drops to just 310-430 Mbps** — the mitigation's biggest payoff shows up here, not at the single-router level |

**The one number worth remembering from this table: 97% at worst case, single theatre.**
The mitigation reliably resolves the per-router ceiling problem (128% → under 100%
either way), but under the pessimistic rclone assumption it leaves only about 3% headroom
— comfortably safe on paper, uncomfortably close in practice if anything else about that
theatre's traffic runs a little hotter than modeled. Pausing ATEM ingest fleet-wide during
a genuine mass NDI fallback is unambiguously the right call regardless — that's where the
mitigation actually earns its keep, cutting the mothership's own upstream load from
~1,553 Mbps to ~310-430 Mbps (a ~72-80% reduction depending on realistic vs. worst-case
rclone) at exactly the moment the network is already under the most stress.

**Alternative: a higher-throughput GL-iNet model.** Would fix this numerically, but not
cleanly for either mid/high-tier option:

| Model | WireGuard (vendor) | LAN ports | Form factor | ~Price | NDI-fallback+ATEM+Overseer+Flock utilization |
|---|---|---|---|---|---|
| A-1300 (current) | 170 Mbps | 2 | Pocket travel router | ~$100 | 128% |
| Beryl AX (GL-MT3000) | [300 Mbps](https://www.gl-inet.com/en-us/products/gl-mt3000) | **1 only** | Pocket travel router | ~$100-140 | 73% |
| Flint 2 (GL-MT6000) | [900 Mbps](https://www.gl-inet.com/en-us/products/gl-mt6000) | 5 (2×2.5GbE+4×1GbE, minus WAN) | 233×137×53mm, 761g | ~$170 | 24% |

**Beryl AX is a trap for this design specifically** — better throughput, but only 1 LAN
port total, so it can't replicate the dedicated-ATEM-port wiring
([`docs/topology.md`](topology.md)) without an external switch ATEM would then have to
share anyway, undoing exactly the isolation that wiring was for.

**Flint 2 genuinely solves it** — ports to spare, comfortable margin (24% vs. 128%) — but
it's ~3x the volume and ~5x the weight of the A-1300, no longer pocket-travel-router class
for a 14-unit touring kit, at ~70% more per unit. Its 900 Mbps figure carries the same
caveat as the A-1300's 170 Mbps: a vendor benchmark, not a confirmed real-world
simultaneous-bidirectional rating under this exact mixed traffic.

**Given the software mitigation above already fixes the same problem at zero hardware
cost and no footprint change**, a router swap isn't the recommended fix — it's a genuine
option if the touring-kit footprint and cost increase are acceptable trade-offs, not a
clear upgrade.

## Is the current plan (4 VLANs, 3 theatres each) sufficient?

**Yes, with large margin — at the VLAN level.** Per-VLAN upstream aggregate:
3 × 88 = **~265 Mbps realistic (27% of 1 Gbps)**, 3 × 129 ≈ 388 Mbps even at worst case
(39%). Downstream is lower still. The VLAN was never actually at risk — the per-router
ceiling above is the one that actually bites first, and no VLAN count changes that.

## Consolidating further (fewer, more expensive VLANs handling more theatres each)

| VLANs | Theatres/VLAN | Upstream, realistic | Upstream, worst case | Verdict |
|---|---|---|---|---|
| 4 (current) | 3 | 265 Mbps (27%) | 388 Mbps (39%) | Comfortable, as designed |
| 3 | 4 | 353 Mbps (35%) | 518 Mbps (52%) | Comfortable, but now over half the link at worst case |
| **2** | **6** | **529 Mbps (53%)** | **776 Mbps (78%)** | **Workable, real margin eroding — over half the link even at realistic load, no longer the wide 65% worst-case margin it had before either monitoring stream existed** |
| 1 | 12 | **1058 Mbps (106% — exceeds the link even at realistic load)** | **1553 Mbps (155%)** | **Not viable, full stop** — this used to only fail at worst case; it now fails under normal expected conditions |

The worst-case column is normally the one that matters for a go/no-go call, but **1 VLAN
has crossed a real threshold here**: it no longer needs an unlucky worst-case day to fail,
it exceeds the link under the *realistic*, expected-case assumptions this whole document
otherwise treats as the comfortable baseline. **2 VLANs (6 theatres each) is still the
furthest safe consolidation**, but between Overseer and Flock, the two monitoring streams
have eaten a real chunk of its margin — 78% worst-case (was 65% before either existed),
and now over half the link (53%) even at realistic load, which wasn't true before. Worth
re-weighing whether 2 VLANs is still the right call now that "comfortable" and "worst
case" are closer together than they used to be. This is still **at the VLAN level; the
per-router finding above is tighter and applies regardless**. This holds for normal
operation (SRT primary) — **see the NDI fallback scenario below, which revises this** for
the case where the backup path has to carry real load.

## If the NDI backup path actually activates — very different math

The bandwidth model above assumes SRT is what's actually flowing downstream. NDI (full,
not HX) is a fundamentally different animal: **~130 Mbps at 1080p50 with WireGuard
overhead, roughly constant regardless of content** ([official NDI spec](https://docs.ndi.video/all/getting-started/white-paper/bandwidth)) —
NDI's compression doesn't get cheaper for static/motion-graphics content the way SRT's
H.264 long-GOP does. That's ~12-22x the SRT figures above, and it changes which scenario
the VLAN-count decision actually needs to survive.

**A single theatre falling back is a non-event at the VLAN level** — 130 Mbps extra on
one theatre's downstream fits comfortably even inside a fully-loaded 6-theatre VLAN group
(though see the per-router finding above — that theatre's own A-1300 is a tighter
constraint than the VLAN). The real VLAN-level question is a **mass fallback**: since
BirdDog Central/NDI is a separate path from Restreamer/SRT, a Restreamer failure (a single
container, single point of failure) would push *every* theatre onto NDI simultaneously —
that's the scenario worth sizing for, not the single-theatre case.

| VLANs | Theatres/VLAN | Downstream if ALL theatres in the group fall back to NDI at once (incl. presenter internet) | Verdict |
|---|---|---|---|
| 4 (current) | 3 | 450 Mbps (45%) | Still comfortable |
| 3 | 4 | 600 Mbps (60%) | Workable, less margin than 4 but not tight |
| **2 (bandwidth-only recommendation above)** | **6** | **900 Mbps (90%)** | **Tight — no real margin left** |
| 1 | 12 | 1800 Mbps (180%) | Not viable at any scale |

This is the direct trade-off the earlier 2-VLAN recommendation glossed over: it's safe for
*normal* operation, but a mass NDI fallback at 2 VLANs leaves almost no headroom (90%,
combined with whatever ATEM upstream is doing on the other direction at the same time).
At the current 4-VLAN split, the same event is still comfortable (45%).

**Revised recommendation:** if the design needs to gracefully survive a mass simultaneous
NDI fallback (Restreamer going down, most plausible trigger), **stay at 3-4 VLANs rather
than consolidating to 2** — the bandwidth-only case for 2 VLANs assumed the backup path
stays rare and low-volume, which doesn't hold if you actually need it to work at full
scale. If a mass fallback event is judged acceptable to handle operationally instead (e.g.
running degraded/reduced-quality NDI, or accepting some theatres go dark until Restreamer
recovers, rather than provisioning full-bandwidth NDI for all 12 at once), 2 VLANs remains
viable — but that's now an explicit choice being made, not a free consequence of the SRT
numbers alone.

## Splitting further instead (more, cheaper-per-theatre but more numerous VLANs)

Going the other direction (6 or 12 VLANs, 1-2 theatres each) buys essentially nothing on
the bandwidth side — even the current 4-VLAN plan runs at 27-39% utilization under normal
SRT operation, and a comfortable 45% even under a mass NDI fallback (see above), nowhere
near needing more headroom. It also does nothing for the per-router NDI-fallback finding
above, since that's a single-router problem, not something more VLANs can fix. The only
genuine benefit of more/smaller VLANs is **fault isolation**: a failed venue port or
switch takes out fewer theatres. Given the explicit cost pressure on VLAN count, the
bandwidth numbers don't support this direction — it's a resilience trade-off to make
consciously if at all, not one the traffic model asks for.

## The highest-leverage lever: real-time ATEM ingest is the dominant cost

ATEM ISO ingest is ~71% of realistic upstream load per theatre — still the dominant
single item, but down from ~92% before either monitoring stream existed (~80% with just
Overseer), now that Overseer's and Flock's flat 10.4 Mbps apiece are real contributors,
not noise. It exists purely for near-real-time review during the event — see
[`docs/atem-iso-ingest.md`](atem-iso-ingest.md)'s "master vs. mirror" framing: **the
ATEM's own SSD remains the authoritative master regardless**, pulled in full after each
session either way. If VLAN count/cost turns out to be the binding constraint rather than
a one-time design choice, deferring ATEM ingest to end-of-session pulls (instead of
continuous near-real-time) drops per-theatre upstream from ~88 Mbps to **~25.8 Mbps
realistic / ~35.8 Mbps worst case** (rclone + Overseer's 10.4 Mbps + Flock's 10.4 Mbps,
none of which go away — **unlike ATEM ISO, neither monitoring stream is deferrable, both
are live feeds**) — at which point **1 VLAN for all 12 theatres sits at ~31% realistic /
~43% worst-case utilization**. Real, workable margin, but a genuinely different number
from the "trivially safe ~12%" this lever used to buy before either monitoring stream
existed — it's still the single biggest lever available (bigger than any VLAN-topology
change), and it's still enough to make 1 VLAN viable where it otherwise now isn't (see
the table above), just not quite the near-zero-risk free pass it once was. Losing same-day
review access to footage (not the final deliverable) is still the cost. Has nothing to do
with the per-router NDI-fallback finding above — that's purely a downstream/NDI issue.

## VMix nodes' uplinks

Not yet assigned to a VLAN group in the existing docs. Given the cost pressure, they
shouldn't get dedicated VLANs of their own for just 2 nodes — fold each into whichever
group its adjacent theatre already belongs to (Node 1 → Theatre 1's group, Node 2 →
Theatre 4's group). VMix record-ingest bitrate is unconfirmed (see
[`docs/vmix-record-ingest.md`](vmix-record-ingest.md) open items), but even at a generous
assumed 20-30 Mbps/PC (comparable to a single ATEM channel), adding 2 PCs' worth of
traffic to a 6-theatre VLAN group (529 Mbps realistic) still leaves room, if less than it
used to — worth re-checking against the 2-VLAN group's now-thinner margin above once
VMix's real bitrate is confirmed. The same per-router
NDI-fallback caveat above would apply to the VMix node's own A-1300 too, if its record
ingest and an NDI fallback ever coincide on that same router.

## Recommendation

- **Confirm the full-duplex assumption with the venue** before finalizing any count.
- **Set up the per-theatre NDI-fallback mitigation regardless of VLAN count** — pause/
  throttle that theatre's ATEM ingest when it falls back to NDI. This isn't optional the
  way the VLAN-count trade-offs are; without it, one theatre alone can exceed its own
  A-1300's ~170 Mbps ceiling (128% combined) even on a fully over-provisioned VLAN. It
  still works with both monitoring streams added, but with less margin doing so than it
  used to (92% post-mitigation, was 79% before Overseer/Flock existed) — worth being
  aware this mitigation has less room to absorb a *fifth* new upstream/downstream load if
  one ever gets proposed.
- **1 VLAN is no longer a real option, full stop — not just a worst-case risk.** Before
  Overseer and Flock existed, 1 VLAN was viable if ATEM ingest was deferred to
  end-of-session pulls. It still is (~31% realistic / ~43% worst-case with ATEM
  deferred), but with real-time ATEM ingest kept, 1 VLAN now exceeds the link even under
  normal, expected-case assumptions (106%), not just an unlucky worst-case day. If a
  single VLAN is genuinely the target, real-time ATEM ingest has to be deferred — that's
  now a requirement rather than the discretionary lever it used to be.
- **Decide how much a mass NDI fallback needs to survive at full quality** — the actual
  fork in the VLAN-count recommendation, not a footnote:
  - If a Restreamer failure pushing all 12 theatres onto NDI simultaneously must keep
    working at full 1080p50 quality: **stay at 3-4 VLANs**. 2 VLANs puts that scenario at
    90% utilization with no real margin.
  - If that event is acceptable to handle operationally instead (degraded/reduced-quality
    NDI, or some theatres going dark until Restreamer recovers, rather than full-bandwidth
    NDI for all 12 at once): **2 VLANs (6 theatres each)** is still viable for normal
    SRT-primary operation, but weigh this carefully now — halves current VLAN cost, keeps
    real-time ATEM ingest, but margin has eroded a real amount since this recommendation
    was first made: 78% worst-case (was 65% before either monitoring stream existed) and
    now over half the link (53%) even at realistic load, which wasn't true before. This
    is the trade-off most worth revisiting given everything added since the original
    2-VLAN call.
- **Fold both VMix nodes into their adjacent theatre's VLAN group** rather than requesting
  dedicated VLANs for them, but re-check their real bitrate against the thinner margin
  above once it's confirmed.
- **If VLAN cost pressure is severe enough to want a single VLAN**, deferring ATEM ISO
  ingest to end-of-session pulls is now a requirement, not an optional lever — real-time
  ATEM ingest alone pushes 1 VLAN over capacity at realistic load, before worst case even
  enters into it. Note this doesn't fix the NDI downstream problem, though — 1 VLAN is
  not viable for a mass NDI fallback (180%) regardless of what's done on the ATEM side,
  since that's a downstream, not upstream, load.
- **Resolve the presenter-internet question** (shared with production VLANs or separate
  venue circuit) before treating any of the above as final — it's folded into the
  downstream figures above as a conservative shared-infrastructure assumption, and
  downstream isn't the binding constraint under normal SRT operation, but it should still
  be confirmed.
