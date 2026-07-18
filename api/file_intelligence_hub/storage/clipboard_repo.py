"""Persistence for the clipboard shelf.

AutoHotkey watches the Windows clipboard and POSTs entries here; the hub is the
durable memory. Clients never open this database directly -- only the server writes.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from typing import Any

JsonDict = dict[str, Any]
_SECRET_PATTERNS = (
    re.compile(r"\b(?:api[_-]?key|token|secret|password)\b", re.I),
    re.compile(r"\b[A-Za-z0-9_=-]{32,}\b"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
)


def _sha(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8", errors="ignore")).hexdigest()


def _secret_warning(body: str) -> bool:
    return any(pattern.search(body or "") for pattern in _SECRET_PATTERNS)


class ClipboardRepo:
    """Store the clipboard history: quick saves, pins, folders, tags, soft deletes."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def save_item(
        self,
        *,
        body: str,
        kind: str = "text",
        source_app: str | None = None,
        source_window: str | None = None,
        folder: str | None = None,
        tags: str | None = None,
        pinned: bool = False,
        mime_type: str | None = None,
        payload_json: str | None = None,
    ) -> JsonDict:
        content_hash = _sha(body)
        cursor = self.conn.execute(
            """
            INSERT INTO clipboard_items
                (body, kind, source_app, source_window, folder, tags, pinned, content_hash, mime_type, payload_json, secret_warning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (body, kind, source_app, source_window, folder, tags, int(pinned), content_hash, mime_type, payload_json or "{}", int(_secret_warning(body))),
        )
        self.conn.commit()
        return self.get_item(int(cursor.lastrowid))

    def get_item(self, item_id: int) -> JsonDict:
        row = self.conn.execute(
            "SELECT * FROM clipboard_items WHERE id = ?", (item_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"clipboard item not found: {item_id}")
        return self._item(row)

    def list_items(
        self,
        *,
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
    ) -> list[JsonDict]:
        clauses: list[str] = []
        params: list[object] = []
        if deleted is not None:
            clauses.append("deleted = ?")
            params.append(int(deleted))
        elif not include_deleted:
            clauses.append("deleted = 0")
        if folder:
            clauses.append("folder = ?")
            params.append(folder)
        if source_app:
            clauses.append("source_app = ?")
            params.append(source_app)
        if source_window:
            clauses.append("source_window = ?")
            params.append(source_window)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        if pinned is not None:
            clauses.append("pinned = ?")
            params.append(int(pinned))
        if tag:
            clauses.append("(',' || COALESCE(tags, '') || ',') LIKE ?")
            params.append(f"%,{tag},%")
        if date_from:
            clauses.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("created_at <= ?")
            params.append(date_to)
        if query:
            clauses.append("body LIKE ?")
            params.append(f"%{query}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(max(1, min(limit, 1000)))
        rows = self.conn.execute(
            f"SELECT * FROM clipboard_items{where} "
            "ORDER BY pinned DESC, created_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [self._item(row) for row in rows]

    def set_item_state(
        self,
        item_id: int,
        *,
        body: str | None = None,
        folder: str | None = None,
        tags: str | None = None,
        pinned: bool | None = None,
        deleted: bool | None = None,
    ) -> JsonDict:
        self.get_item(item_id)
        fields: list[str] = []
        params: list[object] = []
        if body is not None:
            fields.extend(["body = ?", "content_hash = ?", "secret_warning = ?"])
            params.extend([body, _sha(body), int(_secret_warning(body))])
        if folder is not None:
            fields.append("folder = ?")
            params.append(folder)
        if tags is not None:
            fields.append("tags = ?")
            params.append(tags)
        if pinned is not None:
            fields.append("pinned = ?")
            params.append(int(pinned))
        if deleted is not None:
            fields.append("deleted = ?")
            params.append(int(deleted))
        if fields:
            params.append(item_id)
            self.conn.execute(
                f"UPDATE clipboard_items SET {', '.join(fields)} WHERE id = ?", params
            )
            self.conn.commit()
        return self.get_item(item_id)

    def soft_delete(self, item_id: int) -> JsonDict:
        return self.set_item_state(item_id, deleted=True)

    def restore(self, item_id: int) -> JsonDict:
        return self.set_item_state(item_id, deleted=False)

    def mark_copied(self, item_id: int) -> JsonDict:
        self.get_item(item_id)
        self.conn.execute(
            "UPDATE clipboard_items SET copied_at = datetime('now') WHERE id = ?",
            (item_id,),
        )
        self.conn.commit()
        return self.get_item(item_id)

    def merge_items(self, item_ids: list[int], *, separator: str = "\n\n---\n\n", save: bool = False) -> JsonDict:
        items = [self.get_item(item_id) for item_id in item_ids]
        body = separator.join(item["body"] for item in items)
        result: JsonDict = {"body": body, "count": len(items), "source_ids": item_ids, "secret_warning": _secret_warning(body)}
        if save:
            result["item"] = self.save_item(body=body, kind="text", source_app="Top of Mind", folder="Merged", tags="merged")
        return result

    def duplicates(self, *, include_deleted: bool = False, limit: int = 100) -> list[JsonDict]:
        clause = "" if include_deleted else "WHERE deleted = 0"
        rows = self.conn.execute(
            f"""
            SELECT content_hash, COUNT(*) AS duplicate_count, MIN(created_at) AS first_seen, MAX(created_at) AS last_seen
            FROM clipboard_items {clause}
            GROUP BY content_hash
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC, last_seen DESC
            LIMIT ?
            """,
            (max(1, min(limit, 1000)),),
        ).fetchall()
        return [dict(row) for row in rows]

    def facets(self) -> JsonDict:
        def values(column: str) -> list[str]:
            rows = self.conn.execute(
                f"SELECT DISTINCT {column} AS value FROM clipboard_items WHERE {column} IS NOT NULL AND {column} != '' ORDER BY value LIMIT 250"
            ).fetchall()
            return [row["value"] for row in rows]

        tags: set[str] = set()
        for row in self.conn.execute("SELECT tags FROM clipboard_items WHERE tags IS NOT NULL AND tags != ''").fetchall():
            tags.update(tag.strip() for tag in row["tags"].split(",") if tag.strip())
        return {
            "source_apps": values("source_app"),
            "source_windows": values("source_window"),
            "folders": values("folder"),
            "kinds": values("kind"),
            "tags": sorted(tags),
        }

    def import_items(self, items: list[JsonDict]) -> int:
        count = 0
        for item in items:
            body = item.get("body")
            if not body:
                continue
            self.save_item(
                body=str(body),
                kind=str(item.get("kind", "text")),
                source_app=item.get("source_app"),
                source_window=item.get("source_window"),
                folder=item.get("folder"),
                tags=item.get("tags"),
                pinned=bool(item.get("pinned", False)),
                mime_type=item.get("mime_type"),
                payload_json=json.dumps(item.get("payload", {})),
            )
            count += 1
        return count

    @staticmethod
    def _item(row: sqlite3.Row) -> JsonDict:
        keys = set(row.keys())
        return {
            "id": row["id"],
            "body": row["body"],
            "kind": row["kind"],
            "source_app": row["source_app"],
            "source_window": row["source_window"],
            "folder": row["folder"],
            "tags": row["tags"],
            "pinned": bool(row["pinned"]),
            "deleted": bool(row["deleted"]),
            "copied_at": row["copied_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "content_hash": row["content_hash"] if "content_hash" in keys else _sha(row["body"]),
            "mime_type": row["mime_type"] if "mime_type" in keys else None,
            "payload": json.loads(row["payload_json"] or "{}") if "payload_json" in keys else {},
            "secret_warning": bool(row["secret_warning"]) if "secret_warning" in keys else _secret_warning(row["body"]),
        }
