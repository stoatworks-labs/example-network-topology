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
# a pure append-only recording) — it never corrects bytes rewritten in place, e.g. an
# MP4 header patched when recording stops. Run mount-and-sync.sh with VERIFY=1 once a
# session ends for a one-time integrity pass: a full --checksum comparison that repairs
# any differing blocks in place. (Not --append-verify: that SKIPS any file already the
# same size on both sides, so it never checks a fully-synced file.) VERIFY reads every
# file in full through the FTP mount — a full re-download over the theatre's uplink —
# so run it after the session, never during.
#
# --dir-cache-time 30s: FTP has no change notification in rclone, so a growing file's
# size on the mount only refreshes when the directory cache expires (default 5m, which
# would silently stretch the 90s sync interval to ~5 minutes). Keep it below the
# sync interval.
#
# ATEM_ISO_INPUTS (default "1", same variable and meaning as pull-iso.py): which ISO inputs
# cross the network live. The ATEM records every input to its own SSD regardless; this
# only filters what rsync pulls. Program recording always; ISO files only for the listed
# inputs; .mp4/.mov only (audio .wav and the .drp project come with the physical DIT
# offload). Empty = program only. See docs/atem-iso-ingest.md, "Common theatre input map".
# Matches ISO files on "CAM <n>" / "CAM<n>" in the file name (glob, case-insensitive) —
# pull-iso.py's ATEM_ISO_INPUT_PATTERN regex does NOT apply here; if a real unit names
# its ISO files differently (docs/open-questions.md #21), edit build_filters below.
set -euo pipefail

RCLONE_CONFIG="$(dirname "$0")/rclone.conf"
MOUNT_BASE="${ATEM_MOUNT_BASE:-/mnt/atem-mounts}"
DEST_BASE="${ATEM_ISO_LOCAL_BASE:-/mnt/user/nextcloud-external}"
SYNC_INTERVAL_SECONDS="${ATEM_ISO_SYNC_INTERVAL:-90}"
VERIFY="${VERIFY:-0}"
ISO_INPUTS="${ATEM_ISO_INPUTS-1}"

# rsync filter rules: first match wins. Directories are always traversed (-m prunes the
# ones left empty); a chosen input's media files are included; every other CAM file is
# excluded; remaining media (the program recording) is included; everything else excluded.
build_filters() {
	FILTERS=(--include='*/')
	local n ext sep cam
	local -a inputs
	IFS=',' read -r -a inputs <<< "$1"
	for n in "${inputs[@]}"; do
		n="${n//[[:space:]]/}"
		[[ "$n" =~ ^[0-9]+$ ]] || continue
		for sep in ' ' ''; do
			cam="*[Cc][Aa][Mm]${sep}${n}"
			for ext in '[Mm][Pp]4' '[Mm][Oo][Vv]'; do
				# "...CAM 1.mp4" and "...CAM 1 01.mp4", but never "...CAM 10 01.mp4"
				FILTERS+=(--include="${cam}.${ext}" --include="${cam}[!0-9]*.${ext}")
			done
		done
	done
	FILTERS+=(--exclude='*[Cc][Aa][Mm] [0-9]*' --exclude='*[Cc][Aa][Mm][0-9]*'
	          --include='*.[Mm][Pp]4' --include='*.[Mm][Oo][Vv]' --exclude='*')
}

# Per-theatre override: ATEM_ISO_INPUTS_T<n> (e.g. ATEM_ISO_INPUTS_T3="1,2") replaces
# ATEM_ISO_INPUTS for that theatre only, so laptop inputs can be turned on where there's
# router headroom rather than fleet-wide. Empty means no override; "0" = program only.
inputs_for() {
	local var="ATEM_ISO_INPUTS_T$1"
	printf '%s' "${!var:-$ISO_INPUTS}"
}

mount_theatre() {
	local theatre="$1"
	local mount_point="${MOUNT_BASE}/theatre${theatre}"
	mkdir -p "$mount_point"

	if ! mountpoint -q "$mount_point" 2>/dev/null; then
		rclone mount "atem-theatre${theatre}:" "$mount_point" \
			--config "$RCLONE_CONFIG" \
			--vfs-cache-mode off \
			--dir-cache-time 30s \
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

	build_filters "$(inputs_for "$theatre")"

	local mode_flags=(--append)
	if [ "$VERIFY" = "1" ]; then
		# full checksum pass, repairs differing blocks in place — run once per finished session
		mode_flags=(--checksum --inplace --no-whole-file)
	fi

	rsync -a -m "${mode_flags[@]}" "${FILTERS[@]}" --itemize-changes "${mount_point}/" "$dest" \
		|| echo "[theatre-${theatre}] rsync pass failed (will retry next cycle)"
}

if [ "$VERIFY" = "1" ]; then
	echo "ATEM ISO ingest — one-shot --checksum integrity pass"
else
	echo "ATEM ISO ingest (rclone mount + rsync --append) starting"
	echo "Mounts under ${MOUNT_BASE}, syncing into ${DEST_BASE}, every ${SYNC_INTERVAL_SECONDS}s"
	echo "ISO inputs: ${ISO_INPUTS:-none} + program (per-theatre ATEM_ISO_INPUTS_T<n> overrides apply)"
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
