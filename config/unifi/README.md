# UniFi Cloud Gateway config

Unlike GL-iNet (OpenWrt/UCI, flat text config files), UniFi's Cloud Gateway is managed
through the UniFi Network application (or its API) — there's no equivalent single file to
drop in. [`network-config.yaml`](network-config.yaml) is a structured reference: create
each network/firewall rule/port profile it describes in the UniFi Network UI
(Settings → Networks / Settings → Firewall & Security / Settings → Ports), in the order
listed. If you'd rather script it, the same fields map directly onto the UniFi Network
API (`/proxy/network/api/s/<site>/rest/networkconf`, `/rest/firewallrule`, etc.).

Everything here is **newly proposed** to support this build — none of it was specified
before this point — so treat it as a starting point to confirm or change, not a fixed
requirement. See [`docs/ip-address-map.md`](../../docs/ip-address-map.md) for how these
addresses fit into the rest of the network.

## What this covers

1. **4 uplink VLANs** — one per physical VLAN group (Theatres 1–3, 4–6, 7–9, 10–12),
   each a plain DHCP-served transit subnet for that group's GL-iNet WAN ports. The
   theatres' own `192.168.X.0/24` LANs stay entirely behind their GL-iNet's NAT and never
   touch these — only the WAN-facing side rides on them.
2. **Firewall baseline** — the 4 uplink VLANs can reach the internet (needed for
   Tailscale) but not each other and not the mothership's own `192.168.1.0/24` LAN. This
   is defense-in-depth on top of the Tailscale ACLs
   ([`config/tailscale-acl.json`](../tailscale-acl.json)) already doing the real
   cross-theatre isolation — it doesn't replace them.
3. **Port profiles** — one profile per uplink VLAN, applied to whichever switch ports
   feed each group's cabling run, plus a LAG profile for the Unraid server's bonded NICs
   (Settings → Ports → create Link Aggregation Group). Assuming this Cloud Gateway
   supports port aggregation (only UDM Pro/SE/Pro Max, UXG Enterprise, and EFG do) — if
   it turns out not to, drop an intermediate LACP-capable switch in between and bond
   through that instead (see `docs/open-questions.md`).
4. **Port forwards** for the self-hosted DERP server (Settings → Firewall & Security →
   Port Forwarding): WAN 443/tcp and 3478/udp → the DERP container on `192.168.1.16` — see
   [`docs/tailscale.md`](../../docs/tailscale.md).
5. **Self-hosted UniFi Controller** — a UniFi Network Application container on the
   consolidated services server (`192.168.1.19`, ports 8443/8080), reachable over the
   tailnet like everything else on that box. The Cloud Gateway ships with its own
   built-in controller and works standalone without this — adopting it into the
   self-hosted instance is optional, purely for a local management console independent
   of cloud.ui.com. No firewall/port-forward change needed for it; it's admin access
   only, not part of the traffic paths in `network-config.yaml`.
6. **Port forwards for self-hosted GLKVM-Cloud** (Settings → Firewall & Security → Port
   Forwarding): WAN `8443/tcp` → `192.168.1.20:443` (web UI), WAN `10443/tcp` →
   `192.168.1.20:10443` (WebSocket proxy), WAN `3479/tcp+udp` → `192.168.1.22:3478`
   (TURN). All three ports are remapped off GLKVM-Cloud's own documented port numbers
   because DERP already occupies WAN `443/tcp` and `3478/udp` — see
   [`docs/glkvm-cloud.md`](../../docs/glkvm-cloud.md) for the full reasoning and the
   open question about whether the app's `GLKVM_ACCESS_IP` setting accepts this remap
   cleanly.

## What this doesn't cover

The mothership's own `192.168.1.0/24` LAN (where the Unraid server, ready-room PCs, etc.
live) is assumed to already exist as the Cloud Gateway's default/main network — this
file only adds the 4 new uplink VLANs alongside it.
