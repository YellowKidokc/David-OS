# David OS MCP Hub

Local, read-first bridge between Top-of-Mind/TypingMind, AutoHotkey, MCP-capable AI clients, remote MCP servers, and SiYuan.

## What version 1 provides

- HTTP: `GET /health`, `GET /tools`, `POST /tools/call`, `POST /knowledge/search`, `POST /knowledge/get`, and `POST /knowledge/context`.
- Local tools: `knowledge.search`, `knowledge.get`, `knowledge.context_packet`, `tool.list`, and `tool.call`.
- Direct SiYuan Kernel API access at `127.0.0.1:6806` by default.
- Optional remote streamable-HTTP MCP discovery/calls. Remote tools are namespaced as `<server>.<tool>`.
- An MCP stdio mode for Codex, Claude Desktop, and other local MCP clients.
- Browser access through configurable CORS (`MCP_HUB_CORS_ORIGINS`); the default is `*` for this loopback-only service.
- No write or delete tools. `ALLOW_WRITES` is reserved for a later explicitly gated version.
- Response and context size caps. Logs contain tool names and timings, not note bodies.

## Install and run

```bash
cd apps/mcp-hub
python -m venv .venv
. .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env                # export values or use your process manager to load it
mcp-hub
```

The service reads process environment variables directly; `.env` is a documented template and should be loaded by your shell or process manager.

Open `http://127.0.0.1:8787/docs` for the HTTP API. Example context request:

```bash
curl -X POST http://127.0.0.1:8787/knowledge/context \
  -H 'Content-Type: application/json' \
  -d '{"query":"Top of Mind agent architecture","max_chars":4000,"purpose":"Continue the work"}'
```

The response contains compact cited text plus source IDs and human paths. It never expands every matching document.

## SiYuan

Set `SIYUAN_TOKEN` if authentication is enabled. The adapter uses `/api/query/sql` for read-only block search and `/api/block/getBlockKramdown` for retrieval. Queries escape SQL string literals, cap result counts at 50, and expose no arbitrary SQL endpoint.

## Remote MCP servers

Set `MCP_SERVERS_JSON` to a JSON array. The hub sends JSON-RPC `tools/list` and `tools/call` requests to each configured streamable-HTTP URL:

```json
[{"name":"siyuan_note","url":"http://127.0.0.1:9000/mcp","token":""}]
```

A remote `search` tool then appears as `siyuan_note.search`. A failing remote server is isolated and does not hide local tools.

## MCP client configuration

After `pip install -e .`, add a stdio server to a compatible client:

```json
{
  "mcpServers": {
    "david_os": {
      "command": "mcp-hub-stdio",
      "env": {
        "SIYUAN_HOST": "127.0.0.1",
        "SIYUAN_PORT": "6806",
        "SIYUAN_TOKEN": ""
      }
    }
  }
}
```

For browser chats without tool support, call `/knowledge/context` from the Top-of-Mind API or AutoHotkey, then paste the returned `context` into the chat. Keep the returned `sources` beside the response for traceability.
