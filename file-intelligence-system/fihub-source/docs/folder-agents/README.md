# Folder Agents and File Actions

Folder agents are small watchers or bridge scripts that talk to the hub API instead of mutating files on their own.

## Basic Shape

1. A watcher scans a folder or receives an OCR/clipboard/window event.
2. It posts the text or observation to `/top-of-mind/messages`.
3. If a file needs work, it posts a file action to `/operator/file-actions`.
4. The hub either executes the action immediately or creates a review item.
5. Approved actions write to the ledger so later scans know what happened.

## File Actions

`POST /operator/file-actions`

Supported actions:

- `write_text`: write Markdown, TXT, JSON, CSV, or other text.
- `append_text`: append to an existing text file.
- `touch`: create an empty file or update its timestamp.
- `copy`: copy a file.
- `move`: move a file.
- `archive`: move a file into an archive folder.
- `delete`: delete a file or empty folder.
- `open`: start a file with the Windows default application.

Set `review_required` to `true` for actions that should wait for approval.

## AutoHotkey Bridge Idea

AutoHotkey can capture a hotkey, clipboard text, or a window rectangle and send JSON to the API. That makes AHK the low-power front hand, while the hub records the decision and does the file work.
