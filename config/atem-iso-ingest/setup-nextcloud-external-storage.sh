#!/usr/bin/env bash
# One-time setup: mount each theatre's ISO ingest folder into Nextcloud as External
# Storage (Local), so pull-iso.py's output is visible without any WebDAV upload step.
# Run inside the Nextcloud container/host, as the user occ normally runs as (usually www-data).
#
# Requires the "files_external" app enabled: occ app:enable files_external
set -euo pipefail

NEXTCLOUD_USER="${NEXTCLOUD_USER:-admin}"   # the Nextcloud user these mounts should appear under
LOCAL_BASE="${ATEM_ISO_LOCAL_BASE:-/mnt/user/nextcloud-external}"

occ app:enable files_external

for theatre in $(seq 1 12); do
	mount_point="Theatre${theatre}-ISO"
	datadir="${LOCAL_BASE}/Theatre${theatre}/ISO"

	mkdir -p "$datadir"

	occ files_external:create "$mount_point" local null::null \
		-c "datadir=${datadir}" \
		--user="$NEXTCLOUD_USER"

	echo "Mounted ${datadir} -> ${NEXTCLOUD_USER}/files/${mount_point}"
done

cat <<'EOF'

Setup done. Add a cron entry for targeted (not full) rescans, e.g.:

  */2 * * * * for t in $(seq 1 12); do occ files:scan --path="/admin/files/Theatre${t}-ISO"; done

Adjust the "/admin/files/..." path if NEXTCLOUD_USER wasn't "admin". A 1-2 minute cadence
is cheap here since it's scoped to one small folder per theatre, not a full-tree scan.
See ../../docs/atem-iso-ingest.md for why a targeted scan (not `occ files:scan --all`) is
the right call.
EOF
