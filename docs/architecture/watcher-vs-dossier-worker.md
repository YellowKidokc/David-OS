# Watcher vs Folder Dossier Worker

The watcher is not responsible for knowing everything about a folder.

The watcher is responsible for noticing change, recording evidence, and asking
the hub to schedule the right work.

## Boundary

```text
Watcher = tripwire + event recorder + API caller
Scanner = symptom detector
Dossier worker = deterministic folder rollup
Review gate = safety decision
Worker = approved action executor
```

Do not build a watcher that tries to compute every folder statistic itself.

## What The Watcher Does

For every watched root, the watcher should:

- notice created, modified, moved, deleted, and renamed paths,
- normalize the event,
- attach cheap facts: extension, size, parent folder, timestamp, source node,
- detect immediate danger markers such as `.git`, `package.json`, `.env`, `.key`,
- call the hub API,
- queue locally if the API is offline.

Watcher event shape:

```json
{
  "source_node_id": "desktop",
  "event_type": "created",
  "path": "D:/Downloads/example.pdf",
  "old_path": null,
  "extension": ".pdf",
  "size_bytes": 123456,
  "parent_path": "D:/Downloads",
  "observed_at": "2026-07-03T18:44:00-05:00",
  "cheap_labels": ["document"],
  "danger_markers": []
}
```

The watcher can increment event counters, but it should not try to maintain the
entire `.folder.fmeta` dossier alone.

## What The Dossier Worker Does

The folder dossier worker is the thing that writes the complete `.folder.fmeta`.

It is scheduled by the hub after watcher events or scan jobs.

It computes:

- folder identity,
- current path/name,
- name/path history,
- first seen / last seen,
- scan count,
- file count,
- directory count,
- total bytes,
- extension histogram,
- kind histogram,
- top domains,
- top classifications,
- semantic rollup,
- symptom counts,
- anomaly counts,
- program-root evidence,
- protection flags,
- action ledger totals,
- deterministic folder role,
- deterministic folder name recommendation.

The dossier worker reads from:

- SQLite file records,
- SQLite file events,
- SQLite jobs/action ledger,
- scanner reports,
- semantic score records,
- folder markers/sidecars where allowed.

## Write Order

```text
1. Watcher sees event.
2. Watcher posts event/cache payload to hub.
3. Hub records event in SQLite.
4. Hub schedules file classify/hash jobs if needed.
5. Hub schedules folder scan/dossier refresh for the parent folder.
6. Scanner detects symptoms.
7. Dossier worker computes `.folder.fmeta`.
8. Review gate enforces labels before any action job.
```

## Why This Matters

If the watcher tries to compute the whole folder dossier, it becomes fragile,
slow, and dangerous.

If the watcher only records events and triggers jobs, it can run all day on a
desktop, laptop, or Synology without getting heavy.

## Rule

```text
Watcher writes events.
Dossier worker writes folder biography.
SQLite is the enforcement source of truth.
.folder.fmeta is the portable snapshot.
```

