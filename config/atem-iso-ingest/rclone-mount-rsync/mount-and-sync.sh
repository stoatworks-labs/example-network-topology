#!/usr/bin/env bash
# ATEM ISO ingest — alternative to pull-iso.py, using rclone mount (FUSE) + rsync
# --append instead of a direct FTP REST-based pull script. See
# ../../../docs/atem-iso-ingest.md for the full comparison of the two approaches.
#
# --append transfers only the bytes past the destination's current size — it does NOT
# hash/diff the whole file the way rsync's general algorithm does, and does NOT depend
# on rclone's VFS cache behavior for growing files (there is no cache in play here;
# --vfs-cache-mode=off below, deliberately). This is what makes this approach genuinely
# incremental over the network, same as pull-iso.py's direct REST-resume, just built
# from off-the-shelf tools instead of a custom script.
#
# --append trusts that the beginning of the file never changes once written (true for
# a pure append-only recording). Run mount-and-sync.sh with VERIFY=1 for a final
# --append-verify pass (reads/checksums the whole file) once a session ends, as a
# one-time integrity check rather than paying that cost every cycle.
set -euo pipefail

RCLONE_CONFIG="$(dirname "$0")/rclone.conf"
MOUNT_BASE="${ATEM_MOUNT_BASE:-/mnt/atem-mounts}"
DEST_BASE="${ATEM_ISO_LOCAL_BASE:-/mnt/user/nextcloud-external}"
SYNC_INTERVAL_SECONDS="${ATEM_ISO_SYNC_INTERVAL:-90}"
VERIFY="${VERIFY:-0}"

mount_theatre() {
	local theatre="$1"
	local mount_point="${MOUNT_BASE}/theatre${theatre}"
	mkdir -p "$mount_point"

	if ! mountpoint -q "$mount_point" 2>/dev/null; then
		rclone mount "atem-theatre${theatre}:" "$mount_point" \
			--config "$RCLONE_CONFIG" \
			--vfs-cache-mode off \
			--read-only \
			--daemon
		echo "[theatre-${theatre}] mounted at ${mount_point}"
	fi
}

sync_theatre() {
	local theatre="$1"
	local mount_point="${MOUNT_BASE}/theatre${theatre}"
	local dest="${DEST_BASE}/Theatre${theatre}/ISO/"
	mkdir -p "$dest"

	local append_flag="--append"
	if [ "$VERIFY" = "1" ]; then
		append_flag="--append-verify"   # full checksum pass — run occasionally, not every cycle
	fi

	rsync -a "$append_flag" --itemize-changes "${mount_point}/" "$dest" \
		|| echo "[theatre-${theatre}] rsync pass failed (will retry next cycle)"
}

if [ "$VERIFY" = "1" ]; then
	echo "ATEM ISO ingest — one-shot --append-verify integrity pass"
else
	echo "ATEM ISO ingest (rclone mount + rsync --append) starting"
	echo "Mounts under ${MOUNT_BASE}, syncing into ${DEST_BASE}, every ${SYNC_INTERVAL_SECONDS}s"
fi

for theatre in $(seq 1 12); do
	mount_theatre "$theatre"
done

while true; do
	for theatre in $(seq 1 12); do
		sync_theatre "$theatre"
	done
	[ "$VERIFY" = "1" ] && break   # one-shot verify run, not a loop
	sleep "$SYNC_INTERVAL_SECONDS"
done
