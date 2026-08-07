# Montage Local Footage Runbook

## Purpose

Run routine documentary editing on owner-controlled compute instead of paying an editor agent to repeatedly inspect and click a browser UI.

Montage remains the project/control layer. `LocalFootageTool` is the deterministic FFmpeg executor. Faster-Whisper is optional local transcription. SynthCut is a replaceable adapter and never becomes canonical project storage.

## Requirements

- Python 3.11+
- `ffmpeg` and `ffprobe` on PATH
- optional: `faster-whisper` for local transcript generation
- enough local/external-drive space for source media, proxies, and outputs

## Start the worker

From a checked-out Montage repository:

```bash
python scripts/montage_local_service.py
```

Default endpoint:

```text
http://127.0.0.1:4788
```

Default workspace:

```text
~/.montage/local-media
```

Override the workspace when large footage should live on another drive:

```bash
python scripts/montage_local_service.py --workspace "E:/MONTAGE_MEDIA"
```

The service refuses non-loopback binding.

## Optional transcription

Install Faster-Whisper in the worker Python environment:

```bash
python -m pip install faster-whisper
```

The initial UI defaults to the `base` model with CPU `int8` execution. This is intentionally conservative for ordinary laptops. Larger models can be selected by a later routing policy when hardware permits.

## Studio workflow

1. Open the production Montage Studio.
2. Create a local-first project.
3. Open the Footage Factory.
4. Start the local worker on the computer that owns the footage.
5. Click **Connect**.
6. Choose footage. The browser streams it directly to the loopback worker; Vercel does not receive the media.
7. Transcribe locally when Faster-Whisper is available.
8. Perform bounded cut/reframe/caption operations.
9. Review the generated Change Beads.
10. Verify output before treating it as a delivery candidate.

## Security properties

- worker binds to `127.0.0.1` only;
- browser origins are allowlisted;
- browser requests cannot provide arbitrary absolute filesystem paths;
- uploaded media is stored under one configured workspace root;
- source assets are immutable by editing contract;
- no publish endpoint exists;
- no API key is required for the deterministic local path;
- local tool cost reports `$0.00` paid credits.

## SynthCut boundary

`tools/synthcut_adapter.py` intentionally does not copy SynthCut source or invent its current MCP schemas. Before execution is enabled against an installed version, the adapter must discover that runtime's actual MCP tools and schemas, map an approved Montage operation to a supported tool, execute it locally, and write evidence back to Montage.

This keeps SynthCut replaceable and avoids turning an upstream editor into project truth.

## Recovery

Generated media files are evidence and are not deleted when an edit is rolled back. A rollback changes which artifact the Montage project considers active. This makes rejected edits recoverable and keeps the operation history auditable.

If the local worker fails:

1. stop issuing new edits;
2. preserve source and existing outputs;
3. restart the worker;
4. reconnect from Studio;
5. inspect the last accepted Change Bead;
6. retry only the failed bounded operation.
