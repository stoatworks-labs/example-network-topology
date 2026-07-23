#!/usr/bin/env python3
"""
ATEM ISO ingest — incremental FTP pull into Nextcloud's local external storage.

For each theatre's ATEM (built-in FTP server, reachable via Tailscale subnet routing),
lists the recording drive and pulls only the bytes appended since the last check,
using FTP's REST command (the same "resume from byte offset" mechanism curl/wget/lftp
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


def sync_theatre(theatre_num, state):
    ip = theatre_atem_ip(theatre_num)
    key_prefix = f"theatre-{theatre_num}"
    local_dir = os.path.join(LOCAL_BASE, f"Theatre{theatre_num}", "ISO")

    try:
        ftp = ftplib.FTP()
        ftp.connect(ip, timeout=15)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(FTP_REMOTE_DIR)
    except (ftplib.all_errors, OSError) as e:
        print(f"[theatre-{theatre_num}] FTP connect/login failed ({ip}): {e}", file=sys.stderr)
        return

    try:
        names = ftp.nlst()
    except ftplib.all_errors as e:
        print(f"[theatre-{theatre_num}] directory listing failed: {e}", file=sys.stderr)
        ftp.quit()
        return

    for name in names:
        if not name.lower().endswith(MEDIA_EXTENSIONS):
            continue

        try:
            remote_size = ftp.size(name)
        except ftplib.all_errors as e:
            print(f"[theatre-{theatre_num}] SIZE failed for {name}: {e}", file=sys.stderr)
            continue
        if remote_size is None:
            continue

        state_key = f"{key_prefix}/{name}"
        known_offset = state.get(state_key, 0)
        local_path = os.path.join(local_dir, name)

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
          f"poll every {POLL_INTERVAL_SECONDS}s, writing under {LOCAL_BASE}")
    while True:
        state = load_state()
        for theatre_num in THEATRES:
            sync_theatre(theatre_num, state)
        save_state(state)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
