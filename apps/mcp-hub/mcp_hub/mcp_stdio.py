"""Minimal MCP 2025-03-26 stdio server for Codex, Claude Desktop, and peers."""

from __future__ import annotations

import json
import sys

from .hub import ToolHub


def dispatch(message: dict, hub: ToolHub) -> dict | None:
    request_id = message.get("id")
    method = message.get("method")
    if request_id is None:
        return None
    if method == "initialize":
        result = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "david-os-mcp-hub", "version": "0.1.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{key: value for key, value in tool.items() if key != "source"} for tool in hub.list_tools()]}
    elif method == "tools/call":
        params = message.get("params") or {}
        response = hub.call(params.get("name", ""), params.get("arguments") or {})
        result = {"content": [{"type": "text", "text": json.dumps(response, ensure_ascii=False)}], "isError": not response.get("ok")}
    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> None:
    hub = ToolHub()
    for line in sys.stdin:
        try:
            response = dispatch(json.loads(line), hub)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}}), flush=True)


if __name__ == "__main__":
    main()
