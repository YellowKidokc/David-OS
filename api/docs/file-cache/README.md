# Desktop File Cache

The desktop file cache is a fast SQLite lookup layer for files on desktop-tier machines.

It is not the file itself. It is an index of what exists.

Stores:

- full path
- filename
- extension
- parent folder
- tier, such as `desktop`, `nas`, `sync`, or `archive`
- owner id, such as `david`, `codex`, or `shared`
- size
- modified timestamps
- tags
- metadata
- last seen time

API:

- `POST /files/cache`
- `GET /files/cache`
- `GET /files/cache/search?q=...`
- `GET /files/cache/by-path?path=...`

Use this for:

- fast file lookup from the frontend
- desktop/NAS file inventory
- "find my prompt/document/video" searches
- deciding which file action should run

Do not use it as the only source of truth for file existence. A worker should verify the file still exists before destructive operations.
