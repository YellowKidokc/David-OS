"""OpenAI-compatible local router endpoints for Mattermost Agents.

Refactored July 14, 2026: Replaced hardcoded DeepSeek forwarding with
pluggable provider router (services/provider_router.py). Any OpenAI-compatible
endpoint (Ollama, LM Studio, OpenAI, DeepSeek, etc.) works via config/providers.json.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from file_intelligence_hub.storage.db import Database
from file_intelligence_hub.storage.top_of_mind_repo import TopOfMindRepo
from file_intelligence_hub.services.provider_router import send, get_registry

DEFAULT_DB_PATH = Path(os.environ.get("FIHUB_DB_PATH", ".data/file-intelligence-hub.sqlite3"))
DEFAULT_MODEL = os.environ.get("TOP_OF_MIND_ROUTER_MODEL", "top-of-mind-router")

router = APIRouter(prefix="/v1", tags=["openai-compatible"])


@dataclass(frozen=True)
class Persona:
    id: str
    label: str
    aliases: tuple[str, ...]
    instructions: str


PERSONAS: dict[str, Persona] = {
    "kimi": Persona(
        id="kimi",
        label="Kimi",
        aliases=("kimi", "kimmy", "k"),
        instructions=(
            "You are Kimi inside David's Mattermost AI Crew. Act as the default coordinator: "
            "short operational answers, clear next actions, and careful scope control."
        ),
    ),
    "codex": Persona(
        id="codex",
        label="Codex",
        aliases=("codex", "codex-cli", "code", "c"),
        instructions=(
            "You are Codex inside David's Mattermost AI Crew. Focus on code, files, APIs, "
            "tests, shell commands, and verification. Be explicit about exact files and commands."
        ),
    ),
    "fabel": Persona(
        id="fabel",
        label="Fabel",
        aliases=("fabel", "fable", "fabel-cli", "f"),
        instructions=(
            "You are Fabel inside David's Mattermost AI Crew. Focus on site pipelines, content "
            "structure, math translation, workflow simplification, and buildable scripts."
        ),
    ),
    "gemini": Persona(
        id="gemini",
        label="Gemini",
        aliases=("gemini", "g"),
        instructions=(
            "You are Gemini inside David's Mattermost AI Crew. Focus on broad verification, "
            "integration checks, visual QA, and catching hidden assumptions."
        ),
    ),
    "gpt": Persona(
        id="gpt",
        label="GPT",
        aliases=("gpt", "gpt-5.5", "gpt-55", "gpt-5.4", "gpt-54"),
        instructions=(
            "You are GPT inside David's Mattermost AI Crew. Focus on general reasoning, planning, "
            "summaries, and translating fuzzy requirements into executable work."
        ),
    ),
    "opus": Persona(
        id="opus",
        label="Opus",
        aliases=("opus", "4.8", "4.7", "opus-48", "opus-47"),
        instructions=(
            "You are Opus inside David's Mattermost AI Crew. Focus on deep reasoning, canon, "
            "editorial judgment, theorem-level clarity, and high-stakes review."
        ),
    ),
    "sonnet": Persona(
        id="sonnet",
        label="Sonnet",
        aliases=("sonnet", "sonnet-5"),
        instructions=(
            "You are Sonnet inside David's Mattermost AI Crew. Focus on balanced implementation, "
            "writing polish, and practical tradeoffs."
        ),
    ),
    "anti-gravity": Persona(
        id="anti-gravity",
        label="Anti Gravity",
        aliases=("anti-gravity", "antigravity", "ag"),
        instructions=(
            "You are Anti Gravity inside David's Mattermost AI Crew. Focus on UI, visual layout, "
            "browser behavior, platform packaging, and user-facing polish."
        ),
    ),
    "hakui": Persona(
        id="hakui",
        label="Hakui",
        aliases=("hakui", "hakui-4.5", "h"),
        instructions=(
            "You are Hakui inside David's Mattermost AI Crew. Focus on fast lightweight answers, "
            "quick checks, and minimal operational friction."
        ),
    ),
}
ALIAS_TO_PERSONA: dict[str, Persona] = {
    alias.lower(): persona
    for persona in PERSONAS.values()
    for alias in persona.aliases
}


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: list[ChatMessage] = Field(default_factory=list)
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: dict[str, Any] | None = None


class ResponseInputItem(BaseModel):
    role: str | None = None
    content: str | list[dict[str, Any]] | None = None


class ResponsesRequest(BaseModel):
    model: str = DEFAULT_MODEL
    input: str | list[ResponseInputItem] | list[dict[str, Any]] | None = None
    instructions: str | None = None
    stream: bool = False
    metadata: dict[str, Any] | None = None


def _repo() -> TopOfMindRepo:
    db = Database(DEFAULT_DB_PATH)
    return TopOfMindRepo(db.conn)


def _content_to_text(content: str | list[dict[str, Any]] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict):
            text = item.get("text") or item.get("content")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)


def _latest_user_message(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return _content_to_text(message.content).strip()
    for message in reversed(messages):
        text = _content_to_text(message.content).strip()
        if text:
            return text
    return ""


def _target_from_text(text: str) -> tuple[Persona | None, str, str]:
    stripped = text.strip()
    lowered = stripped.lower()
    for alias, persona in sorted(ALIAS_TO_PERSONA.items(), key=lambda item: len(item[0]), reverse=True):
        candidates = (f"/{alias}", f"@{alias}", f"{alias}:")
        for token in candidates:
            if lowered == token:
                return persona, "", f"prompt-prefix:{token}"
            if lowered.startswith(token + " "):
                return persona, stripped[len(token):].strip(), f"prompt-prefix:{token}"
            if token.endswith(":") and lowered.startswith(token):
                return persona, stripped[len(token):].strip(), f"prompt-prefix:{token}"
    return None, stripped, "default"


def _metadata_values(metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("persona", "target", "agent", "channel", "channel_name", "channel_display_name", "team_name"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    return values


def _select_persona(messages: list[ChatMessage], metadata: dict[str, Any] | None) -> tuple[Persona, list[ChatMessage], str]:
    prompt = _latest_user_message(messages)
    persona, cleaned_prompt, reason = _target_from_text(prompt)
    routed_messages = list(messages)
    if persona:
        routed_messages = _replace_latest_user_message(routed_messages, cleaned_prompt or prompt)
    else:
        for value in _metadata_values(metadata or {}):
            normalized = value.lower().replace("_", "-").replace(" ", "-")
            for alias, candidate in ALIAS_TO_PERSONA.items():
                if alias == normalized or alias in normalized:
                    persona = candidate
                    reason = f"metadata:{value}"
                    break
            if persona:
                break
    if not persona:
        persona = PERSONAS["kimi"]
        reason = "default:kimi"
    return persona, _add_persona_system_message(routed_messages, persona), reason


def _replace_latest_user_message(messages: list[ChatMessage], content: str) -> list[ChatMessage]:
    replaced = list(messages)
    for index in range(len(replaced) - 1, -1, -1):
        if replaced[index].role == "user":
            original = replaced[index]
            replaced[index] = ChatMessage(role=original.role, content=content, name=original.name)
            return replaced
    return replaced


def _add_persona_system_message(messages: list[ChatMessage], persona: Persona) -> list[ChatMessage]:
    safety = (
        "You are behind the Top of Mind router. Do not claim you edited files, ran commands, "
        "or contacted services unless the user provided evidence. For destructive actions, "
        "credential handling, or irreversible changes, require explicit operator approval. "
        "Keep responses concise and operational."
    )
    return [ChatMessage(role="system", content=f"{persona.instructions}\n\n{safety}"), *messages]


def _messages_to_dicts(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    return [
        {"role": m.role, "content": _content_to_text(m.content)}
        for m in messages
        if _content_to_text(m.content).strip()
    ]


def _build_router_reply(
    messages: list[ChatMessage],
    model: str,
    request_metadata: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    persona, routed_messages, route_reason = _select_persona(messages, request_metadata)
    prompt = _latest_user_message(messages)
    repo = _repo()
    repo.upsert_source(
        "mattermost-ai",
        label="Mattermost AI",
        kind="mattermost",
        priority=3,
        metadata={"model": model, "gateway": "openai-compatible"},
    )
    stored = repo.post_message(
        source_id="mattermost-ai",
        source_label="Mattermost AI",
        role="user",
        body=prompt or "[empty prompt]",
        wall="ai-crew",
        folder="Mattermost",
        metadata={
            "model": model,
            "persona": persona.id,
            "persona_label": persona.label,
            "route_reason": route_reason,
            "request_metadata": request_metadata or {},
            "messages": [message.model_dump() for message in messages],
        },
    )

    # ── Provider routing (replaces hardcoded DeepSeek) ────────────────
    content = ""
    provider_metadata: dict[str, Any] = {
        "provider": "none",
        "persona": persona.id,
        "persona_label": persona.label,
        "route_reason": route_reason,
    }

    registry = get_registry()
    default_provider = registry.default_provider()

    if default_provider:
        try:
            content, provider_metadata = send(
                _messages_to_dicts(routed_messages),
                model=model if model != DEFAULT_MODEL else None,
                fallback=True,
            )
        except RuntimeError as exc:
            provider_metadata = {
                "provider": default_provider.id if default_provider else "none",
                "error": str(exc),
                "persona": persona.id,
                "persona_label": persona.label,
                "route_reason": route_reason,
            }
            content = (
                "Top of Mind router received the request, but the provider chain failed. "
                f"Router error: {exc}"
            )
    else:
        content = (
            "Top of Mind router is online. "
            "I received the request and saved it into the AI Crew stream. "
            "Add a provider via POST /providers to enable real downstream answers."
        )
        if prompt:
            clipped = prompt.replace("\n", " ").strip()
            if len(clipped) > 240:
                clipped = clipped[:237] + "..."
            content += f"\n\nReceived: {clipped}"

    reply = repo.post_message(
        source_id="top-of-mind-router",
        source_label="Top of Mind Router",
        role="assistant",
        body=content,
        wall="ai-crew",
        folder="Mattermost",
        metadata={"request_message_id": stored["id"], "model": model, **provider_metadata},
    )
    return content, {"request_message_id": stored["id"], "reply_message_id": reply["id"], **provider_metadata}


def _chat_payload(content: str, model: str, metadata: dict[str, Any]) -> dict[str, Any]:
    created = int(time.time())
    prompt_tokens = max(1, len(content.split()) // 2)
    completion_tokens = max(1, len(content.split()))
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "top_of_mind": metadata,
    }


async def _stream_chat(content: str, model: str) -> AsyncIterator[str]:
    stream_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    for word in content.split(" "):
        chunk = {
            "id": stream_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": word + " "}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(chunk, separators=(',', ':'))}\n\n"
    done = {
        "id": stream_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(done, separators=(',', ':'))}\n\n"
    yield "data: [DONE]\n\n"


@router.get("/models")
def list_models() -> dict[str, Any]:
    registry = get_registry()
    providers = registry.list()
    models = []
    for p in providers:
        if p.enabled:
            models.append({
                "id": f"{p.id}/{p.model}" if p.model != "auto" else p.id,
                "object": "model",
                "created": 0,
                "owned_by": p.id,
            })
    if not models:
        models.append({
            "id": DEFAULT_MODEL,
            "object": "model",
            "created": 0,
            "owned_by": "top-of-mind",
        })
    return {"object": "list", "data": models}


@router.get("/top-of-mind/personas")
def list_personas() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": persona.id,
                "label": persona.label,
                "aliases": list(persona.aliases),
            }
            for persona in PERSONAS.values()
        ],
    }


@router.post("/chat/completions", response_model=None)
def chat_completions(request: ChatCompletionRequest):
    content, metadata = _build_router_reply(
        request.messages,
        request.model or DEFAULT_MODEL,
        request.metadata or {},
    )
    if request.stream:
        return StreamingResponse(_stream_chat(content, request.model or DEFAULT_MODEL), media_type="text/event-stream")
    return _chat_payload(content, request.model or DEFAULT_MODEL, metadata)


@router.post("/responses", response_model=None)
def responses(request: ResponsesRequest):
    messages = _response_input_to_messages(request)
    content, metadata = _build_router_reply(messages, request.model or DEFAULT_MODEL, request.metadata or {})
    if request.stream:
        return StreamingResponse(_stream_chat(content, request.model or DEFAULT_MODEL), media_type="text/event-stream")
    return {
        "id": f"resp_{uuid.uuid4().hex}",
        "object": "response",
        "created_at": int(time.time()),
        "status": "completed",
        "model": request.model or DEFAULT_MODEL,
        "output": [
            {
                "id": f"msg_{uuid.uuid4().hex}",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": content}],
            }
        ],
        "output_text": content,
        "top_of_mind": metadata,
    }


def _response_input_to_messages(request: ResponsesRequest) -> list[ChatMessage]:
    messages: list[ChatMessage] = []
    if request.instructions:
        messages.append(ChatMessage(role="system", content=request.instructions))
    if isinstance(request.input, str):
        messages.append(ChatMessage(role="user", content=request.input))
    elif isinstance(request.input, list):
        for item in request.input:
            if isinstance(item, ResponseInputItem):
                messages.append(ChatMessage(role=item.role or "user", content=item.content))
            elif isinstance(item, dict):
                messages.append(ChatMessage(role=str(item.get("role") or "user"), content=item.get("content")))
    return messages
