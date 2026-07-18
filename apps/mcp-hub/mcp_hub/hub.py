"""Tool registry, normalized dispatch, context packets, and remote MCP proxying."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from .config import Settings
from .siyuan import SiyuanClient
from .transport import JsonTransport

LOGGER = logging.getLogger("mcp_hub")

ToolHandler = Callable[[dict], Any]


class ToolHub:
    def __init__(self, settings: Settings | None = None, siyuan: SiyuanClient | None = None, transport: JsonTransport | None = None):
        self.settings = settings or Settings()
        self.transport = transport or JsonTransport()
        self.siyuan = siyuan or SiyuanClient(self.settings, self.transport)
        self._tools: dict[str, tuple[dict, ToolHandler]] = {}
        self.register("knowledge.search", "Search SiYuan notes and blocks", self._knowledge_search, {
            "type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}, "notebook": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}
        })
        self.register("knowledge.get", "Read one SiYuan block as kramdown", self._knowledge_get, {
            "type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}
        })
        self.register("knowledge.context_packet", "Build compact cited context for an AI chat", self._context_packet, {
            "type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "max_chars": {"type": "integer"}, "purpose": {"type": "string"}, "notebook": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}
        })
        self.register("tool.list", "List local and connected MCP tools", lambda _: self.list_tools(), {"type": "object", "properties": {}})
        self.register("tool.call", "Call another tool by name", self._nested_call, {
            "type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "arguments": {"type": "object"}}
        })

    def register(self, name: str, description: str, handler: ToolHandler, input_schema: dict) -> None:
        self._tools[name] = ({"name": name, "description": description, "inputSchema": input_schema, "source": "local"}, handler)

    def list_tools(self) -> list[dict]:
        tools = [definition for definition, _ in self._tools.values()]
        for server in self.settings.remote_servers:
            try:
                response = self._remote_request(server, "tools/list", {})
                for tool in response.get("result", {}).get("tools", []):
                    tools.append({**tool, "name": f"{server['name']}.{tool['name']}", "source": server["name"]})
            except Exception as exc:  # remote discovery must not disable local tools
                LOGGER.warning("remote tool discovery failed server=%s error=%s", server.get("name"), exc)
        return tools

    def call(self, name: str, arguments: dict | None = None) -> dict:
        started = time.perf_counter()
        arguments = arguments or {}
        try:
            if name in self._tools:
                result = self._tools[name][1](arguments)
            else:
                result = self._call_remote(name, arguments)
            normalized = {"ok": True, "tool": name, "result": result}
            return self._bounded(normalized)
        except Exception as exc:
            LOGGER.warning("tool call failed tool=%s error=%s", name, exc)
            return {"ok": False, "tool": name, "error": str(exc)}
        finally:
            LOGGER.info("tool=%s duration_ms=%.1f", name, (time.perf_counter() - started) * 1000)

    def _knowledge_search(self, args: dict) -> list[dict]:
        query = str(args.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        return self.siyuan.search(query, args.get("limit", 8), args.get("notebook"), args.get("tags"))

    def _knowledge_get(self, args: dict) -> dict:
        block_id = str(args.get("id") or args.get("block_id") or args.get("document_id") or "").strip()
        if not block_id:
            raise ValueError("id is required")
        return self.siyuan.get(block_id)

    def _context_packet(self, args: dict) -> dict:
        query = str(args.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        requested = int(args.get("max_chars") or self.settings.max_context_chars)
        max_chars = max(200, min(requested, self.settings.max_context_chars))
        matches = self.siyuan.search(query, args.get("limit", 12), args.get("notebook"), args.get("tags"))
        purpose = str(args.get("purpose", "Background for the next AI response")).strip()
        header = f"Context purpose: {purpose}\nQuery: {query}\n\n"
        chunks, sources, used = [], [], len(header)
        for item in matches:
            citation = f"[SiYuan:{item['id']}]"
            chunk = f"{citation} {item['title']} — {item['excerpt']}\n"
            if used + len(chunk) > max_chars:
                break
            chunks.append(chunk)
            used += len(chunk)
            sources.append({"id": item["id"], "title": item["title"], "path": item["path"], "notebook": item["notebook"]})
        return {"context": (header + "".join(chunks)).rstrip(), "sources": sources, "truncated": len(sources) < len(matches), "max_chars": max_chars}

    def _nested_call(self, args: dict) -> dict:
        name = str(args.get("name", ""))
        if name == "tool.call":
            raise ValueError("tool.call cannot call itself")
        return self.call(name, args.get("arguments") or {})

    def _call_remote(self, qualified_name: str, arguments: dict) -> Any:
        server_name, separator, tool_name = qualified_name.partition(".")
        if not separator:
            raise KeyError(f"unknown tool: {qualified_name}")
        server = next((item for item in self.settings.remote_servers if item.get("name") == server_name), None)
        if not server:
            raise KeyError(f"unknown MCP server: {server_name}")
        response = self._remote_request(server, "tools/call", {"name": tool_name, "arguments": arguments})
        if "error" in response:
            raise RuntimeError(response["error"].get("message", "Remote MCP call failed"))
        return response.get("result")

    def _remote_request(self, server: dict, method: str, params: dict) -> dict:
        payload = {"jsonrpc": "2.0", "id": int(time.time_ns()), "method": method, "params": params}
        return self.transport.post(server["url"], payload, server.get("token", ""))

    def _bounded(self, value: dict) -> dict:
        encoded = json.dumps(value, ensure_ascii=False)
        if len(encoded) <= self.settings.max_response_chars:
            return value
        return {"ok": False, "tool": value.get("tool"), "error": "result exceeded MAX_RESPONSE_CHARS", "truncated": True}
