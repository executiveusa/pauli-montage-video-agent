# OneDrive Footage

Use this skill when an agent needs to discover or import documentary footage from
the owner's OneDrive without risking the remote masters.

## Safety contract

- OneDrive is a **read-only source**.
- Authentication uses Microsoft device-code login.
- Ask Microsoft for delegated `Files.Read` only. `offline_access` is allowed for
  refresh tokens. Reject any `ReadWrite` scope.
- Never request the user's Microsoft password or a client secret.
- Never delete, rename, move, replace, or upload a OneDrive item.
- Download into a bounded local workspace under `source/`.
- Treat downloaded source copies as immutable.
- Create edits only from derivatives such as `proxies/`, `selects/`, or exports.
- Preserve the OneDrive item ID, timestamps, size, file facets, and a local
  SHA-256 in a sidecar source manifest.

## Required setup

Create an owner-controlled Microsoft Entra app registration configured as a
public client that supports device authorization. Set:

```bash
export ONEDRIVE_CLIENT_ID="<public-client-id>"
export ONEDRIVE_TENANT="consumers"
```

Use `common` instead of `consumers` only when the owner intentionally wants both
personal Microsoft accounts and organizational accounts.

No client secret belongs in this flow.

## Connect

```bash
python scripts/onedrive_footage.py login
```

The CLI prints Microsoft's verification URL and a short user code. The human
opens that Microsoft page, enters the code, and signs in directly with
Microsoft. Tokens are cached outside the repository under the user's home
directory with restrictive file permissions where the OS supports them.

Check without exposing tokens:

```bash
python scripts/onedrive_footage.py status
```

Disconnect removes only the local token cache:

```bash
python scripts/onedrive_footage.py logout
```

## Discover footage

Browse:

```bash
python scripts/onedrive_footage.py list --media-only
python scripts/onedrive_footage.py list --item-id "<folder-item-id>" --media-only
```

Search metadata:

```bash
python scripts/onedrive_footage.py search "Culture Shock"
python scripts/onedrive_footage.py search "Montenegro"
python scripts/onedrive_footage.py search "Fats"
```

Do not rely on names alone. Before editorial use, collect the returned DriveItem
metadata and then analyze the downloaded proxy with ffprobe, transcription, and
visual scene indexing.

## Import safely

Download a protected local source copy:

```bash
python scripts/onedrive_footage.py download "<item-id>" \
  --workspace "/path/to/culture-shock"
```

Create an editable 720p proxy through the existing immutable-source FFmpeg tool:

```bash
python scripts/onedrive_footage.py import-proxy "<item-id>" \
  --workspace "/path/to/culture-shock" \
  --height 720
```

The operation creates:

```text
workspace/
  source/       # protected working copies + .source.json provenance
  proxies/      # editable derivatives
```

## Edit with YAPPY-CLIPZ

Feed the proxy path into `LocalFootageTool` for deterministic probe, cut,
transcription, captions, overlays, or vertical reframing. Never use the OneDrive
master as an output path.

## Edit with CLI-Anything Shotcut

CLI-Anything's Shotcut harness should receive the **proxy**, never the remote
master. Once `cli-anything-shotcut` and its Shotcut/MLT prerequisites are
installed, create a Shotcut project and import the local proxy using that
harness. Keep rendered outputs in a derivative/output directory.

The responsibility split is:

```text
OneDrive / Microsoft Graph
        ↓ read only
protected local source copy
        ↓
editable proxy
        ├─ YAPPY-CLIPZ LocalFootageTool
        └─ CLI-Anything Shotcut
        ↓
selects / rough cuts / exports
```

## Proof before claiming success

For every imported asset report:

- OneDrive item ID
- OneDrive filename
- remote size and timestamps
- local source path
- local SHA-256
- proxy path
- ffprobe duration/resolution once probed
- `source_immutable=true`
- `remote_write_enabled=false`

Do not claim that a clip is usable footage merely because a OneDrive folder or
filename exists. Verify the actual media object.
