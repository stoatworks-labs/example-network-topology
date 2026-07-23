#!/usr/bin/env bash
# Generates one combined rclone.conf with all 12 theatres' ATEM FTP remotes, from
# rclone.conf.template. Re-run after editing the template.
set -euo pipefail

cd "$(dirname "$0")"
OUT="rclone.conf"

> "$OUT"
for theatre in $(seq 1 12); do
	x=$(( theatre + 1 ))   # Theatre 1 -> 192.168.2.2, Theatre 12 -> 192.168.13.2
	sed -e "s/__THEATRE__/${theatre}/g" -e "s/__X__/${x}/g" \
		rclone.conf.template >> "$OUT"
	echo "" >> "$OUT"
done

echo "Generated $OUT with 12 theatre remotes (atem-theatre1 .. atem-theatre12)"
echo "Remember: replace REPLACE_WITH_FTP_USER / REPLACE_WITH_OBSCURED_PASSWORD in each block."
