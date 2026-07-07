# Hub watcher/API bridge

`agents/watchers/hub_watcher.py` is the safe always-running TOP AI FIS watcher layer. It observes configured folders, normalizes file events, and calls the Hub API. It does **not** organize files directly and does not move, rename, delete, archive, convert, or write sidecars next to watched files.

The allowed local write area is one contained watcher folder per scan root:

```text
<scanned-root>/.tomfis-watch/
```

That watcher folder can hold manifests, extension summaries, offline queues, blocked-event notes, and "needs reader" requests. It should be treated as rebuildable scanner state, not user content. See `D:\GitHub\tom_fis_api\GUI\KIMI\WATCHER_FOLDER_CONTRACT.md` for the full GUI/API contract.

## Run

```bash
FIHUB_BASE_URL=http://127.0.0.1:10000 FIHUB_API_TOKEN=optional-token \
python agents/watchers/hub_watcher.py --config config/watchers/hub_watcher.example.json --watch
```

Useful flags:

- `--once`: scan once, compare with the startup snapshot, send any discovered delta, and exit.
- `--watch`: poll forever.
- `--offline`: never call the API; queue normalized events under `runtime/queue`.
- `--dry-run`: print API payloads instead of sending them.
- `--emit-existing`: emit current files as `created` events for demos or first-run bootstrap.

## Payload flow

For a created or modified file, the watcher sends:

1. `POST /files/cache` with the path, size, tags, and normalized event metadata.
2. `POST /jobs/file-events` for scanner/classify/review job creation.
3. `POST /semantic/score` only for safe text-like extensions and never for blocked files.
4. `POST /top-of-mind/messages` so operators can see watcher activity.

Deleted events skip file-cache indexing but still create job and visible notification payloads. If the API is offline, normalized events are appended as JSONL under `runtime/queue` and replayed on the next online run.

## Protection rules

The watcher marks events as `review_status=block` for protected folder profiles, program roots, protected directories, secret-like names, and unknown sensitive blobs. Blocked events still become visible API/job payloads, but they are not semantic-scored and are never directly acted on by the watcher.

## Fake-folder demo

```bash
mkdir -p runtime/demo/watch-inbox runtime/demo/program-root
printf 'hello' > runtime/demo/watch-inbox/demo.txt
python agents/watchers/hub_watcher.py --config config/watchers/hub_watcher.example.json --dry-run --once --emit-existing
```

The dry-run command prints `POST /files/cache`, `POST /jobs/file-events`, optional `POST /semantic/score`, and `POST /top-of-mind/messages` payloads. The watcher only scans and writes to `runtime/queue` when offline queuing is enabled.

## Deep reading rule

The watcher may inspect cheap filesystem facts such as extension, size, modified time, and folder location. If it needs deeper content understanding, it should send a job/API request instead of reading the document itself.

Examples:

- PDF/Office/Markdown content reading -> parser/classifier worker job.
- Unknown extension -> review or classifier job.
- Secret-like file -> blocked event plus review gate.
- Large folder -> aggregate extension/count summary, then folder summary worker.
