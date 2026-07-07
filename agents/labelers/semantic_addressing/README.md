# Semantic Addressing Worker

This folder promotes the useful deterministic part of the old FIS repo:

```text
D:\GitHub\file-intelligence-system\fis\nlp\semantic_scorer.py
D:\GitHub\file-intelligence-system\fis\nlp\hash_codec.py
D:\GitHub\file-intelligence-system\fis\nlp\meta_mapper.py
```

It does not promote the old watcher or Postgres pipeline.

## What It Produces

For a file, the worker produces:

```text
10D vector: G M E S T K R Q F C
dominant variables
magnitude
state
legacy coord hash
20-bit decodable coord hash
human score string
meta classification: CONTEXT / DOMAIN / FUNCTION / STATE
```

## Run

```powershell
python "D:\GitHub\TOP AI FIS\agents\labelers\semantic_addressing\semantic_address_worker.py" --path "D:\GitHub\TOP AI FIS\README.md"
```

The Hub API should eventually call this after file intake/extraction and store
the result in SQLite plus `.chi`/`.fmeta` sidecars where allowed.

