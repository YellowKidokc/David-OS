"""Graph store — CRUD over kg_nodes, kg_edges, anti_edges, graph_index.

Purpose: Provide the data layer for the Second Brain graph system.
Every graph operation goes through here. No direct SQL outside this module.

Date: 2026-07-14
codex: graphs/store.py — graph CRUD layer for Second Brain
Status: TESTED (unit test in tests/test_graph_store.py)
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


@dataclass
class Node:
    id: str
    hub: str
    type: str
    label: str
    path: str | None = None
    summary: str | None = None
    chi_score: float | None = None
    props: dict = field(default_factory=dict)


@dataclass
class Edge:
    id: str
    src: str
    dst: str
    type: str
    force: str
    weight: float = 1.0
    evidence: list = field(default_factory=list)


@dataclass
class AntiEdge:
    id: str
    src: str
    dst: str
    status: str
    why_not: str | None = None
    evidence: list = field(default_factory=list)


@dataclass
class IndexEntry:
    node_id: str
    keywords: str
    one_liner: str


class GraphStore:
    """CRUD over the knowledge graph tables in the hub SQLite database."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    # ── Nodes ──────────────────────────────────────────────────────────

    def create_node(
        self,
        *,
        hub: str,
        type: str,
        label: str,
        path: str | None = None,
        summary: str | None = None,
        chi_score: float | None = None,
        props: dict | None = None,
        node_id: str | None = None,
    ) -> str:
        node_id = node_id or f"kg-{uuid.uuid4().hex[:16]}"
        self.conn.execute(
            """
            INSERT INTO kg_nodes (id, hub, type, label, path, summary, chi_score, props_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node_id,
                hub,
                type,
                label,
                path,
                summary,
                chi_score,
                json.dumps(props or {}),
            ),
        )
        self.conn.commit()
        return node_id

    def get_node(self, node_id: str) -> Node | None:
        row = self.conn.execute(
            "SELECT id, hub, type, label, path, summary, chi_score, props_json FROM kg_nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
        if not row:
            return None
        return Node(
            id=row["id"],
            hub=row["hub"],
            type=row["type"],
            label=row["label"],
            path=row["path"],
            summary=row["summary"],
            chi_score=row["chi_score"],
            props=json.loads(row["props_json"] or "{}"),
        )

    def list_nodes(self, hub: str | None = None, type: str | None = None) -> list[Node]:
        sql = "SELECT id, hub, type, label, path, summary, chi_score, props_json FROM kg_nodes WHERE 1=1"
        params: list = []
        if hub:
            sql += " AND hub = ?"
            params.append(hub)
        if type:
            sql += " AND type = ?"
            params.append(type)
        rows = self.conn.execute(sql, params).fetchall()
        return [
            Node(
                id=r["id"],
                hub=r["hub"],
                type=r["type"],
                label=r["label"],
                path=r["path"],
                summary=r["summary"],
                chi_score=r["chi_score"],
                props=json.loads(r["props_json"] or "{}"),
            )
            for r in rows
        ]

    def update_node(self, node_id: str, **fields) -> None:
        allowed = {"label", "path", "summary", "chi_score", "props"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        if "props" in updates:
            updates["props_json"] = json.dumps(updates.pop("props"))
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [node_id]
        self.conn.execute(f"UPDATE kg_nodes SET {set_clause} WHERE id = ?", values)
        self.conn.commit()

    def delete_node(self, node_id: str) -> None:
        self.conn.execute("DELETE FROM kg_edges WHERE src = ? OR dst = ?", (node_id, node_id))
        self.conn.execute("DELETE FROM anti_edges WHERE src = ? OR dst = ?", (node_id, node_id))
        self.conn.execute("DELETE FROM graph_index WHERE node_id = ?", (node_id,))
        self.conn.execute("DELETE FROM kg_nodes WHERE id = ?", (node_id,))
        self.conn.commit()

    # ── Edges ──────────────────────────────────────────────────────────

    def create_edge(
        self,
        *,
        src: str,
        dst: str,
        type: str,
        force: str,
        weight: float = 1.0,
        evidence: list | None = None,
        edge_id: str | None = None,
    ) -> str:
        edge_id = edge_id or f"e-{uuid.uuid4().hex[:16]}"
        self.conn.execute(
            """
            INSERT INTO kg_edges (id, src, dst, type, force, weight, evidence_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (edge_id, src, dst, type, force, weight, json.dumps(evidence or [])),
        )
        self.conn.commit()
        return edge_id

    def get_edges(self, node_id: str, direction: str = "both") -> list[Edge]:
        edges = []
        if direction in ("out", "both"):
            rows = self.conn.execute(
                "SELECT id, src, dst, type, force, weight, evidence_json FROM kg_edges WHERE src = ?",
                (node_id,),
            ).fetchall()
            edges.extend(
                Edge(
                    id=r["id"], src=r["src"], dst=r["dst"],
                    type=r["type"], force=r["force"], weight=r["weight"],
                    evidence=json.loads(r["evidence_json"] or "[]"),
                )
                for r in rows
            )
        if direction in ("in", "both"):
            rows = self.conn.execute(
                "SELECT id, src, dst, type, force, weight, evidence_json FROM kg_edges WHERE dst = ?",
                (node_id,),
            ).fetchall()
            edges.extend(
                Edge(
                    id=r["id"], src=r["src"], dst=r["dst"],
                    type=r["type"], force=r["force"], weight=r["weight"],
                    evidence=json.loads(r["evidence_json"] or "[]"),
                )
                for r in rows
            )
        return edges

    def delete_edge(self, edge_id: str) -> None:
        self.conn.execute("DELETE FROM kg_edges WHERE id = ?", (edge_id,))
        self.conn.commit()

    # ── Anti-edges ─────────────────────────────────────────────────────

    def create_anti_edge(
        self,
        *,
        src: str,
        dst: str,
        status: str,
        why_not: str | None = None,
        evidence: list | None = None,
        edge_id: str | None = None,
    ) -> str:
        edge_id = edge_id or f"ae-{uuid.uuid4().hex[:16]}"
        self.conn.execute(
            """
            INSERT INTO anti_edges (id, src, dst, status, why_not, evidence_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (edge_id, src, dst, status, why_not, json.dumps(evidence or [])),
        )
        self.conn.commit()
        return edge_id

    def get_anti_edges(self, node_id: str) -> list[AntiEdge]:
        rows = self.conn.execute(
            """
            SELECT id, src, dst, status, why_not, evidence_json
            FROM anti_edges
            WHERE src = ? OR dst = ?
            """,
            (node_id, node_id),
        ).fetchall()
        return [
            AntiEdge(
                id=r["id"], src=r["src"], dst=r["dst"],
                status=r["status"], why_not=r["why_not"],
                evidence=json.loads(r["evidence_json"] or "[]"),
            )
            for r in rows
        ]

    # ── Graph Index ────────────────────────────────────────────────────

    def upsert_index(self, node_id: str, keywords: str, one_liner: str) -> None:
        self.conn.execute(
            """
            INSERT INTO graph_index (node_id, keywords, one_liner, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(node_id) DO UPDATE SET
                keywords = excluded.keywords,
                one_liner = excluded.one_liner,
                updated_at = datetime('now')
            """,
            (node_id, keywords, one_liner),
        )
        self.conn.commit()

    def search_index(self, query: str) -> list[IndexEntry]:
        pattern = f"%{query}%"
        rows = self.conn.execute(
            """
            SELECT node_id, keywords, one_liner
            FROM graph_index
            WHERE keywords LIKE ? OR one_liner LIKE ?
            ORDER BY one_liner
            """,
            (pattern, pattern),
        ).fetchall()
        return [IndexEntry(node_id=r["node_id"], keywords=r["keywords"], one_liner=r["one_liner"]) for r in rows]

    # ── Import / Export ────────────────────────────────────────────────

    def export_hub(self, hub: str) -> dict:
        """Export all nodes, edges, and anti-edges for a given hub as JSON-serializable dict."""
        nodes = self.list_nodes(hub=hub)
        edges = []
        anti_edges = []
        for node in nodes:
            edges.extend(self.get_edges(node.id))
            anti_edges.extend(self.get_anti_edges(node.id))
        return {
            "hub": hub,
            "nodes": [
                {
                    "id": n.id, "hub": n.hub, "type": n.type, "label": n.label,
                    "path": n.path, "summary": n.summary, "chi_score": n.chi_score,
                    "props": n.props,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id, "src": e.src, "dst": e.dst, "type": e.type,
                    "force": e.force, "weight": e.weight, "evidence": e.evidence,
                }
                for e in edges
            ],
            "anti_edges": [
                {
                    "id": ae.id, "src": ae.src, "dst": ae.dst, "status": ae.status,
                    "why_not": ae.why_not, "evidence": ae.evidence,
                }
                for ae in anti_edges
            ],
        }

    def import_hub(self, data: dict) -> None:
        """Import nodes, edges, and anti-edges from a JSON-serializable dict."""
        for n in data.get("nodes", []):
            self.create_node(
                hub=n["hub"], type=n["type"], label=n["label"],
                path=n.get("path"), summary=n.get("summary"),
                chi_score=n.get("chi_score"), props=n.get("props", {}),
                node_id=n["id"],
            )
        for e in data.get("edges", []):
            self.create_edge(
                src=e["src"], dst=e["dst"], type=e["type"],
                force=e["force"], weight=e.get("weight", 1.0),
                evidence=e.get("evidence", []), edge_id=e["id"],
            )
        for ae in data.get("anti_edges", []):
            self.create_anti_edge(
                src=ae["src"], dst=ae["dst"], status=ae["status"],
                why_not=ae.get("why_not"), evidence=ae.get("evidence", []),
                edge_id=ae["id"],
            )

    # ── Helpers ────────────────────────────────────────────────────────

    def count_nodes(self, hub: str | None = None) -> int:
        sql = "SELECT COUNT(*) FROM kg_nodes"
        params = ()
        if hub:
            sql += " WHERE hub = ?"
            params = (hub,)
        row = self.conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    def count_edges(self, hub: str | None = None) -> int:
        if hub is None:
            row = self.conn.execute("SELECT COUNT(*) FROM kg_edges").fetchone()
            return row[0] if row else 0
        row = self.conn.execute(
            """
            SELECT COUNT(*) FROM kg_edges e
            JOIN kg_nodes n ON e.src = n.id
            WHERE n.hub = ?
            """,
            (hub,),
        ).fetchone()
        return row[0] if row else 0

    def node_exists(self, node_id: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM kg_nodes WHERE id = ?", (node_id,)).fetchone()
        return row is not None
