"""Read-only SiYuan Kernel API adapter."""

from __future__ import annotations

import re
from typing import Any

from .config import Settings
from .transport import JsonTransport


def _sql_text(value: str) -> str:
    return value.replace("'", "''")


def _excerpt(text: str, limit: int = 360) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


class SiyuanClient:
    def __init__(self, settings: Settings, transport: JsonTransport | None = None):
        self.settings = settings
        self.transport = transport or JsonTransport()

    def _call(self, path: str, payload: dict) -> Any:
        response = self.transport.post(
            f"{self.settings.siyuan_url}{path}", payload, self.settings.siyuan_token
        )
        if response.get("code") not in (None, 0):
            raise RuntimeError(response.get("msg") or "SiYuan request failed")
        return response.get("data")

    def search(self, query: str, limit: int = 8, notebook: str | None = None, tags: list[str] | None = None) -> list[dict]:
        limit = max(1, min(int(limit), 50))
        clauses = [f"content LIKE '%{_sql_text(query)}%'", "type IN ('d','h','p')"]
        if notebook:
            clauses.append(f"box = '{_sql_text(notebook)}'")
        for tag in tags or []:
            clauses.append(f"content LIKE '%#{_sql_text(tag.lstrip('#'))}#%'")
        statement = (
            "SELECT id, root_id, box, path, hpath, name, content, type, updated "
            f"FROM blocks WHERE {' AND '.join(clauses)} ORDER BY updated DESC LIMIT {limit}"
        )
        rows = self._call("/api/query/sql", {"stmt": statement}) or []
        return [self._normalize(row) for row in rows]

    def get(self, block_id: str) -> dict:
        content = self._call("/api/block/getBlockKramdown", {"id": block_id}) or {}
        rows = self._call(
            "/api/query/sql",
            {"stmt": "SELECT id, root_id, box, path, hpath, name, type, updated "
             f"FROM blocks WHERE id = '{_sql_text(block_id)}' LIMIT 1"},
        ) or []
        item = self._normalize(rows[0] if rows else {"id": block_id})
        item["content"] = content.get("kramdown", "") if isinstance(content, dict) else str(content)
        return item

    @staticmethod
    def _normalize(row: dict) -> dict:
        title = row.get("name") or row.get("content") or row.get("hpath") or row.get("id", "Untitled")
        return {
            "id": row.get("id", ""),
            "document_id": row.get("root_id") or row.get("id", ""),
            "title": _excerpt(title, 120),
            "notebook": row.get("box", ""),
            "path": row.get("hpath") or row.get("path", ""),
            "excerpt": _excerpt(row.get("content", "")),
            "type": row.get("type", ""),
            "updated": row.get("updated", ""),
        }
