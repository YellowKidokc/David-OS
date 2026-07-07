# Top of Mind Relay

Top of Mind is the API lane for routing messages between AI tools, command-line apps, clipboard helpers, and future UI panels.

## Folders

- `file_intelligence_hub/api/routes_top_of_mind.py`: HTTP endpoints for sources, messages, combine, and end-all controls.
- `file_intelligence_hub/storage/top_of_mind_repo.py`: SQLite persistence for sources and message history.
- `config/top_of_mind/sources.example.json`: starter map for Kimi, Codex, clipboard, folders, and walls.
- `docs/top-of-mind/`: design notes for the relay and future MCP/AutoHotkey/TypingMind bridge work.

## Flow

1. Register each tool as a source with `POST /top-of-mind/sources`.
2. Post incoming text with `POST /top-of-mind/messages`.
3. Read the shared stream with `GET /top-of-mind/messages?limit=75`.
4. Pin, move, archive, or reroute messages with `PATCH /top-of-mind/messages/{message_id}`.
5. Combine selected messages with `POST /top-of-mind/combine`.
6. Stop every active source with `POST /top-of-mind/controls/end-all`.

This gives the frontend a single left-side inbox, while every AI/program keeps its own source identity, priority, folder, and wall.
