#!/usr/bin/env bash
# Generates theatre-1-alt.sh .. theatre-12-alt.sh from theatre-network-alt.template.
# Mirrors ../gl-inet/generate-configs.sh — same per-theatre pattern, different backend.
set -euo pipefail

cd "$(dirname "$0")"

for theatre in $(seq 1 12); do
	x=$(( theatre + 1 ))
	sed -e "s/__THEATRE__/${theatre}/g" -e "s/__X__/${x}/g" \
		theatre-network-alt.template > "theatre-${theatre}-alt.sh"
	chmod +x "theatre-${theatre}-alt.sh"
done

echo "Generated theatre-1-alt.sh .. theatre-12-alt.sh"
