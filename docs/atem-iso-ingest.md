# ATEM ISO ingest — near-real-time, Nextcloud-aware

Goal: get each theatre's ATEM Mini Extreme ISO recordings (up to 9 H.264 streams — 8
camera ISOs + program — at ~10 Mbps each per this design's working figure; **Blackmagic's
spec is up to 70 Mb/s per ISO file**, see [Bandwidth](#bandwidth)) onto the mothership's Nextcloud as close to
real time as the hardware allows, without corrupting anything and without the theatre's
uplink falling permanently behind.

## The two hardware facts that shape this

- **The ATEM has a built-in FTP server**, and files can be browsed/transferred over it
  *while recording is still in progress* — confirmed via multiple independent accounts
  ([aaronparecki.com](https://aaronparecki.com/2022/01/25/8/),
  [Directory Opus forum](https://resource.dopus.com/t/ftp-access-to-atem-mini-iso-failed/42809)).
  This is also the only mechanism available — the unit has no NDI output and its Ethernet
  port doesn't expose the drive over SMB/NFS, only FTP. **This holds for the original
  ATEM Mini Extreme ISO only.** The newer **ATEM Mini Extreme ISO G2** has a 10G Ethernet
  port and shares its CFexpress/USB recording media as a network disk
  ([Blackmagic tech specs](https://www.blackmagicdesign.com/products/atemmini/techspecs)) —
  if the theatres have G2 units, a mount-based pull (like the VMix ingest) becomes
  possible. Confirm which model is actually deployed.
- **The files are very likely safe to read mid-write.** Blackmagic markets editing an ISO
  recording in DaVinci Resolve *before the event even finishes* — that only works if the
  container format is structured so a partial file is valid up to whatever's been flushed
  so far (in practice, this means fragmented MP4 — periodic `moof`/`mdat` boxes rather
  than one index at the very end). Treat this as **very likely true given the marketed
  capability, but worth a quick empirical check** (copy a file mid-recording, confirm
  `ffprobe`/a media player can open it) before relying on it operationally.

## Why not plain rsync, and why not plain rclone sync

**Plain rsync can't connect at all** — it needs SSH or an rsync daemon on the far end, and
the ATEM only speaks FTP. There's no bridging that directly; the ATEM never exposes rsync
or SSH.

**A naive periodic `rclone sync`/whole-file re-copy doesn't survive the bandwidth math.**
Real numbers: at a realistic 4–6 active camera ISOs + program (~10 Mbps each, i.e.
50–70 Mbps), a 3-hour session is already ~68–95 GB. Re-uploading the *entire current file*
every 10 minutes stops fitting in that 10-minute window at the A-1300's ~170 Mbps ceiling
once the session is ~25–35 minutes old (~19 minutes at the 90 Mbps worst case) — and
that ignores everything else sharing the uplink — after which the sync falls permanently
behind.
Genuinely incremental transfer isn't a nice-to-have here, it's required.

**Two ways to get genuinely incremental transfer** — both implemented, pick one (see
[`config/atem-iso-ingest/`](../config/atem-iso-ingest/)):

| | Mechanism | Why it's incremental |
|---|---|---|
| **`pull-iso.py`** (default) | FTP's own `REST <offset>` command — the same "resume from byte offset" mechanism `curl --continue-at`/`lftp --continue`/`wget -c` use | Deterministic: explicitly requests only bytes past the last known offset. No cache layer involved. |
| **`rclone-mount-rsync/`** (alternative) | `rclone mount` presents the ATEM's FTP share as a local FUSE path; `rsync --append` (not rsync's general checksum-diff algorithm) transfers only the tail past the destination's current size | Also deterministic — `--append` seeks straight to the destination's size rather than reading/hashing the whole file, so it doesn't depend on rclone's VFS cache behaving well for a growing remote file — a real concern for mount-based approaches that `--append` sidesteps entirely |

Both are legitimate. `pull-iso.py` has fewer moving parts (no persistent FUSE mounts to
supervise); `rclone-mount-rsync/` uses tools you may already operate day to day, at the
cost of 12 FUSE mounts to keep healthy. Neither uses rsync's *general* block-checksum
algorithm (which genuinely would require reading the whole file every pass) — that
algorithm only saves network bytes when both ends speak the rsync wire protocol to each
other, which isn't possible against an FTP-only source regardless of what sits in between.

## Architecture

Centralized entirely on the Unraid server as its own container (`192.168.1.17`) — no
software installed on any theatre laptop, consistent with how BirdDog Central/NDI
Discovery Server/DERP are already consolidated there (the mothership VMix VM was removed —
see [`docs/open-questions.md`](open-questions.md) #10). Reaches each theatre's ATEM over
Tailscale subnet routing (see
[`docs/tailscale.md`](tailscale.md) — this is exactly the "route between subnets where
needed" case the subnet-router setup was built for). Described below for the default
(`pull-iso.py`) — the `rclone-mount-rsync/` alternative differs only in the pull mechanism,
writing into the same Nextcloud folders the same way.

```
ATEM (192.168.X.2, FTP) --[Tailscale subnet route]--> Unraid: atem-iso-ingest container
                                                              |
                                                     incremental REST-resume pull
                                                              |
                                                              v
                                            local mirror file, growing in lockstep
                                            (written directly into the folder Nextcloud
                                             has mounted as External Storage — Local)
                                                              |
                                                   targeted `occ files:scan` (short cycle)
                                                              |
                                                              v
                                                     visible in Nextcloud, growing
```

1. **Pull step** (`atem-iso-ingest` container, new — see [`config/atem-iso-ingest/`](../config/atem-iso-ingest/)):
   for each theatre, on a schedule (e.g. every 60–120s), list the ATEM's FTP directory,
   and for each media file, `REST`-resume from the last recorded byte offset and append
   the new bytes to a local mirror file. A small state file tracks per-file offsets so a
   restart doesn't re-pull from scratch.
2. **No separate upload/chunking step.** The pull step writes directly into
   `/mnt/user/nextcloud-external/TheatreN/ISO/` — the same path mounted into Nextcloud as
   an External Storage (Local) folder for that theatre. There's no WebDAV re-upload of the
   growing file at all, so the "whole-file re-sync is too slow" problem simply doesn't
   apply on this side — it's a same-host filesystem write, not a WAN transfer.
3. **Nextcloud awareness**: a short-interval, *targeted* `occ files:scan --path=...` (not
   `--all`) picks up the new file size on Nextcloud's side. Because this only touches one
   theatre's folder and runs locally on the same box, it's cheap even at a 1-2 minute
   cadence — unlike scanning the whole Nextcloud tree, which would not be.
4. **On session end**, a final pull + final targeted scan catches the last bytes and
   whatever moov/index finalization is *appended* when the ATEM's recording actually
   stops. **It does not catch finalization that rewrites earlier bytes in place** — MP4
   muxers commonly patch a box size or header near the start of the file when recording
   stops (OBS's hybrid-MP4 "soft remux" is a documented example:
   [obsproject.com](https://obsproject.com/blog/obs-studio-hybrid-mp4)). Both ingest
   methods are append-only and would leave such a mirror with stale header bytes. Whether
   the ATEM does this is unconfirmed; until it is, treat the mirror as "review copy" and
   either re-pull the finished file in full or run a checksum comparison against the
   source before treating it as final (see Open items).

**Second write destination for live editing.** The pull step also writes the same
growing mirror file to a second mount — the edit suite's dedicated NAS
(`192.168.22.x`), not just Nextcloud's External Storage. One read off the ATEM, two
writes, not a separate re-sync reading Nextcloud's copy back out. See
[`docs/live-editing.md`](live-editing.md) for the full editing subsystem this feeds —
not yet reflected in [`config/atem-iso-ingest/pull-iso.py`](../config/atem-iso-ingest/pull-iso.py)
itself, which currently only writes the one Nextcloud destination; adding the second
write path is a real code change, tracked in [`docs/open-questions.md`](open-questions.md).

## Bandwidth

> **The ~10 Mbps-per-stream figure is this design's working assumption, not Blackmagic's
> spec — and it may be badly low.** Blackmagic's tech specs say the ISO inputs are recorded
> as "H.264 .mp4 files at up to 70Mb/s quality"
> ([blackmagicdesign.com](https://www.blackmagicdesign.com/products/atemmini/techspecs)),
> and third-party guides report the ISO bitrate is fixed (not tied to the record-quality
> setting) at roughly 45-70 Mb/s depending on frame rate
> ([worshipmetrics.com](https://worshipmetrics.com/kb/switchers/blackmagic-design/blackmagic-atem-mini-pro-iso-setup-guide/)).
> At those rates a single theatre's realistic 5 streams is ~225-350 Mbps (9 streams:
> ~405-630 Mbps), already **above the A-1300's ~170 Mbps ceiling on its own** — the pull
> would fall steadily behind real time rather than staying near-real-time, and
> fleet-wide output would be ~1.2-3.4 TB/hour. The table below, and every downstream
> figure in [`docs/bandwidth-analysis.md`](bandwidth-analysis.md) and
> [`docs/server-specification.md`](server-specification.md), is only valid if a real unit
> confirms ~10 Mbps. Measure a real ISO file (`ffprobe` bitrate, or file size ÷ duration)
> before building on these numbers.

| Scenario | Aggregate | vs. A-1300 ceiling |
|---|---|---|
| Worst case, all 9 streams active | 90 Mbps | tight but under ~170 Mbps |
| Realistic, 4 cams + program | 50 Mbps | comfortable headroom |
| Realistic, 6 cams + program | 70 Mbps | comfortable headroom |

This rides the theatre's uplink in the *opposite direction* from the incoming SRT feed
(~8–50 Mbps, see [`docs/open-questions.md`](open-questions.md)) — if the link is genuinely
full-duplex-capable at its rated throughput, those two shouldn't compete much. But the
ingest does **not** have the upstream direction to itself: the theatre's ATEM Overseer
monitoring stream and Flock SRT preview (~10.4 Mbps each) run theatre → mothership
alongside it, plus bursty rclone. The authoritative per-router upstream model —
~129 Mbps worst case against the A-1300's ~170 Mbps ceiling — is in
[`docs/bandwidth-analysis.md`](bandwidth-analysis.md); the table above covers the ingest
in isolation only. Worth validating the full-duplex assumption in practice rather than
assuming it, since the ~170 Mbps A-1300 figure was a single-direction benchmark, not a
confirmed simultaneous-bidirectional rating.

## Master vs. mirror

Frame this as: **the ATEM's own SSD remains the authoritative final master** (complete,
guaranteed-valid once recording stops) — pulled in full at the end of each session/day
regardless. **Nextcloud holds a near-real-time, continuously-updated mirror** for early
review/rough-cut purposes during the event. That framing resolves the tension between
"want it fast" and "want it guaranteed correct": you get both, from two different
consumers of the same underlying data.

## Nextcloud versioning caveat

Nextcloud's versioning app may retain snapshots on repeated changes to the same file path.
Configure version retention/expiry for the ISO folders (or disable versioning there
specifically) so a multi-hour growing recording doesn't accumulate many near-duplicate
historical versions before Nextcloud's own expiry curve catches up. Not a blocker, just
worth tuning once this is running for real.

## Open items

- **Confirm the 10 Mbps/stream figure and actual active-channel count** against the real
  ATEM recording settings, rather than relying on the estimate used for the bandwidth math
  above — highest-priority item here, since Blackmagic's own spec (up to 70 Mb/s per ISO)
  would invalidate the near-real-time premise over a ~170 Mbps uplink (see Bandwidth).
- **Confirm the ATEM model (original vs. G2)** — the G2 exposes its media as a network
  disk, which changes which pull mechanism is the natural fit (see the hardware facts at
  the top).
- **`pull-iso.py` only lists one FTP directory, non-recursively, and only picks up
  `.mp4`/`.mov`.** Blackmagic's ISO recordings are written as a *folder* per recording
  (program file, a `Video ISO Files` subfolder, an `Audio Source Files` subfolder of
  `.wav`s, and a `.drp` Resolve project), so as written it would miss the camera ISOs and
  audio unless `ATEM_FTP_REMOTE_DIR` happens to point at the right subfolder — and that
  folder name changes per recording. The script needs a recursive walk (and a decision on
  whether to pull `.wav`/`.drp` too) once the real FTP layout is confirmed on a unit. The
  `rclone-mount-rsync/` alternative already recurses (`rsync -a`).
- **Decide the end-of-session integrity step.** Both methods are append-only (see step 4
  under Architecture). For `rclone-mount-rsync/`, `VERIFY=1` now does a full
  `--checksum` comparison and repairs any differing blocks in place; note that this reads
  every file in full through the FTP mount — i.e. a full re-download over the theatre's
  uplink — so run it after the session, not during. `pull-iso.py` has no equivalent yet.
- **Confirm partial-file playability empirically** — copy a file mid-recording, check it
  opens/scrubs correctly, before treating the "safe to read mid-write" assumption as
  settled rather than "very likely."
- **Tune the scan interval and pull interval** against real session lengths and available
  Unraid CPU/disk headroom, once the server's full spec is known (see
  [`docs/open-questions.md`](open-questions.md)).
- **Confirm the ATEM's actual FTP file/folder naming** (not assumed here — the ingest
  script lists whatever's present rather than hardcoding filenames, precisely because this
  wasn't confirmed against a real unit).
- **If using the `rclone-mount-rsync/` alternative**, test `rsync --append` against a
  genuinely growing file on a real ATEM before trusting it operationally — confirm it
  only transfers the new tail each pass (e.g. watch network throughput or
  `--itemize-changes` output), and budget for supervising 12 persistent FUSE mounts
  (auto-remount on failure), which `pull-iso.py` doesn't need at all. Also confirm new
  bytes show up promptly: FTP has no change notification, so a growing file's size on
  the mount only refreshes when rclone's directory cache expires (default 5 minutes — the
  script now sets `--dir-cache-time 30s`;
  [rclone mount docs](https://rclone.org/commands/rclone_mount/)).
