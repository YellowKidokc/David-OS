# spaCy to CHI Bridge

spaCy is a Python NLP toolkit, so it fits directly into the TOP AI FIS labeler
and CHI pipeline.

Official spaCy linguistic features include tokenization, part-of-speech tags,
morphology, lemmatization, dependency parsing, noun chunks, named entities,
sentence segmentation, and vectors/similarity.

Source: https://spacy.io/usage/linguistic-features

## Where It Hooks In

Current CHI scripts promoted into the active labeler lane:

- `agents/labelers/chi_pipeline.py`
- `agents/labelers/chi_profiles.py`
- `agents/labelers/claim_jurisdiction.py`
- `agents/labelers/wordnet_expander.py`

spaCy should not replace CHI. It should feed CHI better features.

```text
file reader extracts text
  -> spaCy extracts NLP features
  -> CHI pipeline classifies meaning/domain/jurisdiction
  -> sidecar gets updated
  -> SQLite indexes the result
```

## Useful spaCy Features For FIS

| spaCy Feature | FIS Use |
| --- | --- |
| lemmas | Better keyword matching across word forms |
| POS tags | Distinguish claim style, names, actions, data |
| noun chunks | Better file/folder tags and rename suggestions |
| named entities | People, organizations, dates, laws, places |
| dependency parse | Claim structure and What/How/Why diagnosis |
| sentence segmentation | Chunking documents into classifiable claims |
| vectors/similarity | Optional category/reference matching |

## Optional Dependency

Baseline FIS should work without spaCy. If spaCy is installed, the NLP bridge can
add features. If not, CHI falls back to regex/keyword/WordNet/local vector logic.

Suggested install later:

```powershell
python -m pip install spacy
python -m spacy download en_core_web_sm
```

For bigger entity/vector work later:

```powershell
python -m spacy download en_core_web_md
```

