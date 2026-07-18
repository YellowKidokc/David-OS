"""Clipboard shelf API: durable clipboard history, pins, folders, tags."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from file_intelligence_hub.storage.clipboard_repo import ClipboardRepo
from file_intelligence_hub.storage.db import Database

DEFAULT_DB_PATH = Path(os.environ.get("FIHUB_DB_PATH", ".data/file-intelligence-hub.sqlite3"))
router = APIRouter(prefix="/clipboard", tags=["clipboard"])


class ClipboardItemRequest(BaseModel):
    body: str
    kind: str = "text"
    source_app: str | None = None
    source_window: str | None = None
    folder: str | None = None
    tags: str | None = None
    pinned: bool = False
    mime_type: str | None = None
    payload_json: str | None = None


class ClipboardItemStateRequest(BaseModel):
    body: str | None = None
    folder: str | None = None
    tags: str | None = None
    pinned: bool | None = None
    deleted: bool | None = None


class ClipboardImportRequest(BaseModel):
    items: list[dict[str, object]] = Field(default_factory=list)


class ClipboardMergeRequest(BaseModel):
    item_ids: list[int] = Field(default_factory=list)
    separator: str = "\n\n---\n\n"
    save: bool = False


class ClipboardExportRequest(BaseModel):
    item_ids: list[int] = Field(default_factory=list)
    format: str = "json"
    include_deleted: bool = False


class ClipboardRetentionRequest(BaseModel):
    days: int = Field(default=90, ge=1, le=3650)
    include_pinned: bool = False


def _repo() -> ClipboardRepo:
    db = Database(DEFAULT_DB_PATH)
    return ClipboardRepo(db.conn)


@router.post("/items")
def save_item(request: ClipboardItemRequest) -> dict[str, object]:
    return {"item": _repo().save_item(**request.model_dump())}


@router.post("/save")
def save_item_alias(request: ClipboardItemRequest) -> dict[str, object]:
    return save_item(request)


@router.get("/items")
def list_items(
    folder: str | None = None,
    pinned: bool | None = None,
    query: str | None = None,
    source_app: str | None = None,
    source_window: str | None = None,
    tag: str | None = None,
    kind: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    include_deleted: bool = False,
    deleted: bool | None = None,
    limit: int = 100,
) -> dict[str, object]:
    return {
        "items": _repo().list_items(
            folder=folder,
            pinned=pinned,
            query=query,
            source_app=source_app,
            source_window=source_window,
            tag=tag,
            kind=kind,
            date_from=date_from,
            date_to=date_to,
            include_deleted=include_deleted,
            deleted=deleted,
            limit=limit,
        )
    }


@router.get("/facets")
def facets() -> dict[str, object]:
    return {"facets": _repo().facets()}


@router.get("/duplicates")
def duplicates(include_deleted: bool = False, limit: int = 100) -> dict[str, object]:
    return {"duplicates": _repo().duplicates(include_deleted=include_deleted, limit=limit)}


@router.patch("/items/{item_id}")
def set_item_state(item_id: int, request: ClipboardItemStateRequest) -> dict[str, object]:
    try:
        return {"item": _repo().set_item_state(item_id, **request.model_dump())}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/items/{item_id}")
def delete_item(item_id: int) -> dict[str, object]:
    try:
        return {"item": _repo().soft_delete(item_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/items/{item_id}/restore")
def restore_item(item_id: int) -> dict[str, object]:
    try:
        return {"item": _repo().restore(item_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/items/{item_id}/copy")
def copy_item(item_id: int) -> dict[str, object]:
    try:
        return {"item": _repo().mark_copied(item_id), "bridge_action": "copy_to_windows_clipboard"}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/merge")
def merge_items(request: ClipboardMergeRequest) -> dict[str, object]:
    if len(request.item_ids) < 2:
        raise HTTPException(status_code=400, detail="select at least two clipboard items")
    return {"merge": _repo().merge_items(request.item_ids, separator=request.separator, save=request.save)}


@router.post("/export", response_model=None)
def export_items(request: ClipboardExportRequest | None = None):
    request = request or ClipboardExportRequest()
    repo = _repo()
    items = (
        [repo.get_item(item_id) for item_id in request.item_ids]
        if request.item_ids
        else repo.list_items(include_deleted=request.include_deleted, limit=100000)
    )
    if request.format == "markdown":
        body = "\n\n".join(
            f"<!-- clipboard:{item['id']} created:{item['created_at']} -->\n\n{item['body']}"
            for item in items
        )
        return Response(content=body, media_type="text/markdown")
    if request.format == "text":
        body = "\n\n---\n\n".join(item["body"] for item in items)
        return Response(content=body, media_type="text/plain")
    return {"items": items}


@router.post("/import")
def import_items(request: ClipboardImportRequest) -> dict[str, object]:
    return {"stored": _repo().import_items(request.items)}


@router.get("/retention")
def get_retention() -> dict[str, object]:
    return {"retention": {"days": int(os.environ.get("CLIPBOARD_RETENTION_DAYS", "90")), "include_pinned": False}}


@router.post("/retention")
def set_retention(request: ClipboardRetentionRequest) -> dict[str, object]:
    return {"retention": request.model_dump(), "note": "Retention preference accepted by the control plane; scheduled pruning is review-gated."}
