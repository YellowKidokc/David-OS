# SQLite Hub Database

SQLite is the default database for the hub.

It stores:

- messages
- sources
- memory items and local embeddings
- jobs
- reviews
- ledger entries
- file intelligence records
- node heartbeats
- integration state later

## Default Path

By default the API uses:

```text
apps/api/.data/file-intelligence-hub.sqlite3
```

The path can be changed with:

```powershell
$env:FIHUB_DB_PATH="D:\TopOfMind\data\top-of-mind.sqlite3"
```

## LAN Setup

Run one hub API on the main machine and let other computers call it:

```powershell
cd D:\GitHub\Top-of-Mind-API\apps\api
fihub-api --host 0.0.0.0 --port 10000
```

Other machines should use:

```text
http://192.168.2.50:10000
```

Do not point multiple computers at the same SQLite file over a network share. Let them talk to the API instead.

## Backup

Stop the API or use SQLite backup tooling, then copy:

```text
file-intelligence-hub.sqlite3
file-intelligence-hub.sqlite3-wal
file-intelligence-hub.sqlite3-shm
```

Daily backup target examples:

- NAS folder
- Syncthing folder
- external drive
- Cloudflare/R2 export later

## When To Move Beyond SQLite

Stay on SQLite while this is a local/LAN command hub.

Consider Postgres later if:

- many machines write heavily at the same time
- multiple users need accounts/permissions
- vector search becomes large
- remote/cloud deployment becomes the normal path

The API layer should hide that change from AutoHotkey, the frontend, and integrations.

