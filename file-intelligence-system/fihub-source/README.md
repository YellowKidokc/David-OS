# file-intelligence-hub

A local control-plane for file-first automation. The hub observes file activity, turns meaningful work into durable SQLite jobs, runs deterministic workers first, and gates risky actions through review before workers mutate files.

## Layers

- `api/`: thin FastAPI routes and app assembly.
- `core/`: orchestration and review gates.
- `storage/`: SQLite schema, migrations, and repositories.
- `workers/`: deterministic job execution such as hashing, classification, rename, and folder summaries.
- `watchers/`: native and polling filesystem event intake.
- `intelligence/`: canonical file facts and compressed folder pattern builders.
- `services/`: operational node health and safe repair logic.
- `config/` and `rules/`: centralized policy inputs; watched folders do not contain local scripts.
- `docs/top-of-mind/` and `config/top_of_mind/`: multi-agent relay notes and source/folder/wall setup for AI, clipboard, and MCP-style controls.

## Local commands

```bash
fihub-api --host 127.0.0.1 --port 8000
fihub-watch --profiles config/folder_profiles.json
fihub-poll --profiles config/folder_profiles.json --once
fihub-worker --limit 1
fihub-health --db .data/file-intelligence-hub.sqlite3
```

## Top of Mind API

The Top of Mind relay lives under `/top-of-mind` and gives other programs one API lane for registering sources, posting messages, pinning/moving items, combining selected messages, and stopping active sources.

See `docs/top-of-mind-api-blueprint.md` for the full API brain map: hub routes, desktop bridges, memory/vectorization, file operators, integrations, and security rules.

## Packaging note

The package discovery is intentionally constrained to `file_intelligence_hub*` so top-level support directories such as `config/` and `schemas/` are shipped as data files instead of being mistaken for import packages.
