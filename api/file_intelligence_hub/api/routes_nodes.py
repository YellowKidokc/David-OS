"""Node heartbeat, health, and safe repair endpoints."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from file_intelligence_hub.services.node_health import NodeHealthService
from file_intelligence_hub.storage.db import Database
from file_intelligence_hub.storage.job_repo import JobRepo
from file_intelligence_hub.storage.node_repo import NodeRepo

DEFAULT_DB_PATH = Path(os.environ.get("FIHUB_DB_PATH", ".data/file-intelligence-hub.sqlite3"))
router = APIRouter(prefix="/nodes", tags=["nodes"])


class PeerHeartbeatRequest(BaseModel):
    node_id: str
    node_role: str = "peer"
    capabilities: list[str] = Field(default_factory=list)
    status: str = "isolated_but_running"
    resources: dict[str, object] = Field(default_factory=dict)
    local_queue_depth: int = 0
    version: str = "unknown"
    build_signature: str = "unknown"


class RepairRequest(BaseModel):
    artifact_path: str
    source_root: str
    source_node: str | None = None


def _service(node_id: str = "local") -> NodeHealthService:
    db = Database(DEFAULT_DB_PATH)
    return NodeHealthService(NodeRepo(db.conn), JobRepo(db.conn), node_id=node_id)


@router.post("/heartbeat")
def local_heartbeat(node_id: str = "local") -> dict[str, object]:
    return {"node": _service(node_id).heartbeat()}


@router.post("/peer-heartbeat")
def peer_heartbeat(request: PeerHeartbeatRequest) -> dict[str, object]:
    return {"node": _service().receive_peer_heartbeat(request.model_dump())}


@router.get("/health")
def local_health(node_id: str = "local") -> dict[str, object]:
    return {"health": _service(node_id).check_local_health()}


@router.get("")
def list_nodes() -> dict[str, object]:
    db = Database(DEFAULT_DB_PATH)
    return {"nodes": NodeRepo(db.conn).list_nodes()}


@router.post("/repair/safe-artifact")
def repair_safe_artifact(request: RepairRequest) -> dict[str, object]:
    try:
        return {"repair": _service().repair_safe_artifact(request.artifact_path, source_root=request.source_root, source_node=request.source_node)}
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
