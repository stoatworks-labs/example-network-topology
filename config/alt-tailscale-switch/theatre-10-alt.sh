#!/usr/bin/env bash
# Alternative to GL-iNet A-1300 for Theatre 10 — generic Linux box (mini-PC or
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

LAN_IP="192.168.11.1/24"

# --- Interfaces (adjust names to match the actual box's NICs) -------------
# Both LAN NICs bridged into one br-lan holding the gateway IP — same as GL-iNet's
# 'lan1 lan2' bridge. (Putting the same /24 address on two separate NICs instead
# gives two competing connected routes, and one port's devices become unreachable.)
ip link add br-lan type bridge
ip link set lan0 master br-lan   # ATEM Mini Extreme ISO, direct
ip link set lan1 master br-lan   # switch -> BirdDog Play, PowerPoint/VT laptops, control laptop
ip addr add "$LAN_IP" dev br-lan
ip link set lan0 up
ip link set lan1 up
ip link set br-lan up
# Routing between LAN, WAN and tailscale0 — required for NAT and for Tailscale subnet routing
sysctl -w net.ipv4.ip_forward=1
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
cat > /etc/dnsmasq.d/theatre10.conf <<EOF
interface=br-lan
dhcp-range=192.168.11.100,192.168.11.149,12h
dhcp-host=REPLACE_WITH_MAC_01,192.168.11.20   # birddog-play
dhcp-host=REPLACE_WITH_MAC_02,192.168.11.2    # atem-mini-extreme-iso
dhcp-host=REPLACE_WITH_MAC_03,192.168.11.5    # powerpoint-main
dhcp-host=REPLACE_WITH_MAC_04,192.168.11.6    # powerpoint-backup
dhcp-host=REPLACE_WITH_MAC_05,192.168.11.7    # vt-main
dhcp-host=REPLACE_WITH_MAC_06,192.168.11.8    # vt-backup
dhcp-host=REPLACE_WITH_MAC_07,192.168.11.10   # control-laptop
EOF
systemctl restart dnsmasq

# --- Tailscale — identical to the GL-iNet case, see ../tailscale-up-all-devices.sh
# tailscale up --advertise-routes=192.168.11.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-10-router
