#!/usr/bin/env python3
"""
ATEM ISO ingest — incremental FTP pull into Nextcloud's local external storage.

For each theatre's ATEM (built-in FTP server, reachable via Tailscale subnet routing),
walks the recording drive's folders and, for the program recording plus the ISO inputs
in ATEM_ISO_INPUTS, pulls only the bytes appended since the last check, using FTP's REST
command (the same "resume from byte offset" mechanism curl/wget/lftp
use for resumable downloads). Writes directly into the folder Nextcloud has mounted as
External Storage (Local) — see setup-nextcloud-external-storage.sh — so there's no
separate upload step and no need to chunk/slice the video file at all.

See ../../docs/atem-iso-ingest.md for the full design rationale, including why plain
rsync can't be used here (the ATEM only speaks FTP) and why a naive whole-file re-sync
doesn't survive the bandwidth math for a multi-hour recording.

Run as a long-lived process (e.g. the entrypoint of a Docker container on the Unraid
box) — it loops internally rather than expecting to be invoked fresh each cycle.
"""

import ftplib
import json
import os
import posixpath
import re
import sys
import time

# ---- Configuration (override via environment variables) -------------------

THEATRES = range(1, 13)  # Theatre 1..12
FTP_USER = os.environ.get("ATEM_FTP_USER", "REPLACE_ME")  # confirm actual default creds on a real unit
FTP_PASS = os.environ.get("ATEM_FTP_PASS", "REPLACE_ME")
FTP_REMOTE_DIR = os.environ.get("ATEM_FTP_REMOTE_DIR", "/")  # confirm actual path on a real unit
LOCAL_BASE = os.environ.get("ATEM_ISO_LOCAL_BASE", "/mnt/user/nextcloud-external")
STATE_FILE = os.environ.get("ATEM_ISO_STATE_FILE", "/mnt/user/appdata/atem-iso-ingest/state.json")
POLL_INTERVAL_SECONDS = int(os.environ.get("ATEM_ISO_POLL_INTERVAL", "90"))
MEDIA_EXTENSIONS = (".mp4", ".mov")
MAX_DEPTH = 3  # a recording is <root>/<recording>/Video ISO Files/<file>

# Which ISO inputs to pull live. The ATEM always records every input to its own SSD (ISO
# recording is all-or-nothing); this only chooses which of those files cross the network.
# Every theatre is built to the same input map (docs/atem-iso-ingest.md, "Common theatre
# input map"), so one setting covers all 12. Empty = program recording only. The program
# file is always pulled. Everything not pulled stays on the SSD for the physical offload.
def parse_inputs(value):
    return {int(n) for n in value.split(",") if n.strip()}


ISO_INPUTS = parse_inputs(os.environ.get("ATEM_ISO_INPUTS", "1"))


def inputs_for(theatre_num):
    """ATEM_ISO_INPUTS_T<n> (e.g. ATEM_ISO_INPUTS_T3="1,2") overrides the fleet-wide
    setting for one theatre, so laptop inputs go live only where the router has room.
    Empty means no override (docker compose passes unset variables as ""); use "0" for
    program only."""
    override = os.environ.get(f"ATEM_ISO_INPUTS_T{theatre_num}", "").strip()
    return parse_inputs(override) if override else ISO_INPUTS
# How an ISO file names its input. "CAM 1" is Blackmagic's naming as far as we know;
# confirm against a real unit (docs/open-questions.md #21) and override if it differs.
ISO_INPUT_RE = re.compile(os.environ.get("ATEM_ISO_INPUT_PATTERN", r"\bCAM\s*(\d+)\b"), re.I)


def wanted(path, inputs=None):
    """Program recordings always; ISO files only for the chosen inputs."""
    inputs = ISO_INPUTS if inputs is None else inputs
    if not path.lower().endswith(MEDIA_EXTENSIONS):
        return False
    m = ISO_INPUT_RE.search(posixpath.basename(path))
    return m is None or int(m.group(1)) in inputs


def theatre_atem_ip(theatre_num):
    # Theatre 1 -> 192.168.2.2, Theatre 12 -> 192.168.13.2
    x = theatre_num + 1
    return f"192.168.{x}.2"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)


def pull_new_bytes(ftp, remote_name, remote_size, local_path, known_offset):
    """Append only the bytes from known_offset..remote_size to local_path."""
    if remote_size <= known_offset:
        return known_offset  # nothing new (or the file shrank/reset - don't touch it)

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "ab") as out:
        if out.tell() != known_offset:
            # Local mirror doesn't match our recorded offset (e.g. state file lost) —
            # trust the local file's actual size instead of the state file.
            known_offset = out.tell()

        def write_chunk(data):
            out.write(data)

        ftp.voidcmd("TYPE I")
        ftp.retrbinary(f"RETR {remote_name}", write_chunk, rest=known_offset)

    return os.path.getsize(local_path)


def walk(ftp, top, depth=0):
    """Yield file paths under top. Uses MLSD where the server has it, else NLST + a CWD
    probe to tell directories from files (the ATEM's FTP command set is unconfirmed)."""
    try:
        entries = [(posixpath.join(top, n), f.get("type") == "dir")
                   for n, f in ftp.mlsd(top, facts=["type"]) if n not in (".", "..")]
    except ftplib.error_perm:
        entries = []
        for n in ftp.nlst(top):
            path = n if n.startswith("/") else posixpath.join(top, posixpath.basename(n))
            try:
                ftp.cwd(path)
                ftp.cwd(top)
                entries.append((path, True))
            except ftplib.error_perm:
                entries.append((path, False))
    for path, is_dir in entries:
        if is_dir:
            if depth < MAX_DEPTH:
                yield from walk(ftp, path, depth + 1)
        else:
            yield path


def sync_theatre(theatre_num, state):
    ip = theatre_atem_ip(theatre_num)
    key_prefix = f"theatre-{theatre_num}"
    local_dir = os.path.join(LOCAL_BASE, f"Theatre{theatre_num}", "ISO")

    try:
        ftp = ftplib.FTP()
        ftp.connect(ip, timeout=15)
        ftp.login(FTP_USER, FTP_PASS)
        # Binary mode before SIZE, not just before RETR: many FTP servers refuse SIZE (or
        # report a different size) in the default ASCII mode.
        ftp.voidcmd("TYPE I")
        ftp.cwd(FTP_REMOTE_DIR)
    except (ftplib.all_errors, OSError) as e:
        print(f"[theatre-{theatre_num}] FTP connect/login failed ({ip}): {e}", file=sys.stderr)
        return

    # Blackmagic recordings are a folder per recording ("Video ISO Files/", "Audio Source
    # Files/" .wav, a .drp project), so walk the tree rather than listing one directory.
    try:
        inputs = inputs_for(theatre_num)
        names = [p for p in walk(ftp, FTP_REMOTE_DIR) if wanted(p, inputs)]
    except ftplib.all_errors as e:
        print(f"[theatre-{theatre_num}] directory listing failed: {e}", file=sys.stderr)
        ftp.quit()
        return

    for name in names:

        try:
            remote_size = ftp.size(name)
        except ftplib.all_errors as e:
            print(f"[theatre-{theatre_num}] SIZE failed for {name}: {e}", file=sys.stderr)
            continue
        if remote_size is None:
            continue

        state_key = f"{key_prefix}/{name}"
        known_offset = state.get(state_key, 0)
        local_path = os.path.join(local_dir, posixpath.relpath(name, FTP_REMOTE_DIR))

        if remote_size <= known_offset:
            continue

        try:
            new_offset = pull_new_bytes(ftp, name, remote_size, local_path, known_offset)
            state[state_key] = new_offset
            print(f"[theatre-{theatre_num}] {name}: {known_offset} -> {new_offset} bytes")
        except ftplib.all_errors as e:
            print(f"[theatre-{theatre_num}] pull failed for {name}: {e}", file=sys.stderr)

    ftp.quit()


def main():
    print(f"ATEM ISO ingest starting — {len(list(THEATRES))} theatres, "
          f"ISO inputs {sorted(ISO_INPUTS) or 'none'} + program, "
          f"poll every {POLL_INTERVAL_SECONDS}s, writing under {LOCAL_BASE}")
    while True:
        state = load_state()
        for theatre_num in THEATRES:
            sync_theatre(theatre_num, state)
        save_state(state)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
