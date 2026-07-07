# API menu, AHK buttons, and folder UX standard

This is the integration standard for keeping the React front end, AutoHotkey bridges, and Hub APIs powerful without becoming crowded.

## One-time API menu registry

The React app should load saved actions from `GET /api-actions` and treat each command as a saved API action with these fields:

- `label`: short button/menu text.
- `endpoint`: Hub API route such as `/folders/search`, `/files/cache/search`, `/jobs/file-events`, or `/top-of-mind/messages`.
- `method`: normally `GET` or `POST`.
- `default_payload`: reusable JSON template.
- `input_schema`: the few fields the operator needs to fill in.
- `result_card`: how to render returned folders, files, jobs, or messages.
- `ahk_binding`: optional hotkey/button metadata for AutoHotkey launchers.

The operator should enter connection details once, store them locally, and reuse the saved actions from compact menus or swappable panels rather than permanent screen clutter. The same action IDs are available to AutoHotkey and future bridge clients so buttons, palettes, and React cards do not drift apart.

## Layout recommendation

- Keep the chat/input composer as the center.
- Put an API menu near the composer for quick actions.
- Render returned folders, file movements/proposals, and job results as cards above or below the message box.
- Keep AutoHotkey buttons as a small command strip or palette. They should call the same API actions as React, not a separate workflow.

## Folder rules

Folders are first-class nested records in `/folders`. Each folder can have `parent_id` for folders-inside-folders and up to three tags for quick classification. Use metadata for richer keywords and notes.

Recommended endpoints:

- `POST /folders` to create folders with `tags` and optional `parent_id`.
- `GET /folders?tag=api` to filter by tag.
- `GET /folders/search?q=markov` to search names, slugs, tags, and metadata keywords.
- `GET /folders/tree` to render nested folders.
- `GET /api-actions?group=folders` to render the folder action menu from the shared registry.

The watcher should continue to create proposals/jobs only. React cards should show proposed folder destinations and require explicit approval before any destructive or organizing action happens.
