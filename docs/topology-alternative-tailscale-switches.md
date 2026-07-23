# Alternative: plain switches + Tailscale on generic Linux, no GL-iNet routers

Same theatre topology (isolated `/24` per theatre, subnet routing, Tailscale ACLs doing
cross-theatre isolation) — different hardware. Instead of a GL-iNet A-1300 doing
router+NAT+DHCP+Tailscale in one appliance, use a plain unmanaged switch for LAN fanout
plus a small generic Linux box (mini-PC/NUC, or the theatre's existing control laptop)
running Tailscale as a subnet router with NAT/DHCP built from standard Linux tools
(nftables + dnsmasq). Config in [`config/alt-tailscale-switch/`](../config/alt-tailscale-switch/).

**Why a router-equivalent device is still required, not eliminated:** the ATEM and
BirdDog Play are closed appliances — they can't run the Tailscale client themselves. Some
device must still advertise the theatre's subnet on their behalf. "Pure Tailscale, no
router" only works if literally every device can run Tailscale; since two can't, this
alternative just moves the subnet-router role onto generic Linux instead of GL-iNet's
firmware. The `tailscale up` invocations themselves are identical either way — see
[`config/tailscale-up-all-devices.sh`](../config/tailscale-up-all-devices.sh) — Tailscale
doesn't care what hardware runs it.

## Comparison

| | GL-iNet A-1300 (chosen) | Generic Linux box + switch (alternative) |
|---|---|---|
| Setup effort | Config file, done (see [`config/gl-inet/`](../config/gl-inet/)) | Build + harden NAT/DHCP/Tailscale from scratch per box |
| Throughput confidence | Vendor datasheet, ~170 Mbps WireGuard | Unverified until benchmarked on whatever's chosen |
| Physical footprint | One compact unit per theatre | Separate PC + separate switch + 2 power supplies |
| Dedicated ATEM port | Built-in (2 LAN ports) | Needs a 2nd NIC/dongle to replicate |
| Wi-Fi | Built-in | Extra hardware if needed at all |
| Spares/swap-in | Re-flash identical UCI config | Re-provision a whole OS image |
| Maintenance | Vendor firmware updates | Ongoing OS patching, our responsibility |
| Flexibility/CPU headroom | Fixed, embedded-class | Higher, if it matters later |
| Unit cost at required throughput | ~$100-class travel router | Often more, once a real NIC + case + PSU are added |

## Recommendation: GL-iNet

This is 12 identical small router/switch appliances for a touring event that need to just
work — exactly the product category a travel router is built for. A generic Linux box
gives more flexibility and CPU headroom we don't need here, at the cost of more setup
work, more failure modes, no vendor throughput guarantee, and a bulkier kit per theatre.
The one real advantage of the alternative — no vendor lock-in — doesn't outweigh those
costs for this deployment. Keep GL-iNet as the primary; this alternative is documented for
completeness, not as an equally-weighted option.
