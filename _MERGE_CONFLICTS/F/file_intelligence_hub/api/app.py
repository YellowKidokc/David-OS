"""Minimal FastAPI app factory for local and LAN development."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from file_intelligence_hub.api.routes_agents import router as agents_router
from file_intelligence_hub.api.routes_clipboard import router as clipboard_router
from file_intelligence_hub.api.routes_commands import router as commands_router
from file_intelligence_hub.api.routes_file_actions import router as file_actions_router
from file_intelligence_hub.api.routes_file_cache import router as file_cache_router
from file_intelligence_hub.api.routes_folders import router as folders_router
from file_intelligence_hub.api.routes_intelligence import router as intelligence_router
from file_intelligence_hub.api.routes_jobs import router as jobs_router
from file_intelligence_hub.api.routes_memory import router as memory_router
from file_intelligence_hub.api.routes_nodes import router as nodes_router
from file_intelligence_hub.api.routes_top_of_mind import router as top_of_mind_router


PUBLIC_PATHS = {"/docs", "/redoc", "/openapi.json"}


class OptionalTokenAuthMiddleware(BaseHTTPMiddleware):
    """Require a shared token only when FIHUB_API_TOKEN is configured."""

    async def dispatch(self, request, call_next):  # type: ignore[no-untyped-def]
        token = os.environ.get("FIHUB_API_TOKEN")
        if not token or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        supplied = request.headers.get("x-fihub-token", "")
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()

        if supplied != token:
            return JSONResponse({"detail": "missing or invalid FIHUB_API_TOKEN"}, status_code=401)

        return await call_next(request)


def create_app() -> FastAPI:
    app = FastAPI(title="File Intelligence Hub", version="0.1.0")
    # Allow the browser desk (local dev + deployed) to call the hub.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(OptionalTokenAuthMiddleware)
    app.include_router(jobs_router)
    app.include_router(agents_router)
    app.include_router(clipboard_router)
    app.include_router(commands_router)
    app.include_router(file_actions_router)
    app.include_router(file_cache_router)
    app.include_router(folders_router)
    app.include_router(intelligence_router)
    app.include_router(memory_router)
    app.include_router(nodes_router)
    app.include_router(top_of_mind_router)
    return app


app = create_app()
