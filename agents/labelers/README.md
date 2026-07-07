# Labelers

This lane creates and updates portable file/folder identity markers.

## Active Tools

| Tool | Purpose |
| --- | --- |
| `filetagger.py` | Catalog files into SQLite and optionally write per-file `.fmeta` sidecars |
| `foldertagger.py` | Write per-folder `.folder.fmeta` markers while preserving folder IDs |
| `chi_pipeline.py` | CHI/Master Equation classification pipeline |
| `chi_profiles.py` | Swappable CHI profile lenses for domains like legal, therapy, political, corporate |
| `claim_jurisdiction.py` | What/How/Why claim jurisdiction classifier |
| `wordnet_expander.py` | Optional WordNet expansion for profile vocabularies |

## Sidecar Pattern

```text
example.pdf
example.pdf.fmeta
example.pdf.chi
example.pdf.fmeta.chi

SomeFolder/
  .folder.fmeta
```

## Safety

Sidecars are metadata, not executable code. They should be plain text,
markdown-readable, and safe to back up/sync.

Protected extensions:

- `.fmeta`
- `.chi`
- `.fisnote`
- `.fistag`
- `.fisdead`

## NLP Bridge

spaCy should be an optional feature extractor before CHI classification. It can
provide lemmas, part-of-speech tags, noun chunks, dependency relations, named
entities, and similarity features. CHI then uses those features to improve
classification and confidence.
