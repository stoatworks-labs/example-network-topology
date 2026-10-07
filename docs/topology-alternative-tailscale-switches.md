# Alternative: plain switches + Tailscale on generic Linux, no GL-iNet routers

Same theatre topology (isolated `/24` per theatre, subnet routing, Tailscale ACLs doing
cross-theatre isolation) — different hardware. Instead of a GL-iNet Slate AX doing
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

| | GL-iNet Slate AX (chosen) | Generic Linux box + switch (alternative) |
|---|---|---|
| Setup effort | Config file, done (see [`config/gl-inet/`](../config/gl-inet/)) | Build + harden NAT/DHCP/Tailscale from scratch per box |
| Throughput confidence | Vendor datasheet, ~550 Mbps — but that is kernel WireGuard; Tailscale's userspace `wireguard-go` is estimated at ~150-250 Mbps combined on the Slate AX, unbenchmarked (see [`docs/bandwidth-analysis.md`](bandwidth-analysis.md)). The previous choice, the A-1300, was dropped on 2026-10-06 for exactly this gap (170 Mbps kernel vs ~30-70 Mbps Tailscale est.) | Unverified until benchmarked on whatever's chosen (an x86 mini-PC will very likely beat any travel router under Tailscale) |
| Physical footprint | One compact unit per theatre | Separate PC + separate switch + 2 power supplies |
| Dedicated ATEM port | Built-in (2 LAN ports) | Needs a 2nd NIC/dongle to replicate |
| Wi-Fi | Built-in | Extra hardware if needed at all |
| Spares/swap-in | Re-flash identical UCI config | Re-provision a whole OS image |
| Maintenance | Vendor firmware updates | Ongoing OS patching, our responsibility |
| Flexibility/CPU headroom | Fixed, embedded-class | Higher, if it matters later |
| Unit cost at required throughput | ~$120 travel router (Slate AX list) | Often more, once a real NIC + case + PSU are added |

## Recommendation: GL-iNet

This is 12 identical small router/switch appliances for a touring event that need to just
work — exactly the product category a travel router is built for. A generic Linux box
gives more flexibility and CPU headroom we don't need here, at the cost of more setup
work, more failure modes, and a bulkier kit per theatre. (A travel router's
throughput "guarantee" is weaker than it looks under Tailscale — that is why the A-1300
was replaced by the Slate AX — and if the Slate AX benchmark in
[`docs/bandwidth-analysis.md`](bandwidth-analysis.md) comes back low too, CPU headroom stops
being something "we don't need" and this comparison should be revisited.)
The one real advantage of the alternative — no vendor lock-in — doesn't outweigh those
costs for this deployment. Keep GL-iNet as the primary; this alternative is documented for
completeness, not as an equally-weighted option.
