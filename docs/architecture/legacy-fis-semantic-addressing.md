# Legacy FIS Semantic Addressing

MCP memory surfaced an older File Intelligence System that should not be
rebuilt from scratch. The important part is the deterministic semantic
addressing layer.

Source repo:

```text
D:\GitHub\file-intelligence-system
```

Promoted worker:

```text
D:\GitHub\TOP AI FIS\agents\labelers\semantic_addressing\semantic_address_worker.py
```

## What We Kept

```text
semantic_scorer.py
hash_codec.py
meta_mapper.py
```

These produce:

```text
10D vector
dominant variables
magnitude
state
20-bit coordinate hash
CONTEXT / DOMAIN / FUNCTION / STATE classification
```

## What We Did Not Bring Forward

```text
old watcher
old popup UI
old Postgres pipeline
```

The new hub owns:

```text
scope
folder permissions
job queue
review gates
SQLite ledger
sidecar policy
```

The old scorer is now a worker called by the hub, not a separate filesystem
controller.

## File Intake Integration

Target flow:

```text
file arrives
  -> Hub API creates file_intake job
  -> reader extracts text/metadata
  -> semantic_address_worker scores file
  -> result stored in SQLite
  -> .chi/.fmeta sidecars written only if folder policy allows
  -> React cockpit can search/filter by semantic address
```

## Do Not Rebuild

The following are now treated as existing assets:

```text
semantic scorer
hash codec
meta classification enums
```

Future work should wrap, test, and route these through the hub.

