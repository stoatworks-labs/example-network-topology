# rclone mount (FUSE) + rsync --append needs both tools plus a FUSE device — none of
# that is in a plain base image, unlike ATEM ISO Ingest's pull-iso.py which only needs
# Python. See docs/vmix-record-ingest.md and mount-and-sync.sh for what this actually runs.
FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends rclone rsync fuse3 ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

ENTRYPOINT ["/app/mount-and-sync.sh"]
