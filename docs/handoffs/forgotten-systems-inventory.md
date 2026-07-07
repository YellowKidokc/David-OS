# Forgotten Systems Inventory

Source note:

```text
C:\Users\David\.codex\attachments\16391f53-2f9f-4a18-a3f9-f1ecec122293\pasted-text.txt
```

This handoff records older systems that should be wrapped or mined before
anything is rebuilt.

## Verified On Disk

| System | Path | Status |
| --- | --- | --- |
| Legacy FIS | `D:\GitHub\file-intelligence-system` | Exists |
| BIL / PIL | `D:\BIL` | Exists |
| AHK Hub v2 | `D:\GitHub\ai-hub-v2` | Already imported separately |
| NLP Brain X drive | `X:\04_STATIONS` | Exists |
| Network brain share | `\\192.168.2.50\brain` | Exists |

## Promoted Now

The deterministic semantic addressing layer from legacy FIS is now promoted:

```text
D:\GitHub\TOP AI FIS\agents\labelers\semantic_addressing
```

It includes:

```text
semantic_scorer.py
hash_codec.py
meta_mapper.py
semantic_address_worker.py
```

## Do Not Rebuild

Use or wrap these existing pieces:

```text
legacy FIS semantic scorer
legacy FIS hash codec
legacy FIS meta classification enums
BIL clipboard signal weighting
AHK Hub v2 muscle-memory hotkeys
NLP Brain stations where already wired
```

## Integration Targets

| Old piece | New TOP AI FIS role |
| --- | --- |
| FIS semantic scorer | Post-file-intake semantic address worker |
| FIS hash codec | Stored semantic coordinate / searchable memory key |
| FIS meta mapper | CONTEXT / DOMAIN / FUNCTION / STATE classifier |
| BIL clipboard watcher | Feed `/clipboard/save` and clipboard priority scoring |
| BIL/PIL screenshot capture | Future image/file-drop event source |
| AHK Hub v2 overlay | Desktop hand / window control reference |
| NLP Brain stations | External worker pool behind hub jobs |

## Next Practical Steps

1. Add semantic address columns or JSON payload storage to the SQLite file label/index path.
2. Call `semantic_address_worker.py` after file intake/extraction.
3. Create `/semantic/score` or fold scoring into existing file-cache/classify endpoints.
4. Inspect BIL clipboard weighting and map it to hub clipboard priority.
5. Inspect NLP Brain `PLANT_BOOT.py` and decide whether it becomes a node health endpoint.

