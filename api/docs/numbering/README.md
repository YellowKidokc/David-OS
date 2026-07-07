# Top of Mind Numbering Schema v1.0

One universal numbering system for ports, sources, message types, priorities, walls, folders, API routes, and future internal codes.

Machine-readable registry:

`config/numbering/top_of_mind_numbering.v1.json`

## Ranges

| Range | Category |
| --- | --- |
| `10000-19999` | ports |
| `20000-29999` | source IDs |
| `30000-39999` | message type codes |
| `40000-40099` | priority codes |
| `50000-50999` | wall/workspace IDs |
| `60000-60999` | folder IDs |
| `70000-99999` | reserved |

## Default Ports

| Code Range | Service | Default |
| --- | --- | --- |
| `10000-10099` | File Intelligence Hub main API | `10000` |
| `10100-10199` | Top of Mind relay if split | `10100` |
| `10200-10299` | File Drop API if split | `10200` |
| `10600-10699` | Search/vector proxy | `10600` |
| `10800-10899` | MCP relay servers | `10800` |

Native ports that stay as-is:

- Postgres: `5432`, `2665`
- Qdrant: `6333`
- Ollama: `11434`
- Synology Chat: `2349`
- Kimi MCP bridge: `9201`
- Kimi WebBridge: `10086`

## High-Frequency Codes

- Clipboard source: `22001`
- AHK Controller source: `22002`
- Codex source: `20040`
- Kimi CLI source: `20030`
- Top of Mind frontend source: `23004`
- Normal chat: `30001`
- AI response: `30002`
- Clipboard capture: `32001`
- Stop all: `33005`
- Memory store: `34001`
- Normal priority: `40003`
- High priority: `40007`
- Main wall: `50001`
- Inbox folder: `60001`

## Message Shape

Messages can carry both human names and stable numeric codes:

```json
{
  "source_id": "clipboard",
  "source_code": 22001,
  "source_label": "Clipboard",
  "type_code": 32001,
  "priority": 3,
  "priority_code": 40003,
  "wall": "main",
  "wall_code": 50001,
  "folder": "Inbox",
  "folder_code": 60001,
  "body": "whatever was on the clipboard"
}
```

## Expansion Rules

- Never reuse a number.
- Deprecated numbers stay reserved.
- Add new items to the registry instead of inventing untracked constants.
- Keep names human-readable, but use numeric codes for durable routing and cross-tool agreement.
