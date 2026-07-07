"""Minimal FastAPI app factory for local development."""
from __future__ import annotations

from fastapi import FastAPI

from file_intelligence_hub.api.security import ApiTokenMiddleware

from file_intelligence_hub.api.routes_commands import router as commands_router
from file_intelligence_hub.api.routes_file_actions import router as file_actions_router
from file_intelligence_hub.api.routes_file_cache import router as file_cache_router
from file_intelligence_hub.api.routes_folders import router as folders_router
from file_intelligence_hub.api.routes_intelligence import router as intelligence_router
from file_intelligence_hub.api.routes_jobs import router as jobs_router
from file_intelligence_hub.api.routes_memory import router as memory_router
from file_intelligence_hub.api.routes_nodes import router as nodes_router
from file_intelligence_hub.api.routes_prediction import router as prediction_router
from file_intelligence_hub.api.routes_semantic import router as semantic_router
from file_intelligence_hub.api.routes_top_of_mind import router as top_of_mind_router


def create_app() -> FastAPI:
    app = FastAPI(title="File Intelligence Hub", version="0.1.0")
    app.include_router(jobs_router)
    app.include_router(commands_router)
    app.include_router(file_actions_router)
    app.include_router(file_cache_router)
    app.include_router(folders_router)
    app.include_router(intelligence_router)
    app.include_router(memory_router)
    app.include_router(nodes_router)
    app.include_router(prediction_router)
    app.include_router(semantic_router)
    app.include_router(top_of_mind_router)
    app.add_middleware(ApiTokenMiddleware)
    return app


app = create_app()
