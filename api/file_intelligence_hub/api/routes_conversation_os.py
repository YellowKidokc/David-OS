"""Conversation OS control-plane routes for agent presence, re-entry, arrivals, and branches."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from file_intelligence_hub.storage.conversation_os_repo import ConversationOSRepo, DEFAULT_CONTEXT_SCOPE, DEFAULT_PERMISSIONS, DEFAULT_RESPONSE_MODE
from file_intelligence_hub.storage.db import Database

DEFAULT_DB_PATH = Path(os.environ.get("FIHUB_DB_PATH", ".data/file-intelligence-hub.sqlite3"))
router = APIRouter(prefix="/conversation-os", tags=["conversation-os"])


class ConversationRequest(BaseModel):
    conversation_id: str = "main"
    title: str = "Main"
    status: str = "active"


class ConversationStateRequest(BaseModel):
    conversation_id: str = "main"
    active_project: str | None = None
    current_objective: str | None = None
    canonical_definitions: list[object] | None = None
    accepted_decisions: list[object] | None = None
    rejected_options: list[object] | None = None
    unresolved_questions: list[object] | None = None
    recent_summary: str | None = None
    required_next_action: str | None = None


class ArrivalRequest(BaseModel):
    conversation_id: str = "main"
    agent_id: str
    message_id: int | None = None
    topic: str
    contribution_type: str = "new_contribution"
    priority: str = "normal"
    novelty: float = Field(default=0.5, ge=0, le=1)
    summary: str = ""
    payload: dict[str, object] = Field(default_factory=dict)


class ArrivalStateRequest(BaseModel):
    state: str


class InviteRequest(BaseModel):
    conversation_id: str = "main"
    agent_id: str
    joined_at_message_id: int | None = None
    context_scope: str = DEFAULT_CONTEXT_SCOPE
    response_mode: str = DEFAULT_RESPONSE_MODE
    status: str = "listening"
    permissions: dict[str, object] = Field(default_factory=lambda: DEFAULT_PERMISSIONS.copy())


class BranchRequest(BaseModel):
    parent_conversation_id: str = "main"
    branched_from_message_id: int | None = None
    title: str
    participants: list[str] = Field(default_factory=list)
    shared_state_mode: str = "snapshot"
    merge_back_policy: str = "manual"


class ContextGrantRequest(BaseModel):
    conversation_id: str = "main"
    agent_id: str
    scope: str = DEFAULT_CONTEXT_SCOPE
    sources: list[dict[str, object]] = Field(default_factory=list)
    expires_at: str | None = None


class ProposalRequest(BaseModel):
    conversation_id: str = "main"
    agent_id: str
    body: str
    mode: str = DEFAULT_RESPONSE_MODE
    metadata: dict[str, object] = Field(default_factory=dict)


class DecisionRequest(BaseModel):
    conversation_id: str = "main"
    title: str
    status: str = "accepted"
    rationale: str = ""
    source: str = "user"


class ReentryRequest(BaseModel):
    conversation_id: str = "main"
    agent_id: str
    inactive_hours: float = Field(ge=0)
    last_message_count: int = Field(default=10, ge=1, le=50)


def _repo() -> ConversationOSRepo:
    db = Database(DEFAULT_DB_PATH)
    return ConversationOSRepo(db.conn)


@router.get("/conversations")
def list_conversations() -> dict[str, object]:
    return {"conversations": _repo().list_conversations()}


@router.post("/conversations")
def ensure_conversation(request: ConversationRequest) -> dict[str, object]:
    return {"conversation": _repo().ensure_conversation(request.conversation_id, title=request.title, status=request.status)}


@router.get("/state")
def get_state(conversation_id: str = "main") -> dict[str, object]:
    return {"state": _repo().get_state(conversation_id)}


@router.put("/state")
def upsert_state(request: ConversationStateRequest) -> dict[str, object]:
    return {"state": _repo().upsert_state(**request.model_dump())}


@router.get("/arrivals")
def list_arrivals(conversation_id: str = "main", include_archived: bool = False) -> dict[str, object]:
    return {"arrivals": _repo().list_arrivals(conversation_id, include_archived=include_archived)}


@router.post("/arrivals")
def create_arrival(request: ArrivalRequest) -> dict[str, object]:
    return {"arrival": _repo().create_arrival(**request.model_dump())}


@router.patch("/arrivals/{arrival_id}")
def set_arrival_state(arrival_id: int, request: ArrivalStateRequest) -> dict[str, object]:
    try:
        return {"arrival": _repo().set_arrival_state(arrival_id, request.state)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/memberships")
def list_memberships(conversation_id: str = "main") -> dict[str, object]:
    return {"memberships": _repo().list_memberships(conversation_id)}


@router.post("/memberships/invite")
def invite_agent(request: InviteRequest) -> dict[str, object]:
    return {"membership": _repo().invite_agent(**request.model_dump())}


@router.get("/branches")
def list_branches(parent_conversation_id: str = "main") -> dict[str, object]:
    return {"branches": _repo().list_branches(parent_conversation_id)}


@router.post("/branches")
def create_branch(request: BranchRequest) -> dict[str, object]:
    return {"branch": _repo().create_branch(**request.model_dump())}


@router.post("/context-grants")
def create_context_grant(request: ContextGrantRequest) -> dict[str, object]:
    return {"grant": _repo().create_context_grant(**request.model_dump())}


@router.get("/proposals")
def list_proposals(conversation_id: str = "main") -> dict[str, object]:
    return {"proposals": _repo().list_proposals(conversation_id)}


@router.post("/proposals")
def create_proposal(request: ProposalRequest) -> dict[str, object]:
    return {"proposal": _repo().create_proposal(**request.model_dump())}


@router.get("/decisions")
def list_decisions(conversation_id: str = "main") -> dict[str, object]:
    return {"decisions": _repo().list_decisions(conversation_id)}


@router.post("/decisions")
def create_decision(request: DecisionRequest) -> dict[str, object]:
    return {"decision": _repo().create_decision(**request.model_dump())}


@router.post("/reentry-packets")
def create_reentry_packet(request: ReentryRequest) -> dict[str, object]:
    return {"packet": _repo().create_reentry_packet(**request.model_dump())}
