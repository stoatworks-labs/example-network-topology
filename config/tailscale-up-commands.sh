#!/usr/bin/env bash
# Per-role `tailscale up` invocations for the event network.
# Run the relevant block on each device. Routes must still be approved in the
# Tailscale admin console (or via autoApprovers) before they take effect.

# --- Theatre routers (×12, GL-iNet A-1300 / Slate Plus) -----------------
# X = subnet octet per the map in ../README.md, e.g. Theatre 1 -> 2, Theatre 12 -> 13
tailscale up --advertise-routes=192.168.X.0/24 --accept-routes --advertise-tags=tag:theatre

# --- VMix node routers (×2) ----------------------------------------------
tailscale up --advertise-routes=192.168.20.0/24 --accept-routes --advertise-tags=tag:vmix   # VMix Node 1, off Theatre 1
tailscale up --advertise-routes=192.168.21.0/24 --accept-routes --advertise-tags=tag:vmix   # VMix Node 2, off Theatre 4

# --- Mothership subnet router ---------------------------------------------
# Mothership router is a Ubiquiti Cloud Gateway, which can't run Tailscale
# natively without an unofficial container hack — run this instead as a Docker
# container (host networking) on the consolidated Unraid services server on
# 192.168.1.x, alongside Nextcloud/Restreamer/NDI Discovery Server (see
# ../docs/topology.md and ../docs/open-questions.md).
tailscale up --advertise-routes=192.168.1.0/24 --advertise-tags=tag:mothership
