# Top of Mind control-plane audit and implementation plan

## Inventory

### Frontend (`apps/desk`)
- `src/main.jsx`: single React entry point for the shell, rail navigation, sidebar, funnel, API shelf, operator surface, slash API command handling, chat workspace wiring, and local fallback data.
- `src/components/chat/*`: connected chat view, message cards, source filter, and composer.
- `src/components/prompts/PromptsPanel.jsx`: prompt library surface feeding the composer.
- `src/components/knowledge/KnowledgePanel.jsx` and `src/components/settings/SettingsPanel.jsx`: componentized panels that are not yet fully routed from `main.jsx`.
- `src/lib/api/topOfMindApi.js`: frontend API client for Top of Mind routes, folders, memory, file cache, jobs, clipboard, and bridge calls.

### Backend (`api/file_intelligence_hub`)
- FastAPI app factory in `api/app.py` includes routers for jobs, API actions, agents, clipboard, commands, file actions, file cache, FIS, folders, intelligence, memory, nodes, OpenAI-compatible chat, predictions, semantic search, and top-of-mind messages.
- SQLite migrations and schema management live in `storage/db.py`; repositories wrap SQLite access (`job_repo`, `clipboard_repo`, `folder_repo`, `memory_repo`, `node_repo`, `top_of_mind_repo`, and others).
- Review-gated worker and action paths already exist for commands, file actions, jobs, reviews, nodes, and ledger entries.
- AutoHotkey bridge endpoints are exposed through `/bridge/*` style routes in the command/agent bridge surface and existing AHK imports under `ahk/`, `bridges/ahk/`, and `apps/gui-neighborhood/imports/ahk_v2`.

### Tests and configuration
- API tests live in `api/tests`, including clipboard, command/memory, file cache, FIS, numbering, operator extensions, and Top of Mind tests.
- Desk config lives in `apps/desk/package.json`, `.env.example`, Vite config, and `wrangler.toml`.
- Integration docs/config live under `api/docs`, `api/config`, `config/rules`, and root `docs`.

## Route-to-component matrix

| Route family | Backend route | Frontend surface | Status |
| --- | --- | --- | --- |
| Messages | `/top-of-mind/sources`, `/top-of-mind/messages`, `/top-of-mind/combine`, `/top-of-mind/controls/end-all` | Chat workspace, funnel, composer | Connected, with local optimistic fallback for failed message post/patch |
| Folders | `/folders` | Sidebar folder tree | Partially connected; folder creation/listing is backend-backed, star/tag UI metadata remains local-only |
| Prompts | Frontend prompt library | `PromptsPanel` and slash prompt flow | Local/fallback driven unless prompt backend is added |
| Clipboard | `/clipboard/*` | New `ClipboardWorkspace` | Connected to existing clipboard SQLite repo and AHK copy handoff route |
| API actions/registry | `/api-actions/*` plus hard-coded API shelf data | API shelf | Partially connected; cards remain seeded in frontend/localStorage and need durable backend registry migration |
| File cache | `/files/cache*` | File search panel | Connected search panel, minimal detail UI |
| Memory | `/memory/*` | Memory search panel | Connected search panel, minimal detail UI |
| Commands | `/operator/commands` | Operator surface + slash commands | Connected but intentionally review/dry-run oriented |
| File actions | `/operator/file-actions` | Operator surface | Connected but review-gated/default-safe |
| Jobs/reviews/nodes | `/jobs/*`, `/nodes/*` | Operator/funnel surfaces | Backend exists; unified operations center is not yet complete |
| Agents | `/agents/*` | Funnel, operator surface, command palette | Partially connected; local custom agents still need durable backend registry |
| Semantic/prediction/intelligence | `/semantic/*`, `/prediction/*`, `/intelligence/*` | Search/file panels | Backend exists; unified evidence search UI is deferred |

## Connection audit

- Fully connected: chat message relay, source list, folder list/create, memory search, file cache search, clipboard persistence/list/search/copy/import/export, command/file-action submission surfaces.
- Partially connected: API registry cards, custom agents, folder star/tag metadata, prompt library, command palette catalog entries for models/plugins/workflows/recent projects.
- LocalStorage-only: API shelf custom cards, custom agents added from operator builder, command palette favorites/recents, system prompt text, sidebar folder UI metadata.
- Mock/fallback driven: starter sources/folders, some operator buttons that report unavailable routes, attachment handling, several API cards marked offline/needs key.
- Nonfunctional or intentionally inert: destructive operator actions that only draft/require review, external API docs import that cannot parse non-machine-readable documentation yet.

## Duplicate, obsolete, and conflicting implementations

- Clipboard UI exists in several imported AHK HTML modules, but the active Desk app had no full React clipboard page before this slice. The implementation below uses the existing backend clipboard repository instead of creating a second database.
- `_MERGE_CONFLICTS/*` contains duplicate historical copies of `file_intelligence_hub`; those are not active application code.
- There are legacy file-intelligence copies under `file-intelligence-system/*`; active API code is `api/file_intelligence_hub`.
- `apps/desk/src/main.jsx` still concentrates multiple panels in one file; plugin manifests should eventually reduce hard-coded panels without replacing working routes.

## Implementation plan

### Priority 1 — clipboard workspace
Implemented in this slice: durable React page, backend filters/facets/duplicates/merge/restore/export/retention preference routes, secret warnings, and future image metadata columns. Remaining: native Windows clipboard write confirmation via a live AHK worker and scheduled retention pruning.

### Priority 2 — universal command palette
Implemented first slice: global `Ctrl/Cmd+K`, fuzzy-ish multi-term search, favorites, recents, keyboard navigation, and action metadata/permissions/parameters. Remaining: backend action registry, model/plugin/workflow/recent-project providers, and parameter execution forms.

### Priority 3 — durable API registry
Deferred implementation after clipboard/palette foundation. Plan: add `api_integrations` migration + repository, seed existing cards, add OpenAPI import route, store secret references only, and migrate the Desk API shelf to backend reads.

### Priority 4 — operations center
Deferred implementation. Plan: build from existing `jobs`, `job_events`, `review_items`, `nodes`, and `ledger_entries`; add consolidated read models before adding any new tables.

### Priority 5 — mutation ledger and undo
Deferred implementation. Plan: extend existing `ledger_entries` schema with actor/source/reason/model/approval/reversible/undo fields and wire write/move/delete/command/API mutation routes through ledger helpers while keeping destructive actions review-gated.

## Conversation operating-system slice

Implemented after the clipboard foundation:

- Added a durable conversation OS model for `Conversation`, `ConversationBranch`, `ConversationState`, `AgentMembership`, `AgentArrival`, `ContextGrant`, `ResponseProposal`, `ReentryPacket`, and `Decision`.
- Invitations are explicit contracts with separate `context_scope`, `response_mode`, and permission flags. The default remains limited: recent context, silent advisory, no prior-history access, no visible speaking, no agent self-invitation, no file/command mutation, and approval required.
- Arrival events have lifecycle states so a new AI contribution can be previewed, invited, asked silently, branched, deferred, dismissed, or archived without interrupting the current conversation.
- Branches retain parent conversation provenance, branch point, participants, snapshot/shared-state mode, and manual merge-back policy.
- Re-entry packets are tiered by inactivity duration and use the saved conversation state to avoid re-sending the same full prompt every turn.

Deferred follow-up:

- Wire real remote agent responses into `agent_arrivals` instead of using the UI simulation helper.
- Add conductor-side duplicate suppression and contradiction flagging for `response_proposals`.
- Add persisted trigger rules and suppression windows for first-message-of-day, post-reboot, post-merge, contradiction-found, and project/file-change re-entry events.
