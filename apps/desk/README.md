# Top of Mind Desk

React/Vite frontend for the Top of Mind API. The default API base is `http://127.0.0.1:10000`.

## Install

```bash
cd apps/desk
npm install
```

## Development

```bash
npm run dev
```

## Build

```bash
npm run build
```

## API base override

Create an environment file or export the variable before starting Vite:

```bash
VITE_TOP_OF_MIND_API=http://127.0.0.1:10000 npm run dev
```

The in-app API settings panel also lets you edit the base URL, saves it to `localStorage`, and tests connectivity.

## Wired panels and endpoints

- Top of Mind sources, messages, combine, and end-all controls.
- Durable folders via `GET /folders` and `POST /folders`; nested folders use API `parent_id` and `folder_code`.
- Memory search with text mode and vector mode.
- File cache search.
- Funnel sidebar for source include/exclude, pause/mute/status display, and selected-message routing drafts.
- Operator draft panel for `write_text` and `append_text` payloads. It intentionally does not run destructive actions by default.

## Numbering defaults

Message posts include human labels plus numeric `source_code`, `type_code`, `priority_code`, `wall_code`, and `folder_code` defaults for Clipboard, AHK, Codex, Kimi CLI, normal/response/clipboard types, normal/high priority, main/code walls, and inbox/active folders.
