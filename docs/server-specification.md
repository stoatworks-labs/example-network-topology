# Consolidated services server — minimum specification

The server itself is already on hand (see [`docs/topology.md`](topology.md)) — this
document calculates the **target minimum spec** to check that hardware against, working
forward from the actual workload this box runs
([`docs/topology.md`](topology.md)'s VM/container table) rather than a generic
"decent server" guess. Where a figure depends on something this repo hasn't pinned down
(the mothership's own VMix instance's camera/channel count, the event's actual day
count/hours), that's flagged explicitly rather than assumed — see
[`docs/open-questions.md`](open-questions.md) for the running list.

## Storage — three pools, not one array

Unraid's traditional parity array is built around mixed-size spinning disks with a
single-write-at-a-time parity bottleneck, absorbed by an SSD cache pool that the
overnight "mover" drains onto the array — a good fit for bulk archival storage, a poor
fit for a box whose entire storage workload here is already flash. Recommendation: skip
the legacy array entirely and use three separate Unraid **pools** (ZFS, available since
Unraid 6.12), each sized and mirrored for what it actually holds.

### Container/VM pool

Holds `docker.img`, all container `appdata` (including the three databases — MariaDB,
MongoDB, Redis — that want fast, low-latency small-I/O access), and both Windows VM
vdisks.

| Item | Estimate |
|---|---|
| VMix instance vdisk | ~100 GB (OS + app + local scratch) |
| BirdDog Central vdisk | ~80 GB (OS + app) |
| `docker.img` | ~50 GB |
| Combined `appdata` (12 containers + the Tailscale subnet router + 3 DBs) | ~58 GB |
| **Total** | **~288 GB** |

**Minimum: 500 GB usable, mirrored NVMe** (2× ~512GB+ NVMe) — comfortable headroom over
the ~288 GB estimate, and mirrored because rebuilding two Windows VMs from scratch mid-event
is real downtime, not just an inconvenience. NVMe specifically (not SATA SSD) because VM
and database performance is latency-sensitive, not throughput-bound.

**Drive class: mainstream consumer NVMe with onboard DRAM cache** (not a DRAM-less
budget drive) is genuinely sufficient here — no need for the enterprise tier the
recording pool below needs. VM/appdata churn is nowhere near enough sustained write
volume to meaningfully test even consumer-grade endurance ratings, and the workload cares
about consistent low-queue-depth latency (how snappy a container restart or a DB query
feels), which good consumer NVMe already delivers.

### Content pool — 500 GB (as specified)

Nextcloud's own storage: theatre laptop content synced via rclone (established at
10-20 GB/theatre × 12 theatres = **120-240 GB**, see
[`docs/bandwidth-analysis.md`](bandwidth-analysis.md)), plus Nextcloud's own app/database
footprint and versioning overhead (flagged as a real multiplier in
[`docs/atem-iso-ingest.md`](atem-iso-ingest.md)'s versioning caveat — version retention
settings directly affect how much of this budget versioning eats into). 500 GB gives
roughly 2-4x headroom over the raw 120-240 GB content estimate, which comfortably
absorbs version history without needing an aggressive retention policy from day one.

**Recommendation: mirrored, SATA SSD is adequate** (no NVMe-level latency requirement
here) — mirrored less for data-loss prevention (every laptop is still the source of
truth for its own content even if this copy is lost) and more for **availability**: a
lost content pool mid-event means re-running the initial bulk sync for all 12 theatres,
which is itself only a ~20-40 minute operation at 50-100 Mbps
(`docs/bandwidth-analysis.md`) but is a real, avoidable disruption during a live event.

**Drive class: same reasoning as the container/VM pool** — mainstream consumer SATA SSD
with DRAM cache, the cheapest reasonable tier that still isn't a DRAM-less budget part.
Gentle, sporadic write pattern; no case for spending more here.

### Recording pool — 8 TB, all-flash (as specified)

This is where the calculation actually matters — both *why* it has to be flash and
*whether 8 TB is enough*.

**Why all-flash, not spinning disk — it's not about raw throughput.** Combined worst-case
write load onto this pool, from [`docs/bandwidth-analysis.md`](bandwidth-analysis.md)'s
own established figures:

| Source | Per-unit worst case | Count | Total |
|---|---|---|---|
| ATEM ISO ingest | ~90.4 Mbps (94 Mbps incl. WireGuard tax) | 12 theatres | ~1,085 Mbps |
| VMix Record ingest | ~30 Mbps (assumed, unconfirmed — see `docs/open-questions.md`) | 4 PCs | ~120 Mbps |
| **Combined** | | | **~1,205 Mbps ≈ 151 MB/s** |

151 MB/s sustained is well within a single 7200 RPM HDD's *rated sequential* throughput
on paper — so the case for flash isn't the aggregate number, it's the **access pattern**.
That 151 MB/s isn't one stream, it's **16 independent files being appended to
concurrently** (12 ATEM + 4 VMix, each on its own ~60-90s poll cycle — see
[`docs/atem-iso-ingest.md`](atem-iso-ingest.md) and
[`docs/vmix-record-ingest.md`](vmix-record-ingest.md)), with Nextcloud's own targeted
`occ files:scan` indexing calls layered on top of that. A spinning disk pays
a real seek penalty (~5-15ms) every time it switches between those 16+ scattered write
targets — under this specific concurrent-scattered pattern, achievable HDD throughput
collapses to a small fraction of its rated sequential number, while any flash drive
(no seek penalty) handles 151 MB/s of concurrent random-ish writes without strain. The
"all-flash" requirement is about the write *pattern* this design creates, not the volume.

**Does 8 TB actually cover the event?** This is the one figure genuinely blocked on an
input this repo doesn't have: **actual event duration (days × active-recording hours/day)
isn't established anywhere in this design.** Working from the same combined-load figures:

| | Combined rate | 8 TB covers |
|---|---|---|
| Realistic (5-7 active ATEM channels/theatre, per `docs/bandwidth-analysis.md`) | ~99.4 MB/s ≈ 349 GB/hr | **~23.5 hours** |
| Worst case (all 9 ATEM channels/theatre) | ~150.6 MB/s ≈ 530 GB/hr | **~15.5 hours** |

At a typical ~8-10 hour active-program day, that's roughly **1.5-3 days** of continuous
worst-to-realistic-case recording before the pool fills — workable for a short event,
tight for a longer one, and this assumes every theatre is actually near its "realistic"
active-channel count for the whole day, which per the original design intent ("likely
only 4-6 [channels] will actually have any data") may be conservative. **Confirm actual
event length against this table before treating 8 TB as settled** — if it's a multi-day
event without a periodic archive-off step already planned, either the day count needs to
fit the budget above, or a nightly archive-to-cold-storage step needs adding to free
capacity for the next day. The ingest pipelines write directly into Nextcloud's External
Storage location and, in the same pull, the edit-suite NAS
([`docs/atem-iso-ingest.md`](atem-iso-ingest.md),
[`docs/live-editing.md`](live-editing.md)) — neither write has an offload stage that
frees *this* pool. Tracked in `docs/open-questions.md`.

**Redundancy — worth adding capacity for, not assumed in the 8 TB figure.** This pool is
the authoritative archive: the dual-write to the edit-suite NAS
([`docs/live-editing.md`](live-editing.md)) does give the footage a second landing spot
at ingest time, but that copy may be a curated subset (open-questions #12) and one of the
candidate NAS units is RAID 0 — so a failure here still risks footage that can't be
re-shot. Two ways to get 8 TB *usable* with 1-drive fault tolerance:

| Option | Raw capacity needed | Trade-off |
|---|---|---|
| **2× 8 TB NVMe, mirrored** | 16 TB raw | Simplest to reason about, fastest resilver, 50% capacity overhead |
| **4× ~2.7 TB NVMe, RAID-Z1** | ~10.8 TB raw | 75% capacity efficiency vs. 50%, slower resilver on failure, more drives to manage |

Recommend the mirror for the same reason Unraid was chosen over TrueNAS SCALE elsewhere
in this design (`docs/topology.md`) — operational simplicity, since this may be
maintained by AV staff rather than a storage specialist, matters more here than squeezing
out the last few TB of efficiency.

**Endurance.** Since this repo already treats the router hardware as reusable
across events (see [`docs/gl-inet-rationale.md`](gl-inet-rationale.md)), the same applies
here — a full pool fill is roughly 8 TB of actual flash writes (these are byte-range
*appends*, not whole-file rewrites, so total written ≈ total recorded, not a multiple of
it), and a mirrored pair each independently absorb that same 8 TB per event. Even a
deliberately-generous worst-case estimate — ~530 GB/hr sustained for a full 24 h/day
across ~20 event-days a year, beyond what the pool could even hold without nightly
archive-off — comes to roughly 260 TB/year of
actual writes to the pool — comfortably inside what even the *lower* enterprise
endurance tier (see below) is rated for over a normal warranty period, so endurance
headroom isn't actually the tight constraint here once the right drive class is picked.

**Drive class: this is the one pool where consumer-grade flash — even a good,
DRAM-cached, high-TBW consumer drive — isn't the right call, and endurance isn't the
reason.** The deciding factor is **power-loss protection (PLP)**: capacitor-backed
circuitry that flushes a drive's write cache to permanent storage if power drops
mid-write. Consumer/prosumer NVMe drives don't have this. A generator hiccup, a tripped
breaker, or a UPS transfer glitch mid-event — exactly the kind of thing a live event's
own power setup can produce — risks losing whatever was sitting in the drive's write
cache at that instant, on the one pool in this whole design with no second copy of the
data anywhere else. That's the actual argument for **enterprise-class NVMe** here
specifically (not "enterprise is always better," which isn't true for the other two
pools above) — server-validated drives with capacitor-backed PLP, provisioned for
sustained high-queue-depth writes without the cache-cliff behavior consumer drives show
once their fast write cache fills under prolonged concurrent load. Enterprise drives are
also sold in more than one endurance tier (commonly around 1 drive-write-per-day vs. 3×
that for a heavier-duty tier) — the lighter of the two tiers already has large margin
over this workload's realistic annual write volume, so there's no need to pay for the
heavier tier's endurance on top of the PLP requirement that's actually driving this
choice.

## Write caching

With every pool already flash (no legacy spinning array behind anything), the classic
Unraid "SSD cache pool absorbing writes before the overnight mover" pattern doesn't apply
here — there's no slow array for it to shield. What actually buffers the bursty,
16-concurrent-stream ingest pattern described above is:

- **RAM** — the OS page cache smooths write bursts before they hit the drives (see the
  RAM section below, which already budgets for this).
- **The drives' own onboard DRAM cache** — a real purchasing consideration: choose NVMe
  drives with onboard DRAM (not DRAM-less/QLC-only budget drives), since sustained
  multi-stream concurrent writes are exactly the workload DRAM-less drives handle worst.

## NIC — validating the already-decided 2× bonded GbE

[`docs/topology.md`](topology.md) already settled on 2× gigabit NICs, bonded (802.3ad
LACP). Checking that against the heaviest combined load this design has identified —
the mass-NDI-fallback disaster scenario from
[`docs/bandwidth-analysis.md`](bandwidth-analysis.md), layered on top of full ATEM
ingest:

| Direction | Load | Total |
|---|---|---|
| Inbound (theatres → mothership) | ATEM ingest worst case (~1,123 Mbps) + VMix ingest (~120 Mbps) + ATEM Overseer (~125 Mbps) + Flock (~125 Mbps) | ~1,493 Mbps |
| Outbound (mothership → theatres), all 12 theatres on NDI fallback simultaneously | 12 × ~130 Mbps | ~1,560 Mbps |

(Inbound total updated from an earlier ~1,205 Mbps once ATEM Overseer's and Flock's
monitoring/preview streams were added — see [`docs/topology.md`](topology.md) — each
contributing ~125 Mbps fleet-wide on top of what was already accounted for.)

Both directions run independently over a full-duplex link, so they don't stack against
each other — but each direction needs to fit across the bond's two physical 1 Gbps links
via LACP's per-flow hashing (each *individual* flow is capped at 1 Gbps, since LACP
doesn't split one flow across both links). With 14+ independent theatre flows in each
direction (12 ATEM ingest + 12 Overseer + 12 Flock inbound, each individually well under
1 Gbps — worst case ~94 Mbps ATEM, ~10.4 Mbps apiece for Overseer/Flock, ~130 Mbps NDI
outbound), the hash has plenty of separate flows to distribute across both links without
any single one bottlenecking — **the existing 2× 1GbE bonded design still checks out,
including against the worst-case disaster scenario**, not just normal operation. Margin
has narrowed since this was first validated (~1,205 → ~1,493 Mbps inbound, both still
comfortably under the bond's ~2,000 Mbps aggregate), the same erosion
[`docs/bandwidth-analysis.md`](bandwidth-analysis.md) tracks everywhere else Overseer and
Flock touch this design — see that doc's own worked-through comparison of this exact
disaster scenario with and without pausing ATEM ingest fleet-wide, which is the more
consequential mitigation than the NIC choice itself.

**One load deliberately NOT counted against this bond: the dual-write to the edit-suite
NAS.** The same ingest containers that produce the inbound figures above also write every
recording out again to the edit-suite NAS at `192.168.22.2`
([`docs/live-editing.md`](live-editing.md)) — up to another ~1,243 Mbps of outbound at
worst case. If that leg transited the theatre-facing bond it would stack on top of the
NDI-fallback outbound and break the conclusion above — so it must **not**: the edit
suite is its own 10GbE LAN, and this box needs a separate edit-LAN-facing interface
(a 10GbE NIC, or at minimum its own dedicated port) for that traffic, counted in the
spec alongside the 2× bonded theatre-facing GbE.

**Worth it anyway: 2× 2.5GbE, if the box/switch already support it at no real added
cost.** Doesn't change the conclusion above, but many current motherboards ship 2.5GbE
onboard already, and it buys real margin against the one thing this analysis can't fully
account for — LACP hash distribution isn't perfectly even in practice, and real headroom
above a "checks out, but not by a huge margin" number is cheap insurance if it's already
sitting on the board.

## RAM

| Workload | Estimate | Basis |
|---|---|---|
| VMix instance VM | 32 GB | [vMix's own "Mid" tier guidance](https://www.coremicro.com/blogs/support/vmix-minimum-system-requirements) (4-6 cameras, HD multi-cam) — see GPU section for the caveat on which tier actually fits |
| BirdDog Central VM | 8 GB | Routing/control app, not encode — lighter than VMix |
| Nextcloud + MariaDB + Redis | 6 GB | InnoDB buffer pool + PHP workers + Redis cache |
| UniFi Controller + MongoDB | 3 GB | Manages only the Cloud Gateway (the 14 GL-iNet routers are GLKVM-Cloud's, not UniFi's) — MongoDB's WiredTiger cache doesn't need much at this scale |
| ATEM Overseer + Flock | 5 GB | Unlike the other admin/control-plane containers below, these two are actually decoding video — up to 12 concurrent theatre streams apiece for their monitoring dashboards (see [`docs/bandwidth-analysis.md`](bandwidth-analysis.md)), not just pushing config or metadata |
| Restreamer, NDI Discovery, DERP, both ingest containers, GLKVM-Cloud (rttys+coturn), ATEM Fleet Admin, Tailscale router | 9 GB | 9 lightweight containers, ~1 GB each budgeted |
| Unraid OS + ZFS ARC (3 pools, ~8.5 TB combined) | 8 GB | Soft ZFS guidance is roughly 1 GB RAM per TB of pool for decent ARC hit rate — this is a floor, not a hard requirement, ZFS is adaptive |
| **Subtotal** | **~71 GB** | |
| **Minimum, with headroom** | **96 GB** | 71 GB doesn't map to a clean DIMM configuration on an 8-channel platform (see CPU section) — 96 GB is the next practical capacity above it with real margin, not just rounding up to the subtotal |
| **Recommended** | **128 GB** | Matches vMix's own "64 GB for heavy Instant Replay" guidance with room to spare, and gives ZFS ARC meaningfully more room across all three pools |

**ECC, not just capacity.** All three storage pools above are ZFS — ZFS leans on RAM for
checksumming and its ARC read cache, and a bit flip in ordinary (non-ECC) RAM can get
silently written into a checksum or into the recording pool's parity/mirror data before
anyone notices, which defeats the whole point of using ZFS for the one pool holding
unrepeatable footage. ECC RAM catches and corrects that class of error before it
propagates. Pair this with a platform that has *validated* ECC support (see the CPU
section below) — ECC only protects against silent corruption if it's actually enabled
and working, which isn't guaranteed on every board that merely accepts ECC modules
electrically.

## CPU

| Workload | Estimate | Basis |
|---|---|---|
| VMix instance | 8 cores dedicated | [vMix's official "Mid" tier](https://www.coremicro.com/blogs/support/vmix-minimum-system-requirements): "Core i7 / Core Ultra 7, 3.5-4.5 GHz, 8+ cores" for 4-6 camera HD multi-cam |
| BirdDog Central | 2 cores | Routing/control, not encode |
| Docker stack (12 containers + the Tailscale subnet router + 3 DBs) | 5-7 cores shared | Mostly I/O-bound; Restreamer's SRT relay (remux, not transcode, per this design's primary path) and ATEM Overseer + Flock (each decoding up to 12 concurrent monitoring streams) are the heaviest individual containers, still light relative to VMix's own budget |
| Unraid OS/array overhead | 2 cores | |
| **Subtotal** | **17-19 cores** | |
| **Minimum** | **16 cores / 32 threads, high sustained (not just boost) clock** | Rounds slightly below the subtotal's high end — see platform-class discussion below, which matters more than squeezing out the last 1-3 cores |

**The platform class matters more than the core count, and this is worth spelling out
rather than just naming a chip.** A 16-core desktop CPU is easy to find — the actual
constraint is everything *around* it:

- **PCIe lanes.** Between the GPU and up to 8 NVMe drives spread across the three pools
  above, this box realistically wants 24-40+ usable PCIe lanes. Mainstream consumer
  desktop platforms (the socket a typical Ryzen 9 or Core i9/Ultra 9 sits in) top out
  around half that once you account for the GPU slot, chipset-shared bandwidth, and
  onboard I/O all competing for the same limited lane budget — workable if you're
  willing to compromise the number of drives or share lanes through bifurcation, tight
  otherwise. A **workstation/HEDT-class platform** (Threadripper PRO or a high-end Xeon
  W, not a consumer desktop chip) is the category that actually clears this without
  compromise — this is the same reason HEDT platforms exist at all, not a preference.
- **Validated ECC.** Some mainstream consumer boards technically accept ECC memory
  electrically, but whether ECC actually *functions* — gets detected, enabled, and does
  correction — varies board-to-board and isn't something to gamble on for the pool
  holding irreplaceable footage. Workstation platforms build ECC support into the
  platform itself, officially validated, not a maybe.
- **Sustained clock over peak boost.** vMix is a continuously-loaded, real-time workload,
  not a bursty one — a CPU's *base* clock under sustained all-core load is a better
  predictor of live-production performance than its headline single-core boost number.
  Worth actually comparing base clocks across whichever specific chips are shortlisted,
  not just core count.

**Trade-off worth being upfront about**: workstation/HEDT platforms cost meaningfully
more (CPU + motherboard together) than the mainstream desktop alternative, and idle power
draw for 24/7 operation runs higher too. That's a real cost, not a rounding error — but
the alternative doesn't actually satisfy this box's lane and ECC requirements, so it's
not a straightforward "save money" option, it's a different, smaller build with real
compromises attached.

**Also required, not a separate line item: IOMMU (Intel VT-d) or AMD-Vi support** on
both the CPU and motherboard, for GPU passthrough to the VMix VM — already flagged as
unconfirmed in [`docs/open-questions.md`](open-questions.md) #1; whatever CPU/board
combination is checked against this spec, confirm this specifically. Both platform
classes above support it; this is really only a risk on very old hardware.

## GPU

VMix strongly recommends a dedicated NVIDIA GPU for NVENC hardware encode — already the
existing design's own reasoning for GPU passthrough
([`docs/topology.md`](topology.md): "Windows-only; benefits from hardware encode").
Current vMix-published tiers ([source](https://www.coremicro.com/blogs/support/vmix-minimum-system-requirements)):

| Tier | GPU | Use case |
|---|---|---|
| Entry (1-2 cams) | RTX 5060 Ti (16 GB) | 1080p stream + record |
| **Mid (4-6 cams)** | **RTX 5070 Ti** | HD multi-cam, 1080p replay |
| Demanding (8+ cams / 4K) | RTX 5080+ | 4K productions, multicorder |

**Genuinely can't pin an exact minimum here**, and worth being upfront about why: the
2 VMix *nodes* clearly handle "4× BirdDog P400 cameras, 2× VMix PCs" each
([`docs/topology.md`](topology.md)) — but what the mothership's own separate **VMix
instance** VM actually processes isn't documented anywhere in this repo. Recommend the
**Mid tier (RTX 5070 Ti-equivalent performance/encode class)** as a reasonable working
target absent that detail — check the existing "decent GPU" already on hand
([`docs/topology.md`](topology.md)/[`docs/open-questions.md`](open-questions.md)) against
this table once the mothership VMix instance's actual role/channel count is confirmed.

**Card class: a workstation/professional-line GPU at that performance tier, not the
consumer gaming card itself** — this is a genuinely different recommendation from just
naming a GeForce tier, and worth the reasoning:

- **Chassis fit.** Consumer gaming GPUs are built for open-air desktop-tower cooling
  (multiple large fans dumping heat sideways into the case, relying on front-to-back case
  airflow to clear it). A server chassis rarely has that airflow profile. Workstation
  cards in this class commonly ship as compact, single-slot, blower-style coolers that
  pull air in and exhaust it straight out the card's own bracket — the form factor is
  built for a server/rack enclosure, not retrofitted into one.
- **Driver behavior under continuous load.** Consumer GPU drivers are tuned for gaming
  sessions — burst to a high boost clock, then throttle. A continuously-loaded encode
  workload running for a multi-day event wants a driver branch built for sustained clocks
  under indefinite load, which is what the workstation/enterprise driver track is
  actually validated for.
- **ECC VRAM**, same rationale as ECC system RAM above — protects against silent
  corruption during a multi-day continuous run.
- **Licensing.** Consumer GPU license terms typically carry restrictive language around
  "datacenter"-style deployment that doesn't clearly define whether a single VM on
  owned hardware counts — a real, if loosely-worded and thinly-enforced, gray area for
  running a gaming card inside a server chassis long-term. The workstation/professional
  line's license doesn't carry that ambiguity; it's built for exactly this deployment
  shape. Worth noting this is a licensing question, not a technical one — passthrough
  itself works fine on either card class.
- The actual NVENC encode silicon is typically the **same generation** across the
  consumer and workstation lines at a comparable performance tier — this isn't a "buy
  workstation for better encoding" argument, the encode quality/capability is
  essentially equivalent. It's specifically about fit for continuous server operation.

**Worth knowing when pricing this out**: the historical cost gap between a
workstation-class card and its consumer-tier equivalent has narrowed substantially in
2026 amid broader GPU memory/component pricing pressure — confirm current pricing before
assuming the workstation option carries the large multiplier it used to.

## Summary — minimum spec to check the existing server against

| Component | Minimum | Why this class |
|---|---|---|
| CPU | 16 cores / 32 threads, workstation/HEDT platform (Threadripper PRO or Xeon W class, not a mainstream desktop chip), strong sustained clock | PCIe lane count for GPU + up to 8 NVMe drives, validated ECC support |
| Motherboard | Workstation/HEDT chipset, IOMMU/AMD-Vi capable, validated ECC support, enough PCIe 4.0/5.0 lanes for 3 NVMe pools + GPU | Same reasoning as CPU — the two are a package |
| RAM | 96 GB minimum, 128 GB recommended, ECC, populate all available channels | ZFS data integrity across all 3 pools; matches vMix's own heavy-use guidance |
| GPU | NVENC-capable, workstation/professional line at an RTX 5070 Ti-equivalent tier (unconfirmed exact tier — see above) | Server-chassis cooling fit, sustained-clock driver, ECC VRAM, cleaner passthrough licensing |
| Container/VM pool | 500 GB usable, mirrored, consumer-grade DRAM-cached NVMe | Latency-sensitive VM/DB workload; consumer endurance is more than enough |
| Content pool | 500 GB usable, mirrored, consumer-grade DRAM-cached SATA SSD | Gentle Nextcloud file I/O; no case for spending more |
| Recording pool | 8 TB usable, mirrored (16 TB raw), enterprise-grade NVMe with power-loss protection | PLP is the deciding factor — this pool is the authoritative archive (the edit-suite NAS dual-write copy may be a subset, and may be RAID 0 — see [`docs/live-editing.md`](live-editing.md)); confirm event duration against the capacity table above first |
| Network | 2× 1GbE, bonded LACP (already decided, validated above) — 2× 2.5GbE if free to obtain — **plus a separate edit-LAN-facing interface (10GbE) for the dual-write leg** | Checks out even against the mass-NDI-fallback disaster scenario, provided the edit-suite dual-write never rides the theatre-facing bond |

Everything above is a calculated **target**, not a purchase order — the actual box is
already on hand per `docs/topology.md`. Next step is checking its real spec against this
table and updating [`docs/open-questions.md`](open-questions.md) #1 with the result.
