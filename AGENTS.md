# AGENTS.md — bringing an LLM up to speed on this reference design

Orientation for an AI assistant (or a new human) picking this project up cold.

**Read §1 first. This is a public, deliberately anonymized repository.**

---

## 1. This repository is PUBLIC and anonymized — keep it that way

This is an **anonymized reference design**, published as a worked example of a complete
process: topology, bandwidth modelling, hardware selection with rationale, generated configs
and a deployment runbook.

It is a real design for a real event, with the identifying details generalized:

- **All domains are placeholders on the IANA-reserved `example.net`.** Substitute your own.
- **Nothing here names the event, client or venue.**
- Product names, prices and throughput figures **are real and cited**.

**Rules when working on this repo:**

- **Never introduce a real domain, client name, venue name, event name or public IP.** If a
  change needs a hostname, use `example.net`.
- **Never paste content in from a private working copy without checking it is anonymized.**
  That is the one way this repo's guarantee gets broken.
- **`export/html/` and `export/pdf/` are generated artifacts.** If you change a document, you
  must **regenerate** them. A scrubbed markdown file with a stale PDF beside it is the classic
  leak: the identifying string survives inside a compressed PDF stream where an ordinary text
  search of the repo finds nothing.

To check the PDFs properly, decompress their streams — `strings` alone gives a false
all-clear:

```python
import zlib, re, glob
for f in glob.glob("export/pdf/*.pdf"):
    raw = open(f,'rb').read(); text = b""
    for m in re.finditer(rb'stream\r?\n(.*?)endstream', raw, re.S):
        try: text += zlib.decompress(m.group(1))
        except Exception: text += m.group(1)
    # search text for anything identifying before publishing
```

## 2. What this is

A complete, fully-worked network design for a **12-theatre live event**: every theatre streams
its programme feed and syncs its files back to a central "mothership", all riding over a single
Tailscale mesh, with **no reliance on venue Wi-Fi or a conference-provided network**.

Per-theatre SRT/NDI streaming, rclone/Nextcloud file sync, and near-real-time ATEM ISO + VMix
record ingest back to the mothership.

**Documents and configuration only — there is no application code here.**

## 3. Layout

```
docs/topology.md                 The network design
docs/bandwidth-analysis.md       The bandwidth maths
docs/tailscale.md                DERP-avoidance reasoning, the self-hosted DERP server
docs/ip-address-map.md           Addressing
docs/server-specification.md     The central server
docs/streaming-flow.md, file-sync-flow.md, live-editing.md
docs/atem-iso-ingest.md, vmix-record-ingest.md
docs/deployment-runbook.md       On-site procedure
docs/troubleshooting.md
docs/open-questions.md           Genuinely undecided items
docs/gl-inet-rationale.md, birddog-play-rationale.md, glkvm-cloud.md
docs/topology-alternative-tailscale-switches.md   A considered alternative
config/     docker-compose, tailscale-acl.json, unifi/network-config.yaml, .env.template
export/     GENERATED html/ and pdf/ - regenerate, never hand-edit
diagrams/
```

## 4. Design points worth knowing

- **DERP avoidance is a design goal.** Tailscale's relays are a fallback; the design works to
  keep traffic direct. As insurance, a **self-hosted DERP server runs on the central server
  itself**, so even relayed traffic stays inside the event network.
- **Cross-theatre isolation is enforced in the Tailscale ACL** (`config/tailscale-acl.json`).
  Theatres cannot reach one another. That's deliberate; don't loosen it for convenience.
- `docs/open-questions.md` records what is genuinely undecided. The README also carries
  outstanding DNS-record tasks. Check both before treating a detail as settled.

## 5. Its value as a published example

The point of publishing this is that the **reasoning** is visible, not just the conclusion —
the bandwidth maths, the rationale documents, and the alternatives that were considered and
set aside. When extending it, keep that property: record *why*, and keep the rationale
documents in step with the topology.

## 6. Working on it

This is a design and configuration repo. Changes mean updating documents, diagrams and config
templates — then regenerating `export/`, and re-checking §1 before anything is pushed.
