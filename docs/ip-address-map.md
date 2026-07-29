# IP address map

Authoritative, fully-instantiated device inventory for the whole network — every
physical and virtual device, with its real IP. This is the source of truth; other docs
reference this file rather than repeating addresses.

## Uplink VLANs (Cloud Gateway transit networks — WAN side of each theatre's GL-iNet)

These transit subnets are a proposal — tags and ranges can be changed freely before
deployment. They exist purely so each of the 4 physical VLAN groups has a working transit
subnet; GL-iNet WAN ports don't need a predictable static address, DHCP is fine, since
Tailscale rides over whatever address they get.

| VLAN | 802.1Q tag | Subnet | Cloud Gateway address | Serves |
|---|---|---|---|---|
| Uplink 1 | 101 | 10.10.1.0/24 | 10.10.1.1 | Theatre 1–3 GL-iNet WAN ports |
| Uplink 2 | 102 | 10.10.2.0/24 | 10.10.2.1 | Theatre 4–6 GL-iNet WAN ports |
| Uplink 3 | 103 | 10.10.3.0/24 | 10.10.3.1 | Theatre 7–9 GL-iNet WAN ports |
| Uplink 4 | 104 | 10.10.4.0/24 | 10.10.4.1 | Theatre 10–12 GL-iNet WAN ports |

## Mothership LAN — 192.168.1.0/24

| Device | IP | Notes |
|---|---|---|
| Cloud Gateway (LAN gateway) | 192.168.1.1 | |
| Unraid server (host management IP) | 192.168.1.2 | Tailscale subnet router container shares this IP (host networking) |
| BirdDog Central | 192.168.1.12 | Windows VM — the design's only VM (the mothership VMix instance VM at `.11` was removed, see `docs/open-questions.md` #10; `.11` is left unassigned) |
| Nextcloud | 192.168.1.13 | Docker container, macvlan |
| Restreamer | 192.168.1.14 | Docker container, macvlan |
| NDI Discovery Server | 192.168.1.15 | Docker container, macvlan, port 5959 |
| DERP server | 192.168.1.16 | Docker container, macvlan, port 443 + STUN 3478/udp — see [`docs/tailscale.md`](tailscale.md) |
| ATEM ISO Ingest | 192.168.1.17 | Docker container, macvlan — pulls all 12 theatres' ATEM ISO recordings via FTP, see [`docs/atem-iso-ingest.md`](atem-iso-ingest.md) |
| VMix Record Ingest | 192.168.1.18 | Docker container, macvlan — pulls all 4 VMix PCs' recordings via SMB, see [`docs/vmix-record-ingest.md`](vmix-record-ingest.md) |
| UniFi Controller | 192.168.1.19 | Docker container, macvlan, port 8443 (UI) + 8080 (device inform) — self-hosted UniFi Network Application, independent of cloud.ui.com |
| GLKVM-Cloud (`rttys`) | 192.168.1.20 | Docker container, macvlan, port 443 (UI) + 5912 (device) + 10443 (WebSocket) — self-hosted remote administration for the 14 GL-iNet routers, see [`docs/glkvm-cloud.md`](glkvm-cloud.md) |
| ATEM Overseer | 192.168.1.21 | Docker container, macvlan — fleet monitoring/tally dashboard for all 12 theatres' ATEMs, receives each theatre's monitoring stream (see [`docs/bandwidth-analysis.md`](bandwidth-analysis.md)) |
| GLKVM-Cloud (`coturn`) | 192.168.1.22 | Docker container, macvlan, port 3478 tcp+udp — TURN relay for the above |
| ATEM Fleet Admin | 192.168.1.23 | Docker container, macvlan — bulk ATEM provisioning (model-aware config forms → live network apply via `atem-connection`, or XML+media folder export) |
| Flock | 192.168.1.24 | Docker container, macvlan — BirdDog Play fleet manager (LAN discovery, tag-based grouping, BirdUI-parity settings, batch edits); receives each theatre's BirdDog Play preview stream, see [`docs/bandwidth-analysis.md`](bandwidth-analysis.md) |
| Ready Room PC 1 | 192.168.1.30 | |
| Ready Room PC 2 | 192.168.1.31 | |
| Ready Room PC 3 | 192.168.1.32 | |
| Ready Room PC 4 | 192.168.1.33 | |

## Theatres 1–12

Same 8-device pattern in every theatre; only the subnet octet (X) changes. GL-iNet A-1300
LAN 1 goes directly to the ATEM Mini Extreme ISO, LAN 2 feeds the Netgear switch carrying
the rest (including BirdDog Play) — see [`docs/topology.md`](topology.md) for the physical
wiring.

### Theatre 1 — 192.168.2.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.2.1 |
| BirdDog Play | 192.168.2.20 |
| ATEM Mini Extreme ISO | 192.168.2.2 |
| PowerPoint Main | 192.168.2.5 |
| PowerPoint Backup | 192.168.2.6 |
| VT Main | 192.168.2.7 |
| VT Backup | 192.168.2.8 |
| Control laptop | 192.168.2.10 |

### Theatre 2 — 192.168.3.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.3.1 |
| BirdDog Play | 192.168.3.20 |
| ATEM Mini Extreme ISO | 192.168.3.2 |
| PowerPoint Main | 192.168.3.5 |
| PowerPoint Backup | 192.168.3.6 |
| VT Main | 192.168.3.7 |
| VT Backup | 192.168.3.8 |
| Control laptop | 192.168.3.10 |

### Theatre 3 — 192.168.4.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.4.1 |
| BirdDog Play | 192.168.4.20 |
| ATEM Mini Extreme ISO | 192.168.4.2 |
| PowerPoint Main | 192.168.4.5 |
| PowerPoint Backup | 192.168.4.6 |
| VT Main | 192.168.4.7 |
| VT Backup | 192.168.4.8 |
| Control laptop | 192.168.4.10 |

### Theatre 4 — 192.168.5.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.5.1 |
| BirdDog Play | 192.168.5.20 |
| ATEM Mini Extreme ISO | 192.168.5.2 |
| PowerPoint Main | 192.168.5.5 |
| PowerPoint Backup | 192.168.5.6 |
| VT Main | 192.168.5.7 |
| VT Backup | 192.168.5.8 |
| Control laptop | 192.168.5.10 |

### Theatre 5 — 192.168.6.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.6.1 |
| BirdDog Play | 192.168.6.20 |
| ATEM Mini Extreme ISO | 192.168.6.2 |
| PowerPoint Main | 192.168.6.5 |
| PowerPoint Backup | 192.168.6.6 |
| VT Main | 192.168.6.7 |
| VT Backup | 192.168.6.8 |
| Control laptop | 192.168.6.10 |

### Theatre 6 — 192.168.7.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.7.1 |
| BirdDog Play | 192.168.7.20 |
| ATEM Mini Extreme ISO | 192.168.7.2 |
| PowerPoint Main | 192.168.7.5 |
| PowerPoint Backup | 192.168.7.6 |
| VT Main | 192.168.7.7 |
| VT Backup | 192.168.7.8 |
| Control laptop | 192.168.7.10 |

### Theatre 7 — 192.168.8.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.8.1 |
| BirdDog Play | 192.168.8.20 |
| ATEM Mini Extreme ISO | 192.168.8.2 |
| PowerPoint Main | 192.168.8.5 |
| PowerPoint Backup | 192.168.8.6 |
| VT Main | 192.168.8.7 |
| VT Backup | 192.168.8.8 |
| Control laptop | 192.168.8.10 |

### Theatre 8 — 192.168.9.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.9.1 |
| BirdDog Play | 192.168.9.20 |
| ATEM Mini Extreme ISO | 192.168.9.2 |
| PowerPoint Main | 192.168.9.5 |
| PowerPoint Backup | 192.168.9.6 |
| VT Main | 192.168.9.7 |
| VT Backup | 192.168.9.8 |
| Control laptop | 192.168.9.10 |

### Theatre 9 — 192.168.10.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.10.1 |
| BirdDog Play | 192.168.10.20 |
| ATEM Mini Extreme ISO | 192.168.10.2 |
| PowerPoint Main | 192.168.10.5 |
| PowerPoint Backup | 192.168.10.6 |
| VT Main | 192.168.10.7 |
| VT Backup | 192.168.10.8 |
| Control laptop | 192.168.10.10 |

### Theatre 10 — 192.168.11.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.11.1 |
| BirdDog Play | 192.168.11.20 |
| ATEM Mini Extreme ISO | 192.168.11.2 |
| PowerPoint Main | 192.168.11.5 |
| PowerPoint Backup | 192.168.11.6 |
| VT Main | 192.168.11.7 |
| VT Backup | 192.168.11.8 |
| Control laptop | 192.168.11.10 |

### Theatre 11 — 192.168.12.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.12.1 |
| BirdDog Play | 192.168.12.20 |
| ATEM Mini Extreme ISO | 192.168.12.2 |
| PowerPoint Main | 192.168.12.5 |
| PowerPoint Backup | 192.168.12.6 |
| VT Main | 192.168.12.7 |
| VT Backup | 192.168.12.8 |
| Control laptop | 192.168.12.10 |

### Theatre 12 — 192.168.13.0/24

| Device | IP |
|---|---|
| GL-iNet A-1300 (LAN gateway) | 192.168.13.1 |
| BirdDog Play | 192.168.13.20 |
| ATEM Mini Extreme ISO | 192.168.13.2 |
| PowerPoint Main | 192.168.13.5 |
| PowerPoint Backup | 192.168.13.6 |
| VT Main | 192.168.13.7 |
| VT Backup | 192.168.13.8 |
| Control laptop | 192.168.13.10 |

## VMix nodes

Each has its own router — GL-iNet A-1300, same model as the theatre routers — and its
own Tailscale connection, not part of the theatre it physically sits next to.

### VMix Node 1 — 192.168.20.0/24 (off Theatre 1)

| Device | IP |
|---|---|
| Node 1 router (GL-iNet A-1300) | 192.168.20.1 |
| BirdDog P400 Camera 1 | 192.168.20.11 |
| BirdDog P400 Camera 2 | 192.168.20.12 |
| BirdDog P400 Camera 3 | 192.168.20.13 |
| BirdDog P400 Camera 4 | 192.168.20.14 |
| VMix PC 1 | 192.168.20.21 |
| VMix PC 2 | 192.168.20.22 |

### VMix Node 2 — 192.168.21.0/24 (off Theatre 4)

| Device | IP |
|---|---|
| Node 2 router (GL-iNet A-1300) | 192.168.21.1 |
| BirdDog P400 Camera 1 | 192.168.21.11 |
| BirdDog P400 Camera 2 | 192.168.21.12 |
| BirdDog P400 Camera 3 | 192.168.21.13 |
| BirdDog P400 Camera 4 | 192.168.21.14 |
| VMix PC 1 | 192.168.21.21 |
| VMix PC 2 | 192.168.21.22 |

## Edit suite — 192.168.22.0/24

Post-production subsystem at the mothership — dedicated 10GbE LAN, not part of the
Tailscale mesh (same room as the mothership, no reason to route it over the tailnet).
See [`docs/live-editing.md`](live-editing.md) for the full design.

| Device | IP | Notes |
|---|---|---|
| Edit suite NAS | 192.168.22.2 | Blackmagic Cloud Store or generic 10GbE NAS — see `docs/live-editing.md` Decision 1 |
| MacBook Pro — Editor 1 | 192.168.22.11 | 10GbE via Thunderbolt adapter/dock |
| MacBook Pro — Editor 2 | 192.168.22.12 | 10GbE via Thunderbolt adapter/dock |
| Mac mini — Project Server + Remote Render | 192.168.22.20 | Dedicated always-on machine, never an editor's own laptop — see `docs/live-editing.md` Decision 2 |

## Device count

- Mothership: 19 devices (1 gateway + 1 server host + 1 VM + 12 containers + 4 ready-room PCs)
- Theatres: 12 × 8 devices = 96
- VMix nodes: 2 × 7 devices = 14
- Edit suite: 4 devices (NAS + 2 MacBook Pros + Mac mini Project Server/Remote Render node), see [`docs/live-editing.md`](live-editing.md) Decision 2
- **Total: 133 devices** across the network (excluding the 4 uplink VLAN transit addresses, which aren't per-device).
