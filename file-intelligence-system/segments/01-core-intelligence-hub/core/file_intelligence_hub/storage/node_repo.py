"""Persistence for node heartbeats and repair logs."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

JsonDict = dict[str, Any]


def _dump(value: JsonDict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _load(value: str) -> JsonDict:
    return json.loads(value)


class NodeRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def heartbeat(self, node: JsonDict) -> JsonDict:
        self.conn.execute(
            """
            INSERT INTO nodes (node_id, node_role, capabilities_json, status, resource_json, local_queue_depth, version, build_signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(node_id) DO UPDATE SET
                node_role = excluded.node_role,
                capabilities_json = excluded.capabilities_json,
                status = excluded.status,
                resource_json = excluded.resource_json,
                local_queue_depth = excluded.local_queue_depth,
                version = excluded.version,
                build_signature = excluded.build_signature,
                last_seen = datetime('now')
            """,
            (
                node["node_id"], node["node_role"], _dump(node["capabilities"]), node["status"],
                _dump(node["resources"]), int(node.get("local_queue_depth", 0)), node["version"], node["build_signature"],
            ),
        )
        self.conn.commit()
        return self.get_node(node["node_id"])

    def get_node(self, node_id: str) -> JsonDict:
        row = self.conn.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,)).fetchone()
        if row is None:
            raise KeyError(f"node not found: {node_id}")
        return self._node(row)

    def list_nodes(self) -> list[JsonDict]:
        rows = self.conn.execute("SELECT * FROM nodes ORDER BY node_id").fetchall()
        return [self._node(row) for row in rows]

    def log_repair(self, entry: JsonDict) -> JsonDict:
        cur = self.conn.execute(
            """
            INSERT INTO repair_log (repair_type, scope, transfer_mode, artifact_path, outcome, error, source_node)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry["repair_type"], entry["scope"], entry["transfer_mode"], entry["artifact_path"],
                entry["outcome"], entry.get("error"), entry.get("source_node"),
            ),
        )
        self.conn.commit()
        return self.get_repair_log(int(cur.lastrowid))

    def get_repair_log(self, repair_id: int) -> JsonDict:
        row = self.conn.execute("SELECT * FROM repair_log WHERE id = ?", (repair_id,)).fetchone()
        if row is None:
            raise KeyError(f"repair log not found: {repair_id}")
        return {
            "id": row["id"], "repair_type": row["repair_type"], "scope": row["scope"],
            "transfer_mode": row["transfer_mode"], "artifact_path": row["artifact_path"],
            "outcome": row["outcome"], "error": row["error"], "source_node": row["source_node"],
            "created_at": row["created_at"],
        }

    def list_repairs(self) -> list[JsonDict]:
        rows = self.conn.execute("SELECT * FROM repair_log ORDER BY id").fetchall()
        return [self.get_repair_log(row["id"]) for row in rows]

    @staticmethod
    def _node(row: sqlite3.Row) -> JsonDict:
        return {
            "node_id": row["node_id"], "node_role": row["node_role"], "capabilities": _load(row["capabilities_json"]),
            "status": row["status"], "last_seen": row["last_seen"], "resources": _load(row["resource_json"]),
            "local_queue_depth": row["local_queue_depth"], "version": row["version"], "build_signature": row["build_signature"],
        }
