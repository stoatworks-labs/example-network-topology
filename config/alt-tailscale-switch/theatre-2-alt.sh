#!/usr/bin/env bash
# Alternative to GL-iNet A-1300 for Theatre 2 — generic Linux box (mini-PC or
# the control laptop) + plain switch, using nftables/dnsmasq instead of a router
# appliance's built-in NAT/DHCP. Tailscale invocation is unchanged from
# ../tailscale-up-all-devices.sh — Tailscale doesn't care what hardware runs it.
#
# Generated from theatre-network-alt.template — do not hand-edit, edit the template
# and re-run generate-configs.sh instead. See docs/topology-alternative-tailscale-switches.md.
#
# Requires 2 NICs (lan0 direct to ATEM, lan1 to the switch) to replicate the dedicated
# ATEM port GL-iNet gives for free — see docs/topology.md for why that port is dedicated.
set -euo pipefail

LAN_IP="192.168.3.1/24"

# --- Interfaces (adjust names to match the actual box's NICs) -------------
ip addr add "$LAN_IP" dev lan0   # ATEM Mini Extreme ISO, direct
ip addr add "$LAN_IP" dev lan1   # switch -> BirdDog Play, PowerPoint/VT laptops, control laptop
ip link set lan0 up
ip link set lan1 up
# wan0: DHCP client to the mothership's Cloud Gateway VLAN — same as GL-iNet's WAN port
dhclient wan0

# --- NAT (replaces GL-iNet's built-in NAT) --------------------------------
nft add table inet nat
nft add chain inet nat postrouting '{ type nat hook postrouting priority 100; }'
nft add rule inet nat postrouting oifname "wan0" masquerade

# --- DHCP + static leases (replaces GL-iNet's dhcp config) ----------------
# Static leases per docs/ip-address-map.md. Replace every REPLACE_WITH_MAC_nn with
# that device's real MAC address before applying — same requirement as the GL-iNet
# configs in ../gl-inet/.
cat > /etc/dnsmasq.d/theatre2.conf <<EOF
interface=lan0,lan1
dhcp-range=192.168.3.100,192.168.3.149,12h
dhcp-host=REPLACE_WITH_MAC_01,192.168.3.20   # birddog-play
dhcp-host=REPLACE_WITH_MAC_02,192.168.3.2    # atem-mini-extreme-iso
dhcp-host=REPLACE_WITH_MAC_03,192.168.3.5    # powerpoint-main
dhcp-host=REPLACE_WITH_MAC_04,192.168.3.6    # powerpoint-backup
dhcp-host=REPLACE_WITH_MAC_05,192.168.3.7    # vt-main
dhcp-host=REPLACE_WITH_MAC_06,192.168.3.8    # vt-backup
dhcp-host=REPLACE_WITH_MAC_07,192.168.3.10   # control-laptop
EOF
systemctl restart dnsmasq

# --- Tailscale — identical to the GL-iNet case, see ../tailscale-up-all-devices.sh
# tailscale up --advertise-routes=192.168.3.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-2-router
