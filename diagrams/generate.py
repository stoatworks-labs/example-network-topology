#!/usr/bin/env python3
"""Regenerate every SVG in diagrams/.

    python3 diagrams/generate.py

Stdlib only. The topology diagram is built from docs/ip-address-map.md, which is the
authoritative device inventory, so the picture cannot drift from the address table:
change the table, re-run this script, then regenerate export/.

The other four diagrams are laid out by hand below. Their labels restate facts from
docs/streaming-flow.md, docs/file-sync-flow.md and docs/live-editing.md; keep them in
step when those docs change.
"""

import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "diagrams"

FONT = "Helvetica, Arial, sans-serif"

# One palette for every diagram. Each role has a strong colour (headers, lines) and a
# pale tint (card bodies), so cards stay legible in print and on dark-mode viewers that
# show the white canvas as-is.
INK = "#1a1d2b"
MUTED = "#5b6170"
FAINT = "#8a90a0"
RULE = "#d5d9e2"
ROLES = {
    "core":    ("#1e2235", "#eceef4"),  # mothership / gateway
    "server":  ("#3d4a63", "#eef0f5"),  # Unraid box
    "theatre": ("#24668f", "#eaf2f8"),
    "vmix":    ("#b03a48", "#fbedef"),
    "edit":    ("#64458f", "#f2eef8"),
    "amber":   ("#946200", "#fbf4e2"),
    "green":   ("#3b7a37", "#edf6eb"),
    "grey":    ("#6b7280", "#f3f4f6"),
}
LINK = {
    "srt": ROLES["theatre"][0],
    "ndi": ROLES["vmix"][0],
    "disc": ROLES["amber"][0],
    "sync": ROLES["green"][0],
    "edit": ROLES["edit"][0],
    "core": ROLES["core"][0],
    "grey": ROLES["grey"][0],
}


def text_w(s, size, bold=False):
    """Rough Helvetica advance width, good enough to size boxes."""
    return len(s) * size * (0.58 if bold else 0.53)


class Svg:
    def __init__(self, w, h, title, subtitle=None):
        self.w, self.h = w, h
        self.parts = []
        self.markers = set()
        self.title, self.subtitle = title, subtitle

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=13, fill=INK, anchor="start", weight=None,
             italic=False, family=None):
        attrs = [f'x="{x:.1f}"', f'y="{y:.1f}"', f'font-size="{size}"', f'fill="{fill}"']
        if anchor != "start":
            attrs.append(f'text-anchor="{anchor}"')
        if weight:
            attrs.append(f'font-weight="{weight}"')
        if italic:
            attrs.append('font-style="italic"')
        if family:
            attrs.append(f'font-family="{family}"')
        self.add(f'<text {" ".join(attrs)}>{escape(s)}</text>')

    def rect(self, x, y, w, h, fill, stroke=None, rx=8, sw=1.5, dash=None):
        s = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"'
        if stroke:
            s += f' stroke="{stroke}" stroke-width="{sw}"'
        if dash:
            s += f' stroke-dasharray="{dash}"'
        self.add(s + "/>")

    def card(self, x, y, w, h, role, title, sub=None, head=None):
        """Rounded card with a coloured header band; returns the y where body text starts."""
        strong, tint = ROLES[role]
        head = head or (46 if sub else 32)
        self.add(f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{tint}" '
                 f'stroke="{strong}" stroke-width="1.5"/>'
                 f'<path d="M{x},{y + head} V{y + 8} a8,8 0 0 1 8,-8 H{x + w - 8} '
                 f'a8,8 0 0 1 8,8 V{y + head} Z" fill="{strong}"/></g>')
        self.text(x + w / 2, y + 21, title, 15, "#ffffff", "middle", "bold")
        if sub:
            self.text(x + w / 2, y + 38, sub, 11.5, "#e6e9f0", "middle")
        return y + head

    def marker(self, colour):
        mid = "m" + colour.strip("#")
        if mid not in self.markers:
            self.markers.add(mid)
        return mid

    def line(self, pts, colour, width=2.2, dash=None, arrow_end=True, arrow_start=False,
             halo=False):
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        if halo:  # white underlay so this line visibly hops over any line it crosses
            self.add(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{width + 6}" '
                     f'stroke-linejoin="round"/>')
        s = f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" stroke-linejoin="round"'
        if dash:
            s += f' stroke-dasharray="{dash}"'
        if arrow_end:
            s += f' marker-end="url(#{self.marker(colour)})"'
        if arrow_start:
            s += f' marker-start="url(#{self.marker(colour)}s)"'
            self.markers.add(self.marker(colour) + "s")
        self.add(s + "/>")

    def label(self, x, y, s, colour, size=12, anchor="middle", weight="bold", italic=False):
        """Text on a white halo so it stays readable where it crosses a line."""
        w = text_w(s, size, weight == "bold") + 10
        x0 = {"middle": x - w / 2, "start": x - 5, "end": x - w + 5}[anchor]
        self.rect(x0, y - size + 1, w, size + 6, "#ffffff", rx=4)
        self.text(x, y + 1, s, size, colour, anchor, weight, italic)

    def legend(self, x, y, items, title="Legend"):
        self.text(x, y, title, 12.5, INK, weight="bold")
        for i, (colour, dash, desc) in enumerate(items):
            yy = y + 24 + i * 22
            self.line([(x, yy - 4), (x + 44, yy - 4)], colour, 2.4, dash)
            self.text(x + 56, yy, desc, 12.5, INK)

    def render(self):
        defs = []
        for mid in sorted(self.markers):
            start = mid.endswith("s")
            colour = "#" + (mid[1:-1] if start else mid[1:])
            path = "M10,0 L0,5 L10,10 z" if start else "M0,0 L10,5 L0,10 z"
            defs.append(f'<marker id="{mid}" viewBox="0 0 10 10" refX="{0 if start else 10}" refY="5" '
                        f'markerWidth="7" markerHeight="7" orient="auto">'
                        f'<path d="{path}" fill="{colour}"/></marker>')
        head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'width="{self.w}" height="{self.h}" font-family="{FONT}">',
                f"<title>{escape(self.title)}</title>",
                f"<defs>{''.join(defs)}</defs>",
                f'<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>']
        self.parts[:0] = []
        title = [f'<text x="{self.w / 2}" y="36" text-anchor="middle" font-size="22" '
                 f'font-weight="bold" fill="{INK}">{escape(self.title)}</text>']
        if self.subtitle:
            title.append(f'<text x="{self.w / 2}" y="58" text-anchor="middle" font-size="13" '
                         f'fill="{MUTED}">{escape(self.subtitle)}</text>')
        return "\n".join(head + title + self.parts + ["</svg>", ""])

    def save(self, name):
        (OUT / name).write_text(self.render())
        print("wrote", OUT / name)


# --------------------------------------------------------------------------------------
# docs/ip-address-map.md parser
# --------------------------------------------------------------------------------------

def md_tables(md):
    """Yield (heading, rows) for every markdown table, rows as lists of cell strings."""
    heading, rows, out = None, [], []
    for line in md.splitlines() + [""]:
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                rows.append(cells)
        elif rows:
            out.append((heading, rows[1:]))
            rows = []
    return out


def clean(s):
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    return s.replace("`", "").replace("**", "").strip()


def load_inventory():
    md = (ROOT / "docs" / "ip-address-map.md").read_text()
    inv = {"uplinks": [], "mothership": [], "theatres": [], "nodes": [], "edit": []}
    for heading, rows in md_tables(md):
        if heading.startswith("Uplink VLANs"):
            for r in rows:
                inv["uplinks"].append({"name": r[0], "tag": r[1], "subnet": r[2],
                                       "gw": r[3], "serves": r[4]})
        elif heading.startswith("Mothership LAN"):
            inv["mothership"] = [(clean(r[0]), r[1], clean(r[2]) if len(r) > 2 else "") for r in rows]
        elif m := re.match(r"Theatre (\d+) — (\S+)", heading):
            inv["theatres"].append({"n": int(m[1]), "subnet": m[2],
                                    "devices": [(clean(a), b) for a, b in rows]})
        elif m := re.match(r"VMix Node (\d+) — (\S+) \(off Theatre (\d+)\)", heading):
            inv["nodes"].append({"n": int(m[1]), "subnet": m[2], "near": int(m[3]),
                                 "devices": [(clean(r[0]), r[1]) for r in rows]})
        elif heading.startswith("Edit suite"):
            inv["edit"] = [(clean(r[0]), r[1], clean(r[2])) for r in rows]
    assert len(inv["theatres"]) == 12 and len(inv["nodes"]) == 2 and len(inv["uplinks"]) == 4
    gw = next(n for n, _ in inv["theatres"][0]["devices"] if n.startswith("GL-iNet"))
    inv["router"] = re.sub(r"\s*\(.*\)$", "", gw)  # "GL-iNet Slate AX (LAN gateway)" -> model
    return inv


def router_model():
    """Short router name for the hand-laid diagrams, e.g. "Slate AX"."""
    return load_inventory()["router"].replace("GL-iNet ", "")


def short(ip):
    """192.168.2.20 -> .2.20 for dense lists where the /16 is obvious."""
    return "." + ".".join(ip.split(".")[2:])


# --------------------------------------------------------------------------------------
# topology.svg
# --------------------------------------------------------------------------------------

def topology():
    inv = load_inventory()
    W = 1640
    s = Svg(W, 10, "Event Network — Full Device Inventory",
            "Every device and IP, generated from docs/ip-address-map.md · "
            "Tailscale runs only on the 14 GL-iNet routers and the mothership subnet router")

    def ts_badge(x, y):
        s.rect(x, y - 11, 62, 15, "#ffffff", ROLES["theatre"][0], rx=7, sw=1)
        s.text(x + 31, y, "Tailscale", 9.5, ROLES["theatre"][0], "middle", "bold")

    # ---- top band: server | gateway | ready room + edit suite ------------------------
    top = 84
    moth = {name: (ip, note) for name, ip, note in inv["mothership"]}
    server_rows = [(n, ip, note) for n, ip, note in inv["mothership"]
                   if note.startswith(("Docker container", "Windows VM"))]

    # Unraid server card
    sx, sw_ = 30, 560
    rows_per_col = (len(server_rows) + 1) // 2 + 1
    sh = 46 + 26 + rows_per_col * 19 + 62
    by = s.card(sx, top, sw_, sh, "server", "Consolidated services server — Unraid",
                f"one physical box · host {moth['Unraid server (host management IP)'][0]}")
    s.text(sx + 16, by + 22, "1 Windows VM + Docker containers (macvlan, own IPs)",
           11.5, MUTED, italic=True)
    col_w = (sw_ - 32) / 2
    items = [(n, ip, note.startswith("Windows VM")) for n, ip, note in server_rows]
    items.append(("Tailscale subnet router", "host net (.1.2)", False))
    for i, (n, ip, vm) in enumerate(items):
        c, r = divmod(i, rows_per_col)
        x = sx + 16 + c * (col_w + 0)
        y = by + 46 + r * 19
        label = n + (" (VM)" if vm else "")
        s.text(x, y, label, 12, ROLES["server"][0] if vm else INK, weight="bold" if vm else None)
        s.text(x + col_w - 14, y, short(ip) if ip[0].isdigit() else ip, 12, INK, "end", "bold")
    s.text(sx + 16, by + 46 + rows_per_col * 19 + 4,
           "IPs are 192.168.1.x · the subnet router uses the host's own address",
           11, MUTED, italic=True)
    s.text(sx + sw_ / 2, top + sh - 14,
           "2× 1GbE bonded (802.3ad LACP) to the gateway — aggregate headroom, not a faster single flow",
           11, MUTED, "middle", italic=True)

    # Gateway card
    gx, gw = 650, 340
    gh = 150
    s.card(gx, top + 30, gw, gh, "core", "Mothership — Cloud Gateway",
           f"192.168.1.0/24 · gateway {moth['Cloud Gateway (LAN gateway)'][0]}")
    gy = top + 30 + 46
    for i, line in enumerate(["Hardwired venue WAN (internet)",
                              "Terminates the 4 uplink VLANs",
                              "WAN forwards: DERP 443/tcp + 3478/udp,",
                              "GLKVM-Cloud 8443 · 10443 · 3479"]):
        s.text(gx + gw / 2, gy + 22 + i * 18, line, 12, INK, "middle")
    # WAN pill
    s.rect(gx + gw / 2 - 70, top - 16, 140, 26, "#ffffff", ROLES["core"][0], rx=13)
    s.text(gx + gw / 2, top + 1, "Internet / WAN", 12, ROLES["core"][0], "middle", "bold")
    s.line([(gx + gw / 2, top + 10), (gx + gw / 2, top + 30)], ROLES["core"][0], 2, arrow_end=False)

    # server <-> gateway bond
    s.line([(sx + sw_, top + 105), (gx, top + 105)], ROLES["core"][0], 2.2, arrow_end=False)
    s.line([(sx + sw_, top + 111), (gx, top + 111)], ROLES["core"][0], 2.2, arrow_end=False)
    s.text((sx + sw_ + gx) / 2, top + 132, "LACP", 10.5, ROLES["core"][0], "middle", "bold")
    s.text((sx + sw_ + gx) / 2, top + 146, "2×1GbE", 10.5, ROLES["core"][0], "middle", "bold")

    # Ready room + edit suite cards (right)
    rx, rw = 1050, 560
    ready = [(n, ip) for n, ip, _ in inv["mothership"] if n.startswith("Ready Room")]
    rh = 46 + 34
    s.card(rx, top, rw, rh, "green", "Ready room PCs (physical, mothership LAN)",
           "WebDAV mount straight onto Nextcloud — same LAN, no rclone")
    s.text(rx + rw / 2, top + 46 + 23, "   ·   ".join(f"PC {i + 1} {short(ip)}" for i, (_, ip) in enumerate(ready)),
           12.5, INK, "middle", "bold")
    s.line([(rx, top + 40), (gx + gw, top + 70)], ROLES["core"][0], 2, arrow_end=False)

    ey = top + rh + 18
    eh = 46 + 18 + len(inv["edit"]) * 19 + 12
    eb = s.card(rx, ey, rw, eh, "edit", "Edit suite — 192.168.22.0/24, own 10GbE LAN",
                "Not on the tailnet · routed to the mothership LAN only for the ingest dual-write")
    for i, (n, ip, _) in enumerate(inv["edit"]):
        y = eb + 22 + i * 19
        s.text(rx + 16, y, n, 12, INK)
        s.text(rx + rw - 16, y, ip, 12, INK, "end", "bold")
    s.line([(rx, ey + eh / 2), (gx + gw + 30, ey + eh / 2), (gx + gw + 30, top + 140),
            (gx + gw, top + 140)], ROLES["edit"][0], 2, arrow_end=False)
    s.label(gx + gw + 30, ey + eh / 2 - 26, "routed", ROLES["edit"][0], 10.5, weight=None, italic=True)

    # ---- uplink VLAN trunks ----------------------------------------------------------
    band_top = max(top + sh, ey + eh) + 40
    trunk_y = band_top
    ncol = 4
    margin, gap = 30, 26
    colw = (W - 2 * margin - (ncol - 1) * gap) / ncol
    gwx = gx + gw / 2
    s.line([(gwx, top + 30 + gh), (gwx, trunk_y)], ROLES["core"][0], 2.4, arrow_end=False)
    xs = [margin + i * (colw + gap) + 12 for i in range(ncol)]
    s.line([(xs[0], trunk_y), (xs[-1], trunk_y)], ROLES["core"][0], 2.4, arrow_end=False)

    pill_y = trunk_y + 22
    card_x_off = 34
    cw = colw - card_x_off
    theatres = {t["n"]: t for t in inv["theatres"]}
    nodes = {n["near"]: n for n in inv["nodes"]}
    col_bottom = []

    def theatre_card(x, y, t):
        devs = dict(t["devices"])
        router = next(ip for n, ip in t["devices"] if n.startswith("GL-iNet"))
        atem = next((n, ip) for n, ip in t["devices"] if n.startswith("ATEM"))
        switched = [(n, ip) for n, ip in t["devices"]
                    if not n.startswith("GL-iNet") and not n.startswith("ATEM")]
        h = 46 + 12 + 19 * (2 + 1 + len(switched)) + 6
        b = s.card(x, y, cw, h, "theatre", f"Theatre {t['n']}", t["subnet"])
        yy = b + 22
        s.text(x + 12, yy, inv["router"], 12, INK, weight="bold")
        ts_badge(x + 112, yy)
        s.text(x + cw - 12, yy, router, 12, INK, "end", "bold")
        yy += 19
        s.text(x + 12, yy, f"LAN1 → {atem[0]}", 12, INK)
        s.text(x + cw - 12, yy, atem[1], 12, INK, "end", "bold")
        yy += 19
        spare = 8 - 1 - len(switched)  # one switch port is the uplink to LAN2
        s.text(x + 12, yy, f"LAN2 → 8-port switch ({spare} port{'s' * (spare != 1)} spare):",
               11.5, MUTED, italic=True)
        for n, ip in switched:
            yy += 19
            s.text(x + 26, yy, n, 12, INK)
            s.text(x + cw - 12, yy, ip, 12, INK, "end", "bold")
        return h

    def node_card(x, y, nd):
        h = 46 + 12 + 19 * len(nd["devices"]) + 6
        b = s.card(x, y, cw, h, "vmix", f"VMix Node {nd['n']}",
                   f"{nd['subnet']} · sits beside Theatre {nd['near']}")
        yy = b + 22
        for n, ip in nd["devices"]:
            router = "router" in n.lower()
            name = inv["router"] if router else n.replace("BirdDog P400 Camera", "BirdDog P400 cam")
            s.text(x + 12, yy, name, 12, INK, weight="bold" if router else None)
            if router:
                ts_badge(x + 112, yy)
            s.text(x + cw - 12, yy, ip, 12, INK, "end", "bold")
            yy += 19
        return h

    for c in range(ncol):
        up = inv["uplinks"][c]
        x0 = margin + c * (colw + gap)
        rx_ = xs[c]
        s.line([(rx_, trunk_y), (rx_, pill_y - 8)], ROLES["core"][0], 2.4, arrow_end=False)
        s.rect(x0, pill_y - 8, colw, 40, ROLES["core"][1], ROLES["core"][0], rx=6)
        s.text(x0 + colw / 2, pill_y + 8, f"VLAN {up['tag']} — {up['subnet']}", 13, INK, "middle", "bold")
        s.text(x0 + colw / 2, pill_y + 25, f"venue-supplied 1 Gbps · {up['serves'].replace(' GL-iNet WAN ports', '')}",
               11, MUTED, "middle")
        y = pill_y + 50
        riser_top = pill_y + 32
        taps = []
        members = [theatres[n] for n in range(c * 3 + 1, c * 3 + 4)]
        for t in members:
            h = theatre_card(x0 + card_x_off, y, t)
            taps.append(y + 23)
            if t["n"] in nodes:
                pass
            y += h + 14
        for t in members:
            if t["n"] in nodes:
                h = node_card(x0 + card_x_off, y, nodes[t["n"]])
                taps.append(y + 23)
                y += h + 14
        s.line([(rx_, riser_top), (rx_, taps[-1])], ROLES["core"][0], 2.4, arrow_end=False)
        for ty in taps:
            s.line([(rx_, ty), (x0 + card_x_off, ty)], ROLES["core"][0], 2, arrow_end=False)
            s.text(rx_ + 6, ty - 5, "WAN", 8.5, MUTED, weight="bold")
        col_bottom.append(y)

    # Notes block fills the empty space under columns 3-4
    routers = len(inv["theatres"]) + len(inv["nodes"])
    total = (len(inv["mothership"]) + len(inv["edit"]) + sum(len(t["devices"]) for t in inv["theatres"])
             + sum(len(n["devices"]) for n in inv["nodes"]))
    model = inv["router"].replace("GL-iNet ", "")
    nx = margin + 2 * (colw + gap)
    ny = min(col_bottom[2], col_bottom[3]) + 6
    nw = 2 * colw + gap
    notes = [
        ("Isolation", "VLAN grouping is cabling only. Cross-theatre isolation is enforced by the Tailscale ACL"),
        ("", f"(config/tailscale-acl.json); each {model} also NATs its own theatre /24."),
        ("Overlay", f"Every {model} advertises its /24 as a Tailscale subnet router; the mothership's"),
        ("", "subnet router (container on the Unraid box) advertises 192.168.1.0/24."),
        ("Relay", "If a direct WireGuard path fails, traffic falls back to the self-hosted DERP"),
        ("", "server (.1.16) behind the gateway's WAN forward, so it never leaves the event."),
        ("VMix nodes", f"Each node's own {model} WAN joins its neighbour theatre's VLAN group; it is a"),
        ("", "separate tailnet node, not part of that theatre's LAN."),
        ("ATEM inputs", "Same map in every theatre: 1 camera, 2–3 laptops, 4–8 spare. Live pull ="),
        ("", "program + input 1 (+ 2/3 if headroom); the rest comes off the ATEM's SSD."),
        ("Counts", f"{routers}× {inv['router']} · {len(inv['theatres'])} theatres × "
                   f"{len(inv['theatres'][0]['devices'])} devices · {total} devices in total"),
        ("", "(see docs/ip-address-map.md for the per-device table)."),
    ]
    nh = 40 + len(notes) * 19
    s.rect(nx, ny, nw, nh, ROLES["grey"][1], RULE, rx=8)
    s.text(nx + 16, ny + 26, "How to read this", 13, INK, weight="bold")
    for i, (k, v) in enumerate(notes):
        y = ny + 48 + i * 19
        if k:
            s.text(nx + 16, y, k, 12, INK, weight="bold")
        s.text(nx + 104, y, v, 12, INK)
    s.h = int(max(max(col_bottom), ny + nh) + 20)
    s.save("topology.svg")


# --------------------------------------------------------------------------------------
# streaming-flow.svg
# --------------------------------------------------------------------------------------

def streaming():
    s = Svg(1400, 684, "SRT / NDI Streaming Flow",
            "Primary: SRT through Restreamer · Backup: NDI redistributed by BirdDog Central · "
            "Discovery: unicast NDI Discovery Server, because Tailscale does not carry mDNS")
    blue, red, amber = LINK["srt"], LINK["ndi"], LINK["disc"]

    # VMix nodes (left)
    for i, (node, ips) in enumerate([("VMix Node 1 PCs", "192.168.20.21 · .20.22"),
                                     ("VMix Node 2 PCs", "192.168.21.21 · .21.22")]):
        y = 120 + i * 170
        b = s.card(40, y, 300, 120, "vmix", node, ips)
        s.text(190, b + 24, "program out as SRT (primary)", 12, INK, "middle")
        s.text(190, b + 44, "and native NDI (backup)", 12, INK, "middle")
        s.text(190, b + 64, f"over the node's own {router_model()}", 11, MUTED, "middle", italic=True)

    # Mothership services (middle)
    s.rect(470, 92, 380, 520, ROLES["core"][1], RULE, rx=10, dash="6 4")
    s.text(660, 114, "Mothership — Unraid server", 12.5, MUTED, "middle", "bold")

    b = s.card(500, 130, 320, 96, "core", "Restreamer", "container · 192.168.1.14")
    s.text(660, b + 30, "SRT in → SRT fan-out ×12", 12.5, INK, "middle")

    b = s.card(500, 290, 320, 110, "core", "BirdDog Central", "Windows VM · 192.168.1.12")
    s.text(660, b + 24, "NDI redistributor: receives the", 12.5, INK, "middle")
    s.text(660, b + 43, "node's NDI program, re-sends it", 12.5, INK, "middle")

    b = s.card(500, 470, 320, 110, "amber", "NDI Discovery Server", "container · 192.168.1.15 : 5959/tcp")
    s.text(660, b + 24, "unicast registry — replaces mDNS,", 12.5, INK, "middle")
    s.text(660, b + 43, "which can't cross the tailnet", 12.5, INK, "middle")

    # BirdDog Play (right)
    b = s.card(1000, 130, 360, 450, "theatre", "BirdDog Play ×12", "one per theatre · 192.168.X.20")
    lines = [
        ("Primary — SRT from Restreamer", True),
        ("Unicast by IP: no discovery step,", False),
        ("routes cleanly over the tailnet.", False),
        ("", False),
        ("Backup — NDI from BirdDog Central", True),
        ("Found through the Discovery Server", False),
        ("(BirdUI → Network → Discovery", False),
        ("Server ON, enter 192.168.1.15).", False),
        ("", False),
        ("Full NDI 1080p50 ≈ 125 Mbps per", False),
        ("theatre: fine for one theatre (pause", False),
        ("its ATEM ingest), a capacity problem", False),
        ("if all 12 fall back at once.", False),
        ("See docs/bandwidth-analysis.md.", False),
    ]
    for i, (t, bold) in enumerate(lines):
        s.text(1180, b + 30 + i * 21, t, 12.5, INK, "middle", "bold" if bold else None)

    # Primary SRT
    s.line([(340, 165), (500, 165)], blue, 2.6)
    s.line([(340, 335), (420, 335), (420, 195), (500, 195)], blue, 2.6)
    s.label(420, 152, "SRT", blue)
    s.line([(820, 178), (1000, 178)], blue, 2.6)
    s.label(910, 166, "SRT ×12", blue)

    # Backup NDI: node -> Central -> Play
    s.line([(340, 205), (380, 205), (380, 330), (500, 330)], red, 2.4, "8 5", halo=True)
    s.line([(340, 375), (500, 375)], red, 2.4, "8 5")
    s.label(445, 320, "NDI", red)
    s.line([(820, 345), (1000, 345)], red, 2.4, "8 5")
    s.label(910, 333, "NDI ×12", red)

    # Discovery: clients connect to the server
    s.line([(190, 410), (190, 530), (500, 530)], amber, 1.8, "2 4")
    s.label(300, 518, "register (senders)", amber, 11, weight=None, italic=True)
    s.line([(660, 400), (660, 470)], amber, 1.8, "2 4")
    s.label(660, 440, "register + find", amber, 11, weight=None, italic=True)
    s.line([(1000, 545), (820, 545)], amber, 1.8, "2 4")
    s.label(910, 533, "find (×12)", amber, 11, weight=None, italic=True)

    s.legend(40, 560, [(blue, None, "Primary path — SRT"),
                       (red, "8 5", "Backup path — NDI (fallback only)"),
                       (amber, "2 4", "Discovery — TCP 5959 to the server")], "Legend")
    s.text(700, 640, "Everything crossing into or out of the dashed box rides the Tailscale mesh "
           f"(theatre and node {router_model()}s ↔ mothership subnet router).", 12, MUTED, "middle")
    s.text(700, 662, "Set the SRT payload size to 1128 bytes on VMix and Restreamer: the default 1316 "
           "does not fit Tailscale's 1280-byte MTU.", 12, MUTED, "middle")
    s.save("streaming-flow.svg")


# --------------------------------------------------------------------------------------
# file-sync-flow.svg
# --------------------------------------------------------------------------------------

def file_sync():
    s = Svg(1400, 470, "File Sync Flow",
            "Documents into Nextcloud: theatre laptops over the tailnet, ready-room PCs on the local LAN")
    blue, green, grey = LINK["srt"], LINK["sync"], LINK["grey"]

    b = s.card(40, 100, 380, 150, "theatre", "Theatre laptops", "×12 theatres · 4 per theatre = 48")
    for i, t in enumerate(["PowerPoint Main .5 · Backup .6", "VT Main .7 · Backup .8",
                           "each runs rclone sync of its", "theatre's folder"]):
        s.text(230, b + 24 + i * 19, t, 12.5, INK if i < 2 else MUTED, "middle")

    b = s.card(40, 300, 380, 110, "green", "Ready room PCs", "×4 · 192.168.1.30 – .33")
    s.text(230, b + 26, "live WebDAV mount — no rclone,", 12.5, INK, "middle")
    s.text(230, b + 45, "they share the mothership LAN", 12.5, INK, "middle")

    # tailnet hop
    s.rect(540, 140, 300, 70, ROLES["theatre"][1], blue, rx=35, dash="6 4")
    s.text(690, 170, "Tailscale mesh", 13, blue, "middle", "bold")
    s.text(690, 189, f"theatre {router_model()} → mothership subnet router", 11, MUTED, "middle")

    b = s.card(960, 170, 400, 170, "core", "Nextcloud", "container · 192.168.1.13")
    for i, t in enumerate(["/$TheatreName/ per theatre", "(one rclone target folder each)",
                           "+ ready-room WebDAV root", "+ ingest copies (External Storage)"]):
        s.text(1160, b + 26 + i * 20, t, 12.5, INK if i != 1 else MUTED, "middle")

    s.line([(420, 175), (540, 175)], blue, 2.6, arrow_end=False)
    s.line([(840, 175), (900, 175), (900, 220), (960, 220)], blue, 2.6)
    s.label(480, 163, "rclone", blue)
    s.line([(420, 355), (900, 355), (900, 280), (960, 280)], green, 2.6)
    s.label(660, 343, "WebDAV (local LAN)", green)

    s.line([(1160, 400), (1160, 340)], grey, 1.8, "4 4")
    s.text(1160, 420, "Also written here: ATEM ISO + VMix recordings —", 11.5, MUTED, "middle")
    s.text(1160, 437, "a separate pull mechanism, see atem-iso-ingest.md / vmix-record-ingest.md", 11.5, MUTED, "middle")
    s.save("file-sync-flow.svg")


# --------------------------------------------------------------------------------------
# live-editing-dataflow.svg
# --------------------------------------------------------------------------------------

def live_dataflow():
    s = Svg(1400, 615, "Live Editing — Data Flow",
            "One pull off each ATEM/VMix source, written twice — never a chained re-sync")
    blue, core, purple, grey = LINK["srt"], LINK["core"], LINK["edit"], LINK["grey"]

    # zones
    s.rect(20, 80, 330, 360, ROLES["theatre"][1], RULE, rx=10, dash="6 4")
    s.text(185, 102, "Theatres + VMix nodes (via tailnet)", 12, MUTED, "middle", "bold")
    s.rect(380, 80, 560, 360, ROLES["core"][1], RULE, rx=10, dash="6 4")
    s.text(660, 102, "Mothership LAN — 192.168.1.0/24", 12, MUTED, "middle", "bold")
    s.rect(970, 80, 410, 520, ROLES["edit"][1], RULE, rx=10, dash="6 4")
    s.text(1175, 102, "Edit suite LAN — 192.168.22.0/24, 10GbE", 12, MUTED, "middle", "bold")

    b = s.card(40, 120, 290, 120, "theatre", "ATEM Mini Extreme ISO ×12", "192.168.X.2 · FTP (G2: network share)")
    s.text(185, b + 24, "pulled live: program + input 1", 12, INK, "middle")
    s.text(185, b + 42, "(camera; + 2/3 laptops if headroom)", 11.5, MUTED, "middle")
    s.text(185, b + 60, "every input stays on its SSD", 11.5, MUTED, "middle")
    b = s.card(40, 280, 290, 120, "vmix", "VMix PCs ×4", "192.168.20/21.21–.22 · SMB share")
    s.text(185, b + 26, "recordings on local disk", 12, INK, "middle")
    s.text(185, b + 45, "(the master copy)", 12, MUTED, "middle")

    b = s.card(410, 190, 260, 140, "server", "Ingest containers", "Unraid")
    s.text(540, b + 24, "ATEM ISO Ingest — .1.17", 12.5, INK, "middle")
    s.text(540, b + 43, "VMix Record Ingest — .1.18", 12.5, INK, "middle")
    s.text(540, b + 66, "incremental copy of growing files", 11.5, MUTED, "middle", italic=True)

    b = s.card(720, 130, 200, 110, "core", "Nextcloud", "192.168.1.13")
    s.text(820, b + 26, "review copy", 12.5, INK, "middle")
    s.text(820, b + 45, "(External Storage)", 12, MUTED, "middle")

    b = s.card(1000, 130, 350, 110, "edit", "Edit Suite NAS", "192.168.22.2 · 10GbE")
    s.text(1175, b + 26, "editing copy, same pull", 12.5, INK, "middle")
    s.text(1175, b + 45, "(see live-editing.md Decision 1)", 12, MUTED, "middle")

    b = s.card(1000, 300, 350, 170, "edit", "Edit suite machines",
               "MacBooks via Thunderbolt adapters · Mac mini 10GbE option")
    for i, (n, ip) in enumerate([("MacBook Pro — Editor 1", ".22.11"), ("MacBook Pro — Editor 2", ".22.12"),
                                 ("Mac mini — Project Server", ".22.20"), ("   + Resolve Remote Render", "")]):
        s.text(1016, b + 26 + i * 21, n, 12.5, INK, weight=None)
        s.text(1334, b + 26 + i * 21, ip, 12.5, INK, "end", "bold")
    s.text(1175, b + 116, "shared Resolve project (resolve-configurator)", 11.5, MUTED, "middle", italic=True)

    # flows
    s.line([(330, 180), (370, 180), (370, 240), (410, 240)], blue, 2.4)
    s.line([(330, 340), (370, 340), (370, 280), (410, 280)], blue, 2.4)
    s.label(370, 214, "FTP pull", blue, 11)
    s.label(370, 312, "SMB pull", blue, 11)
    s.line([(670, 230), (695, 230), (695, 185), (720, 185)], core, 2.4)
    s.label(695, 160, "write 1", core, 11)
    s.line([(670, 290), (955, 290), (955, 215), (1000, 215)], purple, 2.4)
    s.label(820, 278, "write 2 (Unraid's 10GbE edit-LAN port)", purple, 11)
    s.line([(1175, 240), (1175, 300)], purple, 2.4, arrow_start=True)
    s.label(1175, 274, "10GbE", purple, 11)

    # DIT physical path
    b = s.card(1000, 500, 350, 80, "grey", "Physical media (DIT offload)", None)
    s.text(1175, b + 24, "ATEM SSDs (all ISOs not pulled live) walked to", 12, INK, "middle")
    s.text(1175, b + 42, "the edit suite · checksummed copy to the NAS", 12, INK, "middle")
    s.line([(1350, 540), (1368, 540), (1368, 200), (1350, 200)], grey, 1.8, "6 4")

    s.text(480, 480, "Why two writes, not Nextcloud → NAS:", 12.5, INK, "middle", "bold")
    for i, t in enumerate(["the edit suite never waits on Nextcloud's own files:scan,",
                           "and editors never read from the pool ingest is writing to.",
                           "ISOs run ~35–70 Mb/s each and can't be turned down,",
                           "so only program + camera go live; the second write",
                           "is not yet implemented in the ingest scripts."]):
        s.text(480, 502 + i * 19, t, 12, MUTED, "middle")
    s.save("live-editing-dataflow.svg")


# --------------------------------------------------------------------------------------
# live-editing-project-structure.svg
# --------------------------------------------------------------------------------------

def project_structure():
    s = Svg(1400, 680, "Live Editing — Project Structure & Smart-Bin Workflow",
            "resolve-configurator builds the project ahead of time, so the editor's job is only cutting")
    core, amber, green, purple = LINK["core"], LINK["disc"], LINK["sync"], LINK["edit"]

    # swimlanes
    s.rect(20, 80, 1360, 250, ROLES["amber"][1], RULE, rx=10)
    s.text(36, 104, "BEFORE THE EVENT — once", 12, amber, weight="bold")
    s.rect(20, 350, 1360, 230, ROLES["edit"][1], RULE, rx=10)
    s.text(36, 374, "DURING THE EVENT — per session, automatic", 12, purple, weight="bold")

    b = s.card(40, 130, 250, 150, "core", "Session CSV", None)
    for i, t in enumerate(["theatre, date, start time,", "presenter", "",
                           "same CSV nc-filedropbatch", "uses for presenter uploads"]):
        s.text(165, b + 26 + i * 19, t, 12, INK if i < 2 else MUTED, "middle")

    b = s.card(350, 120, 300, 180, "amber", "resolve-configurator", "Python, stdlib only · idempotent")
    for i, t in enumerate(["dry-run needs no Resolve install;", "applying needs Resolve Studio",
                           "", "builds everything the scripting", "API can create"]):
        s.text(500, b + 26 + i * 19, t, 12, INK, "middle")

    b = s.card(710, 120, 320, 180, "core", "Shell Resolve project", "on the Mac mini's Project Server")
    for i, t in enumerate(["bin per theatre / day", "empty timeline per session",
                           "(\"Start Time - Presenter\")", "backgrounds + title slides imported",
                           "project format settings applied"]):
        s.text(870, b + 26 + i * 19, t, 12, INK, "middle")

    b = s.card(1090, 120, 270, 180, "amber", "Smart-bin recipe", "smart-bins.md / .json")
    for i, t in enumerate(["per session: file path, date", "created, start TC in the",
                           "session window (path rule must", "match the NAS layout — open item)",
                           "the API can't create smart bins:", "applied by hand, once"]):
        s.text(1225, b + 26 + i * 19, t, 12, INK if i < 3 else MUTED, "middle")

    s.line([(290, 205), (350, 205)], core, 2.4)
    s.line([(650, 190), (710, 190)], core, 2.4)
    s.label(680, 176, "builds", core, 11)
    s.line([(650, 260), (680, 260), (680, 318), (1225, 318), (1225, 300)], amber, 2.2, "8 5")
    s.label(950, 322, "also writes", amber, 11)

    # during
    b = s.card(980, 400, 380, 150, "edit", "Footage lands on the NAS", "dual-write from the ingest pull")
    s.text(1170, b + 28, "files grow through the session", 12, INK, "middle")
    s.text(1170, b + 48, "(see the data-flow diagram)", 12, MUTED, "middle")

    b = s.card(520, 400, 380, 150, "green", "Smart bins auto-fill", "filter rule from the recipe")
    s.text(710, b + 28, "only that session's clips appear —", 12, INK, "middle")
    s.text(710, b + 48, "no manual sorting, no scrubbing", 12, INK, "middle")

    b = s.card(40, 400, 400, 150, "edit", "Editor's job", None)
    for i, t in enumerate(["1. open the session's timeline", "2. drag clips from its smart bin",
                           "3. top-and-tail", "4. export (optionally via Remote Render)"]):
        s.text(64, b + 26 + i * 22, t, 12.5, INK)

    s.line([(980, 475), (900, 475)], green, 2.4)
    s.line([(520, 475), (440, 475)], purple, 2.4)
    s.line([(870, 300), (870, 340), (400, 340), (400, 400)], core, 1.8, "2 4", halo=True)
    s.label(585, 344, "timelines and bins already exist, waiting for footage", core, 11, weight=None, italic=True)
    s.line([(1300, 300), (1300, 385), (800, 385), (800, 400)], amber, 2.2, "8 5")
    s.label(1050, 389, "applied by hand, once", amber, 11)

    s.legend(40, 590, [(core, None, "built automatically, before the event"),
                       (core, "2 4", "already exists, waiting for footage")], "")
    s.legend(520, 590, [(amber, "8 5", "manual one-time step from the recipe"),
                        (green, None, "automatic, during the event")], "")
    s.text(700, 668, "Full walkthrough: docs/live-editing.md (\"Workflow: from ATEM pull to finished edit\").",
           11.5, MUTED, "middle")
    s.save("live-editing-project-structure.svg")


if __name__ == "__main__":
    topology()
    streaming()
    file_sync()
    live_dataflow()
    project_structure()
