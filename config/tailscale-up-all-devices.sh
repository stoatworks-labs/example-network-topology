#!/usr/bin/env bash
# Fully-instantiated `tailscale up` invocation for every subnet-router node on the
# tailnet — one line per real device, no __X__ placeholders. Generated to match
# docs/ip-address-map.md; if that map changes, regenerate by hand from
# tailscale-up-commands.sh (the templated reference version).
#
# This is a REFERENCE LIST, not a script to run in one go — each line runs on its
# own device. Routes still need approving in the Tailscale admin console (or via
# autoApprovers) before they take effect.

# ---- Theatre routers (×12, GL-iNet A-1300) ------------------------------
tailscale up --advertise-routes=192.168.2.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-1-router  # Theatre 1
tailscale up --advertise-routes=192.168.3.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-2-router  # Theatre 2
tailscale up --advertise-routes=192.168.4.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-3-router  # Theatre 3
tailscale up --advertise-routes=192.168.5.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-4-router  # Theatre 4
tailscale up --advertise-routes=192.168.6.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-5-router  # Theatre 5
tailscale up --advertise-routes=192.168.7.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-6-router  # Theatre 6
tailscale up --advertise-routes=192.168.8.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-7-router  # Theatre 7
tailscale up --advertise-routes=192.168.9.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-8-router  # Theatre 8
tailscale up --advertise-routes=192.168.10.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-9-router  # Theatre 9
tailscale up --advertise-routes=192.168.11.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-10-router  # Theatre 10
tailscale up --advertise-routes=192.168.12.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-11-router  # Theatre 11
tailscale up --advertise-routes=192.168.13.0/24 --accept-routes --advertise-tags=tag:theatre --hostname=theatre-12-router  # Theatre 12

# ---- VMix node routers (×2) ----------------------------------------------
tailscale up --advertise-routes=192.168.20.0/24 --accept-routes --advertise-tags=tag:vmix --hostname=vmix-node-1-router   # VMix Node 1, off Theatre 1
tailscale up --advertise-routes=192.168.21.0/24 --accept-routes --advertise-tags=tag:vmix --hostname=vmix-node-2-router   # VMix Node 2, off Theatre 4

# ---- Mothership subnet router (Docker container, host networking) -------
# Runs on the consolidated Unraid server (192.168.1.2), not the Cloud Gateway
# itself — see docs/topology.md and docs/open-questions.md.
tailscale up --advertise-routes=192.168.1.0/24 --advertise-tags=tag:mothership --hostname=mothership-server
