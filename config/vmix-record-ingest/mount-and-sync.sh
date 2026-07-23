#!/usr/bin/env bash
# VMix record ingest — same rclone mount + rsync --append combo used for the ATEM ISO
# ingest alternative (see ../atem-iso-ingest/rclone-mount-rsync/), retargeted at each
# VMix PC's Windows SMB share instead of an FTP server.
#
# SMB is a genuine network filesystem protocol (unlike FTP), so mounting it is the
# native way to access it, not a workaround — this is arguably a more natural fit than
# the ATEM case, not a stretch of the same pattern. See ../../../docs/vmix-record-ingest.md
# for the full rationale, including why rsync --append is what makes this incremental
# (same reasoning as the ATEM doc: it seeks to the destination's current size and
# transfers only the tail, rather than reading/hashing the whole file).
#
# Note: native Linux CIFS mount (`mount -t cifs`) is an even simpler alternative to
# `rclone mount` for SMB specifically, since it needs no FUSE bridge at all — this
# script uses rclone anyway to reuse the exact same tooling/config pattern as the ATEM
# ingest. See docs/vmix-record-ingest.md for that trade-off.
set -euo pipefail

RCLONE_CONFIG="$(dirname "$0")/rclone.conf"
MOUNT_BASE="${VMIX_MOUNT_BASE:-/mnt/vmix-mounts}"
DEST_BASE="${VMIX_RECORD_LOCAL_BASE:-/mnt/user/nextcloud-external}"
SYNC_INTERVAL_SECONDS="${VMIX_RECORD_SYNC_INTERVAL:-90}"
VMIX_SHARE_NAME="${VMIX_SHARE_NAME:-REPLACE_WITH_SHARE_NAME}"   # confirm against the real PCs
VERIFY="${VERIFY:-0}"

# node, pc -> theatre-adjacent label and mount/dest paths
remotes() {
	echo "1 1"
	echo "1 2"
	echo "2 1"
	echo "2 2"
}

mount_pc() {
	local node="$1" pc="$2"
	local remote="vmix-node${node}-pc${pc}"
	local mount_point="${MOUNT_BASE}/node${node}-pc${pc}"
	mkdir -p "$mount_point"

	if ! mountpoint -q "$mount_point" 2>/dev/null; then
		rclone mount "${remote}:${VMIX_SHARE_NAME}" "$mount_point" \
			--config "$RCLONE_CONFIG" \
			--vfs-cache-mode off \
			--read-only \
			--daemon
		echo "[vmix-node${node}-pc${pc}] mounted at ${mount_point}"
	fi
}

sync_pc() {
	local node="$1" pc="$2"
	local mount_point="${MOUNT_BASE}/node${node}-pc${pc}"
	local dest="${DEST_BASE}/VMixNode${node}/PC${pc}/"
	mkdir -p "$dest"

	local append_flag="--append"
	[ "$VERIFY" = "1" ] && append_flag="--append-verify"   # full checksum pass — run occasionally, not every cycle

	rsync -a "$append_flag" --itemize-changes "${mount_point}/" "$dest" \
		|| echo "[vmix-node${node}-pc${pc}] rsync pass failed (will retry next cycle)"
}

if [ "$VERIFY" = "1" ]; then
	echo "VMix record ingest — one-shot --append-verify integrity pass"
else
	echo "VMix record ingest (rclone mount + rsync --append) starting"
	echo "Mounts under ${MOUNT_BASE}, syncing into ${DEST_BASE}, every ${SYNC_INTERVAL_SECONDS}s"
fi

while read -r node pc; do
	mount_pc "$node" "$pc"
done < <(remotes)

while true; do
	while read -r node pc; do
		sync_pc "$node" "$pc"
	done < <(remotes)
	[ "$VERIFY" = "1" ] && break
	sleep "$SYNC_INTERVAL_SECONDS"
done
