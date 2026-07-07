"""Agent routing: send an outbound message addressed to a specific agent.

The hub records the message in the shared Top of Mind stream with a
`target_agent_id` and `delivery: pending` marker. A client (AHK bridge, desk)
polls for pending outbound messages and delivers them to the target AI, then
the reply comes back in through /top-of-mind/messages.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from file_intelligence_hub.storage.db import Database
from file_intelligence_hub.storage.top_of_mind_repo import TopOfMindRepo

DEFAULT_DB_PATH = Path(os.environ.get("FIHUB_DB_PATH", ".data/file-intelligence-hub.sqlite3"))
router = APIRouter(prefix="/agents", tags=["agents"])


class AgentSendRequest(BaseModel):
    agent_id: str
    body: str
    from_id: str = "operator"
    from_label: str = "Operator"
    role: str = "user"          # message is FROM the operator/hub TO the agent
    wall: str = "main"
    folder: str = "Outbound"
    priority: int | None = Field(default=None, ge=0, le=10)
    metadata: dict[str, object] = Field(default_factory=dict)


def _repo() -> TopOfMindRepo:
    db = Database(DEFAULT_DB_PATH)
    return TopOfMindRepo(db.conn)


@router.get("/list")
def list_agents() -> dict[str, object]:
    """Agents are Top of Mind sources; this mirrors /top-of-mind/sources."""
    return {"agents": _repo().list_sources()}


@router.post("/send")
def agent_send(request: AgentSendRequest) -> dict[str, object]:
    metadata = dict(request.metadata)
    metadata.update({"target_agent_id": request.agent_id, "delivery": "pending"})
    try:
        message = _repo().post_message(
            source_id=request.from_id,
            source_label=request.from_label,
            body=request.body,
            role=request.role,
            wall=request.wall,
            folder=request.folder,
            priority=request.priority,
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001 - surface storage errors as 400
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": message, "target_agent_id": request.agent_id, "delivery": "pending"}
