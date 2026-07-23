# ATEM ISO ingest

Runs entirely on the mothership's Unraid box — no software on any theatre laptop. See
[`docs/atem-iso-ingest.md`](../../docs/atem-iso-ingest.md) for the full design rationale
(why plain rsync can't connect to the ATEM at all, why a naive whole-file re-sync doesn't
survive the bandwidth math, and why no manual video chunking is needed).

**Two documented ingest approaches — pick one, both write into the same Nextcloud
External Storage folders:**

| | Mechanism | Trade-off |
|---|---|---|
| [`pull-iso.py`](pull-iso.py) (default) | Custom script, FTP `REST`/resume directly | Fewer moving parts, no persistent mounts to supervise |
| [`rclone-mount-rsync/`](rclone-mount-rsync/) | `rclone mount` (FUSE) + `rsync --append` | Off-the-shelf tools, but 12 FUSE mounts to keep healthy |

Both are genuinely incremental (only new bytes cross the theatre's uplink each cycle) —
they just get there differently. See `docs/atem-iso-ingest.md` for the full comparison.

**Second destination — documented, not yet implemented.** The settled design dual-writes
each growing file to the edit-suite NAS (`192.168.22.x`) alongside Nextcloud, in the
same pull — see [`docs/live-editing.md`](../../docs/live-editing.md). As shipped, both
approaches here write only the Nextcloud destination; adding the second write path is
tracked as [`docs/open-questions.md`](../../docs/open-questions.md) item 15.

## Files

- [`pull-iso.py`](pull-iso.py) — the default ingest loop. For each theatre, connects to
  the ATEM's built-in FTP server over Tailscale subnet routing (`192.168.X.2`), and pulls
  only the bytes appended since the last check (FTP `REST`), writing directly into the
  folder mounted into Nextcloud as External Storage.
- [`rclone-mount-rsync/`](rclone-mount-rsync/) — the alternative described above, with its
  own setup instructions.
- [`setup-nextcloud-external-storage.sh`](setup-nextcloud-external-storage.sh) — one-time
  setup shared by **either** approach: mounts each theatre's ISO folder into Nextcloud via
  `occ files_external:create`, and prints the cron line for the targeted `occ files:scan`
  that keeps Nextcloud's index current.

## Before running (default: `pull-iso.py`)

Using `rclone-mount-rsync/` instead? Its own setup/run instructions are in
[`rclone-mount-rsync/README.md`](rclone-mount-rsync/README.md) — the rest of this section
is specific to `pull-iso.py`.

- **Confirm FTP credentials and the recording path** against a real ATEM unit — both are
  environment-variable placeholders (`ATEM_FTP_USER`/`ATEM_FTP_PASS`/`ATEM_FTP_REMOTE_DIR`
  in `pull-iso.py`), not assumed defaults, since this wasn't verified against real hardware.
- **Run `setup-nextcloud-external-storage.sh` once** before starting `pull-iso.py`, so the
  destination folders exist and Nextcloud already has them mounted.
- **Add the cron line it prints** for the targeted rescan — without it, files land on disk
  but never show up in Nextcloud's UI.

## Running `pull-iso.py`

Intended as a long-lived Docker container on the Unraid box (matches how
Restreamer/NDI Discovery Server/DERP are already run there):

```sh
docker run -d --name atem-iso-ingest \
  -e ATEM_FTP_USER=... -e ATEM_FTP_PASS=... \
  -v /mnt/user/nextcloud-external:/mnt/user/nextcloud-external \
  -v /mnt/user/appdata/atem-iso-ingest:/mnt/user/appdata/atem-iso-ingest \
  python:3-slim python /app/pull-iso.py
```

(Mount `pull-iso.py` into `/app/` — this is a plain script, not published as a prebuilt
image.)
