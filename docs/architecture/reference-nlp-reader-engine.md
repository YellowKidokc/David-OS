# Reference, NLP, and Reader Engine

This is the last intelligence layer for TOP AI FIS.

The hub needs to answer three questions:

1. What kind of file/folder is this?
2. Can we read enough content to classify it?
3. Which reference/NLP engine gives the best result?

## Reader Ladder

Readers run from cheapest to most expensive.

```text
filename + path + extension
  -> magic bytes / signature
  -> lightweight metadata parser
  -> text extraction
  -> OCR or media metadata
  -> NLP classifier
  -> AI/API fallback
  -> unknown-needs-review
```

The current active API already has a first reader in:

`apps/api/file_intelligence_hub/workers/parsers.py`

Current deterministic readers:

- PDF signature/version
- DOCX metadata
- XLSX metadata
- CSV shape
- PNG/GIF/JPEG metadata

## Reference Engine Chain

We should run several reference engines and compare output instead of betting on
one:

1. deterministic suffix/signature classifier
2. file path/folder context classifier
3. sidecar classifier from `.fmeta`, `.chi`, `.fisnote`
4. local keyword/NLP classifier
5. vector similarity against known file/folder examples
6. AI/API classifier when local methods are not enough

Each engine returns:

```json
{
  "engine_id": "suffix-signature-v1",
  "label": "document",
  "category": "document",
  "confidence": 0.9,
  "reason": "suffix",
  "evidence": {
    "extension": ".pdf"
  }
}
```

The hub then chooses a consensus or marks the file for review.

## NLP Category Engine

NLP should classify files and folders into practical buckets:

- code
- document
- media
- data
- archive
- finance
- legal
- theology
- research
- API docs
- screenshots
- generated AI content
- unknown

The NLP engine should use:

- filename tokens
- folder tokens
- extension
- nearby files
- sidecar tags
- extracted text
- vector similarity
- user preferences

## Unknown File Rule

If the hub cannot read a file:

1. Record that it failed.
2. Store extension, signature bytes, size, hash, path, and folder context.
3. Create an action proposal: `needs_reader`.
4. Add it to a reader backlog.
5. Do not delete it.

Example:

```json
{
  "action_type": "needs_reader",
  "path": "D:/example/file.xyz",
  "reason": "No deterministic reader, no text extraction, unknown signature.",
  "requires_approval": false
}
```

## Storage

The hub should persist:

- which reader ran
- whether it succeeded
- extracted text path/hash
- classification candidates
- consensus label
- unresolved reader gaps

