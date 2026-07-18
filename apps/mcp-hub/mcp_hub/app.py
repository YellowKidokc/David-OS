"""FastAPI surface for AI chats, browser connectors, and AutoHotkey."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import Settings
from .hub import ToolHub


class ToolCall(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str
    limit: int = 8
    notebook: str | None = None
    tags: list[str] = Field(default_factory=list)


class ContextRequest(SearchRequest):
    max_chars: int | None = None
    purpose: str | None = None


class KnowledgeGetRequest(BaseModel):
    id: str


def create_app(settings: Settings | None = None, hub: ToolHub | None = None) -> FastAPI:
    settings = settings or Settings()
    hub = hub or ToolHub(settings)
    app = FastAPI(title="David OS MCP Hub", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "service": "mcp-hub", "writes_enabled": settings.allow_writes, "tools": len(hub._tools)}

    @app.get("/tools")
    def tools() -> dict:
        return {"ok": True, "tools": hub.list_tools()}

    @app.post("/tools/call")
    def call_tool(request: ToolCall) -> dict:
        return hub.call(request.name, request.arguments)

    @app.post("/knowledge/search")
    def search(request: SearchRequest) -> dict:
        return hub.call("knowledge.search", request.model_dump(exclude_none=True))

    @app.post("/knowledge/get")
    def get_knowledge(request: KnowledgeGetRequest) -> dict:
        return hub.call("knowledge.get", request.model_dump())

    @app.post("/knowledge/context")
    def context(request: ContextRequest) -> dict:
        response = hub.call("knowledge.context_packet", request.model_dump(exclude_none=True))
        if response.get("ok") and isinstance(response.get("result"), dict):
            return {"ok": True, **response["result"]}
        return response

    return app


app = create_app()
