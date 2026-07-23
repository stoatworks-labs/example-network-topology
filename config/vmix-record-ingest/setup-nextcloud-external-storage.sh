#!/usr/bin/env bash
# One-time setup: mount each VMix PC's record-ingest folder into Nextcloud as External
# Storage (Local), same pattern as ../atem-iso-ingest/setup-nextcloud-external-storage.sh.
# Run inside the Nextcloud container/host, as the user occ normally runs as (usually www-data).
set -euo pipefail

NEXTCLOUD_USER="${NEXTCLOUD_USER:-admin}"
LOCAL_BASE="${VMIX_RECORD_LOCAL_BASE:-/mnt/user/nextcloud-external}"

occ app:enable files_external

for node in 1 2; do
	for pc in 1 2; do
		mount_point="VMixNode${node}-PC${pc}"
		datadir="${LOCAL_BASE}/VMixNode${node}/PC${pc}"

		mkdir -p "$datadir"

		occ files_external:create "$mount_point" local null::null \
			-c "datadir=${datadir}" \
			--user="$NEXTCLOUD_USER"

		echo "Mounted ${datadir} -> ${NEXTCLOUD_USER}/files/${mount_point}"
	done
done

cat <<'EOF'

Setup done. Add a cron entry for targeted (not full) rescans, e.g.:

  */2 * * * * for n in 1 2; do for p in 1 2; do occ files:scan --path="/admin/files/VMixNode${n}-PC${p}"; done; done

Adjust the "/admin/files/..." path if NEXTCLOUD_USER wasn't "admin".
EOF
