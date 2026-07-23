# VMix record ingest

Same rclone mount + `rsync --append` combo as
[`config/atem-iso-ingest/rclone-mount-rsync/`](../atem-iso-ingest/rclone-mount-rsync/),
retargeted at each VMix PC's Windows SMB share instead of an FTP server. See
[`docs/vmix-record-ingest.md`](../../docs/vmix-record-ingest.md) for the full design —
short version: SMB is a real network filesystem protocol, so mounting it here is the
native way to access it, arguably a more natural fit than it was for the ATEM's FTP-only
server. `rsync --append` is what makes this incremental either way — it seeks to the
destination's current size and transfers only the tail, not a whole-file re-copy.

Covers all 4 VMix PCs: VMix Node 1 (`192.168.20.21`/`.22`) and VMix Node 2
(`192.168.21.21`/`.22`) — see [`docs/ip-address-map.md`](../../docs/ip-address-map.md).

## Files

- [`rclone.conf.template`](rclone.conf.template) + [`generate-rclone-conf.sh`](generate-rclone-conf.sh)
  — produces `rclone.conf` with all 4 PCs' SMB remotes.
- [`mount-and-sync.sh`](mount-and-sync.sh) — mounts all 4 shares, then loops
  `rsync --append` into the same Nextcloud External Storage pattern the ATEM ingest uses.
  Run with `VERIFY=1` for a one-shot `--append-verify` integrity pass once a session ends.
  (The settled design also dual-writes to the edit-suite NAS in the same pass — see
  [`docs/live-editing.md`](../../docs/live-editing.md) — but that second destination is
  not yet implemented here; tracked as
  [`docs/open-questions.md`](../../docs/open-questions.md) item 15.)
- [`setup-nextcloud-external-storage.sh`](setup-nextcloud-external-storage.sh) — one-time
  Nextcloud mount setup (`occ files_external:create`) + the cron line for targeted rescans.

## Before running — none of this is confirmed against real hardware yet

- **Enable SMB sharing on each VMix PC** for its recording folder. A dedicated,
  minimal-privilege local Windows account (read-only on just that folder) is strongly
  preferred over a shared/admin account — e.g.:
  ```powershell
  New-SmbShare -Name "VMixRecordings" -Path "C:\VMixRecordings" -ReadAccess "DOMAIN\vmix-ingest-ro"
  ```
- **Confirm the actual recording folder path and share name** on the real PCs — the
  scripts use placeholders (`REPLACE_WITH_SHARE_NAME`, `REPLACE_WITH_SMB_USER`,
  `REPLACE_WITH_OBSCURED_PASSWORD`), not assumed defaults.
- **Confirm what VMix is actually recording** (program mix vs. per-input ISO, resolution,
  codec/bitrate) — this determines the real bandwidth load, not assumed here. Each VMix
  node has its own dedicated GL-iNet A-1300 uplink (not shared with the theatre it sits
  near), so this traffic doesn't compete with that theatre's ATEM ingest or SRT feed —
  but it still needs to fit inside that node's own ~170 Mbps ceiling.
- **Run `setup-nextcloud-external-storage.sh` once** before starting `mount-and-sync.sh`.

## Native CIFS mount alternative

Since SMB is natively mountable on Linux (`mount -t cifs`), you could skip `rclone mount`
for this leg entirely and mount the share directly, then run the same `rsync --append`
against that mount point — one fewer moving part than going through rclone's SMB backend.
This script uses rclone anyway, to reuse the exact same tooling/config pattern as the
ATEM ingest rather than introduce a third mechanism. Worth revisiting if operational
simplicity matters more than consistency with the ATEM setup.
