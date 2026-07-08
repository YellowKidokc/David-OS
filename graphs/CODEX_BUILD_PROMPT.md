# CODEX BUILD PROMPT — graphs (The Second Brain)
## Location: D:\GitHub\David-OS\graphs
**Fabel (Opus) | 2026-07-07 | This is both the spec and the build order. Queue position 7 — runs after api\ (schema) is green.**

## What this is
One graph system serving four hubs, with three properties no other knowledge graph has:
1. **Edges carry their WHY** — evidence payloads, not bare weights.
2. **Anti-edges are first-class** — what does NOT connect and why not.
3. **Algorithms are overlays, not architecture** — one graph store, many switchable lenses.
Plus the retrieval layer that makes it operational (the 70%): deterministic code answers
"where does this live" before any model is invoked.

## Read-only inputs (steal ideas, never import at runtime, NEVER modify)
- `D:\DONT TOUCH BOOT UP\17_KNOWLEDGE_GRAPHS\generators\` — build_graphs.py + graphlib.py:
  the working HTML template (vis-network inlined, offline, click node/edge -> sidebar,
  client-side Dijkstra). THIS IS THE RENDERER BASE. Port it, don't rewrite it.
- `...\graphify\CLAIM_FORCE_TAXONOMY.md` — the edge force type system (F0..F4). Adopt as-is.
- `...\graphify\NABLA_SEMANTIC_ADDRESSING_PROTOCOL.md` — addressing scheme for node IDs.
- `...\_REFERENCE_REPOS\` — study for ideas: gbrain (every answer cites sources; brain
  self-cleans), graphify-8 (notes-as-graph, MCP/SQLite pattern), Understand-Anything
  (click-anything explainer UX), qmd concept (semantic scoring).
- `PICS\91cb...pdf` — the five principles. Principle 3 (deterministic ladder) and
  4 (small index, never drifts) are LAW for this build.
- David-OS assets already built: `llm-wiki\` (the Karpathy-pattern index over 25,686
  pages — the foundation already exists), `pipeline\chat_topic_segmenter.py` +
  `chat_fat_cutter.py` (AI Hub intake), `api\file_intelligence_hub\services\semantic_addressing.py`.

## The four hubs (node namespace `hub:` on every node)
- `ai-hub` — conversation atoms (topic-segmented, fat-cut docs from pipeline\)
- `cross-domain` — Level 2: cycle history, power structure, moral event kernel docs
- `framework` — Laws, axioms (188), claims, papers, Lean status
- `operations` — David-OS itself: agents, watchers, skills, routines, connected apps
  (the ARMS view: seeing the agentic surface IS seeing the risk surface)

## Data model (tables added to the hub SQLite via NEW migrations — coordinate with api\ schema)
```
nodes(id TEXT PK, hub, type, label, path, summary, chi_score REAL, props JSON)
  -- type: file|claim|axiom|law|paper|institution|conv_atom|agent|skill|routine|app
edges(id PK, src, dst, type, force, weight REAL, evidence JSON)
  -- type: supports|contradicts|extends|iso_formal|iso_structural|analogy|cooccur|depends
  -- force: F0..F4 per CLAIM_FORCE_TAXONOMY
  -- evidence: [{doc_id, sentence, score, lean_status?}] — REQUIRED for non-cooccur edges
anti_edges(id PK, src, dst, status, why_not, evidence JSON)
  -- status: unbridged      (should exist, work not done — e.g. Laws 1,2,3,6,8,10 underived)
  --         contradicts    (pipeline found opposing claims)
  --         eliminated     (tested and killed — the 30 structural eliminations)
  --         candidate      (high semantic similarity + zero co-occurrence — discovery queue)
graph_index(node_id, keywords, one_liner)   -- principle 4: one line per node, updated on every write
```

## Components (build in this order)
1. **`graphs\store.py`** — CRUD over the tables above + JSON export per hub and whole-graph.
2. **`graphs\builders\`** — port the six generators from build_graphs.py to write INTO the
   store instead of ad-hoc JSON. Add builder #7: anti-edge harvester (four sources listed
   in the data model). Each builder is a hub worker job (`graph_rebuild:<name>`).
3. **`graphs\brain.py`** — the deterministic retrieval ladder, EXACTLY per the PDF:
   strip keywords -> score graph_index + llm-wiki index WITHOUT opening files ->
   open single best -> extract only the answering section -> follow ONE pointer ->
   return evidence bundle. Model never invoked inside brain.py. Also:
   `brain.py remember "<text>"` writes a memory file AND its index line in one step.
   Expose through the hub as `GET /brain/query?q=` so the whole Mattermost crew uses it.
4. **`graphs\render\`** — ONE html template (ported from graphlib). Adds:
   layer toggle per hub; overlay dropdown (community detect, centrality, chi heat,
   force filter, shortest path, anti-edge density); anti-edge rendering (dashed red =
   contradicts, ghost gray = unbridged, skull marker = eliminated, dotted amber = candidate);
   evidence sidebar showing the WHY payload verbatim with doc links.
   Self-contained output: embeds in Obsidian, faiththruphysics, or standalone.

## Kill conditions (per the PDF's principle 5 — prove it or keep working)
- `python graphs\brain.py "which TTS voice do we use"` answers from index without the
  model, under 1s, and cites its source file+section.
- Same 10 real questions: brain path vs naive full-search — brain must win on tokens
  AND wall time; produce the comparison table.
- law_isomorphism graph renders with at least one edge of every type INCLUDING all four
  anti-edge statuses, each clickable to its evidence.
- Reload of the rendered HTML under 10 seconds at full corpus size.
- Zero writes outside David-OS. `D:\DONT TOUCH BOOT UP` remains byte-identical.

## Dependencies
Needs: api\ prompt DONE (schema/migrations). Feeds: apps\desk (graph view page),
llm-wiki (shared index), Mattermost crew (brain endpoint), the Level 2 documents.

## Priority
store.py -> anti-edge harvester -> brain.py -> renderer. The anti-graph is the
differentiator; do not let it slip to "later." Post to town-square after each component.
