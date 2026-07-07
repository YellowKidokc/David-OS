# API Calls

This folder holds prompt/API call packs and routing manifests that feed the Top of Mind hub.

Current purpose:

- preserve reusable prompt calls
- route station outputs into website, Excel, memory, and vectorization workflows
- document missing stations that need retrieval or corpus search
- provide material that can be imported into `/memory/items`

Important files:

- `API_ROUTING_MANIFEST.md`: sheet/output routing, missing stations, and vectorization plan.
- `Top of Mind - Numbering Schema v1.0.txt`: original numbering-schema source material.
- `Top of Mind - Pre-Built Integrations Worth Grabbing.txt`: integration ideas and candidates.

How it should connect:

1. Store reusable calls as memory items or prompt-library records.
2. Route generated outputs into `/top-of-mind/messages`.
3. Store durable research notes in `/memory/items`.
4. Use `/memory/embed-pending` after adding a batch.
5. Use `/files/cache` for local/NAS file lookup before file actions.

Do not put secrets or raw API keys in this folder.
