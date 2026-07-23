# File sync flow

## Theatre laptops → Nextcloud (rclone)

PowerPoint Main/Backup and VT Main/Backup laptops in each theatre run `rclone`, syncing
their theatre's folder (`/$TheatreName/`) up to the Nextcloud file server at the mothership.

```
Theatre laptop (PowerPoint/VT, Main/Backup) --rclone sync--> Nextcloud:/$TheatreName/
```

## Ready room → Nextcloud (WebDAV)

Ready room PCs at the mothership write directly to Nextcloud via a WebDAV mount — a live
local mount on the mothership LAN, not rclone, since there's no WAN hop involved.

```
Ready room PC --WebDAV mount--> Nextcloud (local to mothership LAN)
```

See [`diagrams/file-sync-flow.svg`](../diagrams/file-sync-flow.svg).

## The other file flows into the same Nextcloud

This doc covers only the *document* sync — theatre laptops and ready-room PCs. Two
recording pipelines write into the same Nextcloud by a completely different mechanism
(near-real-time incremental pulls, not rclone sync of finished files), and one of them
carries on to a second destination:

- [`docs/atem-iso-ingest.md`](atem-iso-ingest.md) — each theatre's ATEM ISO recordings,
  pulled over FTP
- [`docs/vmix-record-ingest.md`](vmix-record-ingest.md) — each VMix PC's recordings,
  pulled over SMB
- [`docs/live-editing.md`](live-editing.md) — the same pulls dual-write to the edit
  suite's NAS alongside Nextcloud
