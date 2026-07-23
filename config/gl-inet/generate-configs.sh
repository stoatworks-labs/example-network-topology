#!/usr/bin/env bash
# Generates theatre-1.uci .. theatre-12.uci from theatre-network.uci.template, and
# vmix-node-1.uci / vmix-node-2.uci from vmix-node-network.uci.template.
# Re-run after editing either template; don't hand-edit the generated files.
set -euo pipefail

cd "$(dirname "$0")"

for theatre in $(seq 1 12); do
	x=$(( theatre + 1 ))   # Theatre 1 -> 192.168.2.x, Theatre 12 -> 192.168.13.x
	sed -e "s/__THEATRE__/${theatre}/g" -e "s/__X__/${x}/g" \
		theatre-network.uci.template > "theatre-${theatre}.uci"
done

echo "Generated theatre-1.uci .. theatre-12.uci"

# VMix Node 1 -> 192.168.20.x, off Theatre 1. VMix Node 2 -> 192.168.21.x, off Theatre 4.
declare -A VMIX_SUBNET=( [1]=20 [2]=21 )
declare -A VMIX_THEATRE=( [1]=1 [2]=4 )
for node in 1 2; do
	sed -e "s/__NODE__/${node}/g" -e "s/__X__/${VMIX_SUBNET[$node]}/g" -e "s/__THEATRE__/${VMIX_THEATRE[$node]}/g" \
		vmix-node-network.uci.template > "vmix-node-${node}.uci"
done

echo "Generated vmix-node-1.uci, vmix-node-2.uci"
