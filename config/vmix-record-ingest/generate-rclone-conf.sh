#!/usr/bin/env bash
# Generates one combined rclone.conf with all 4 VMix PCs' SMB remotes, from
# rclone.conf.template. Re-run after editing the template.
set -euo pipefail

cd "$(dirname "$0")"
OUT="rclone.conf"

> "$OUT"
for node in 1 2; do
	if [ "$node" = "1" ]; then x=20; else x=21; fi   # Node 1 -> 192.168.20.x, Node 2 -> 192.168.21.x
	for pc in 1 2; do
		pcoctet=$(( 20 + pc ))   # PC 1 -> .21, PC 2 -> .22
		sed -e "s/__NODE__/${node}/g" -e "s/__PC__/${pc}/g" -e "s/__X__/${x}/g" -e "s/__PCOCTET__/${pcoctet}/g" \
			rclone.conf.template >> "$OUT"
		echo "" >> "$OUT"
	done
done

echo "Generated $OUT with 4 VMix PC remotes (vmix-node1-pc1 .. vmix-node2-pc2)"
echo "Remember to replace REPLACE_WITH_SMB_USER / REPLACE_WITH_OBSCURED_PASSWORD in each block."
