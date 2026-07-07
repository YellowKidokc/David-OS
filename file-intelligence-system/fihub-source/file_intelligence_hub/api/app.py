"""Minimal FastAPI app factory for local development."""
from __future__ import annotations

from fastapi import FastAPI

from file_intelligence_hub.api.routes_commands import router as commands_router
from file_intelligence_hub.api.routes_file_actions import router as file_actions_router
from file_intelligence_hub.api.routes_intelligence import router as intelligence_router
from file_intelligence_hub.api.routes_jobs import router as jobs_router
from file_intelligence_hub.api.routes_memory import router as memory_router
from file_intelligence_hub.api.routes_nodes import router as nodes_router
from file_intelligence_hub.api.routes_top_of_mind import router as top_of_mind_router


def create_app() -> FastAPI:
    app = FastAPI(title="File Intelligence Hub", version="0.1.0")
    app.include_router(jobs_router)
    app.include_router(commands_router)
    app.include_router(file_actions_router)
    app.include_router(intelligence_router)
    app.include_router(memory_router)
    app.include_router(nodes_router)
    app.include_router(top_of_mind_router)
    return app


app = create_app()
