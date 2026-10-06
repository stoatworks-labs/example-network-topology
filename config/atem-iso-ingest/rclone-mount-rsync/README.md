# Alternative: rclone mount + rsync --append

An alternative to [`../pull-iso.py`](../pull-iso.py), using off-the-shelf tools
(`rclone`, `rsync`) instead of a custom script. See
[`docs/atem-iso-ingest.md`](../../../docs/atem-iso-ingest.md) for the full comparison —
short version: both achieve genuinely incremental network transfer (only the newly
appended bytes cross the theatre's uplink each cycle), via different mechanisms:

- `pull-iso.py` uses FTP's own `REST` command directly — deterministic, no cache layer.
- This alternative uses `rsync --append`, which seeks straight to the destination's
  current size and transfers only the tail — it does **not** rely on rclone's VFS cache
  behaving well for a growing remote file (cache is explicitly off, `--vfs-cache-mode off`
  below), so it sidesteps the caching-uncertainty concern entirely.

## Trade-offs vs. `pull-iso.py`

- **More moving parts.** 12 persistent `rclone mount` FUSE mounts to supervise vs. one
  stateless polling script. A hung FUSE mount is a classic operational pain point —
  budget for health-checking/auto-remount (e.g. a systemd service with `Restart=on-failure`
  per mount, or a periodic `mountpoint -q` check that remounts if needed).
- **`--append` trusts the file's beginning never changes** once written — true for a pure
  append-only recording, same assumption `pull-iso.py` makes (and it never corrects a
  header rewritten in place when recording stops). Run with `VERIFY=1` for a one-time
  full `--checksum --inplace` pass that repairs any differing blocks — do this once per
  finished session, not every cycle, since it reads every file in full through the FTP
  mount (a full re-download over the theatre's uplink). It deliberately does **not** use
  `--append-verify`, which skips any file already the same size on both sides and so
  never checks a fully-synced file.
- **Directory cache.** FTP has no change notification in rclone, so the mount only
  sees a growing file's new size when its directory cache expires (default 5 minutes);
  the script sets `--dir-cache-time 30s` so the 90s sync interval is real.
- **Uses tools you may already operate day to day**, if that's a real advantage for your
  team over maintaining a small Python script.

## Setup

1. `rclone obscure 'the-real-ftp-password'` — never put a plaintext password in
   `rclone.conf`.
2. Edit [`rclone.conf.template`](rclone.conf.template) with the real FTP username and the
   obscured password, then run [`generate-rclone-conf.sh`](generate-rclone-conf.sh) to
   produce `rclone.conf` with all 12 theatre remotes.
3. Run [`mount-and-sync.sh`](mount-and-sync.sh) — mounts all 12 ATEMs, then loops
   `rsync --append` every `ATEM_ISO_SYNC_INTERVAL` seconds (default 90s) into the same
   Nextcloud External Storage folders `pull-iso.py` would use — run
   [`../setup-nextcloud-external-storage.sh`](../setup-nextcloud-external-storage.sh)
   first, same as with the other approach. (Same dual-write caveat as the parent
   README: the documented second write to the edit-suite NAS isn't implemented here
   yet either.)
4. Once a session ends, run `VERIFY=1 ./mount-and-sync.sh` for a one-shot integrity pass
   on that theatre's files.

## Before relying on this operationally

Test the actual mount + `--append` behavior against a real ATEM with a file that's
genuinely growing during the test — confirm rsync only transfers the new tail each pass
(e.g. watch network throughput, or check `--itemize-changes` output) rather than assuming
it from this description.
