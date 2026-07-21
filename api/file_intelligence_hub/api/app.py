"""Minimal FastAPI app factory for local development."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from file_intelligence_hub.api.security import ApiTokenMiddleware

from file_intelligence_hub.api.routes_api_actions import router as api_actions_router
from file_intelligence_hub.api.routes_agents import router as agents_router
from file_intelligence_hub.api.routes_clipboard import router as clipboard_router
from file_intelligence_hub.api.routes_commands import router as commands_router
from file_intelligence_hub.api.routes_conversation_os import router as conversation_os_router
from file_intelligence_hub.api.routes_file_actions import router as file_actions_router
from file_intelligence_hub.api.routes_file_cache import router as file_cache_router
from file_intelligence_hub.api.routes_fis import router as fis_router
from file_intelligence_hub.api.routes_folders import router as folders_router
from file_intelligence_hub.api.routes_intelligence import router as intelligence_router
from file_intelligence_hub.api.routes_jobs import router as jobs_router
from file_intelligence_hub.api.routes_memory import router as memory_router
from file_intelligence_hub.api.routes_nodes import router as nodes_router
from file_intelligence_hub.api.routes_openai_compat import router as openai_compat_router
from file_intelligence_hub.api.routes_prediction import router as prediction_router
from file_intelligence_hub.api.routes_semantic import router as semantic_router
from file_intelligence_hub.api.routes_top_of_mind import router as top_of_mind_router


def create_app() -> FastAPI:
    app = FastAPI(title="File Intelligence Hub", version="0.1.0")
    app.include_router(jobs_router)
    app.include_router(api_actions_router)
    app.include_router(agents_router)
    app.include_router(clipboard_router)
    app.include_router(commands_router)
    app.include_router(conversation_os_router)
    app.include_router(file_actions_router)
    app.include_router(file_cache_router)
    app.include_router(fis_router)
    app.include_router(folders_router)
    app.include_router(intelligence_router)
    app.include_router(memory_router)
    app.include_router(nodes_router)
    app.include_router(openai_compat_router)
    app.include_router(prediction_router)
    app.include_router(semantic_router)
    app.include_router(top_of_mind_router)
    app.add_middleware(ApiTokenMiddleware)
    # Browser clients (the desk app on Vite/Cloudflare) are cross-origin, so
    # without CORS headers every fetch is silently blocked by the browser.
    # Added last so it wraps the token middleware and 401s carry CORS headers.
    # Restrict origins in LAN/server mode with FIHUB_CORS_ORIGINS=<comma-separated>.
    origins = [
        origin.strip()
        for origin in os.environ.get("FIHUB_CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = create_app()
