"""Durable conversation operating-system state.

This repository keeps agent presence, context permissions, arrivals, branches,
response proposals, decisions, and re-entry packets out of React-local state.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

JsonDict = dict[str, Any]

DEFAULT_CONTEXT_SCOPE = "recent_context"
DEFAULT_RESPONSE_MODE = "silent_advisor"
DEFAULT_PERMISSIONS = {
    "can_read_current_conversation": True,
    "can_read_prior_history": False,
    "can_read_files": False,
    "can_call_apis": False,
    "can_send_visible_responses": False,
    "can_advise_silently": True,
    "can_invite_other_agents": False,
    "can_create_branches": False,
    "can_modify_files": False,
    "can_issue_commands": False,
    "requires_approval": True,
}


def _dump(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _load(value: str | None, default: object) -> object:
    if not value:
        return default
    return json.loads(value)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ConversationOSRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def ensure_conversation(self, conversation_id: str = "main", *, title: str = "Main", status: str = "active") -> JsonDict:
        self.conn.execute(
            """
            INSERT INTO conversations (conversation_id, title, status, metadata_json)
            VALUES (?, ?, ?, '{}')
            ON CONFLICT(conversation_id) DO UPDATE SET title = excluded.title, status = excluded.status
            """,
            (conversation_id, title, status),
        )
        self.conn.commit()
        return self.get_conversation(conversation_id)

    def get_conversation(self, conversation_id: str) -> JsonDict:
        row = self.conn.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,)).fetchone()
        if row is None:
            raise KeyError(f"conversation not found: {conversation_id}")
        return self._conversation(row)

    def list_conversations(self) -> list[JsonDict]:
        rows = self.conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC, title ASC").fetchall()
        return [self._conversation(row) for row in rows]

    def upsert_state(self, conversation_id: str = "main", **state: object) -> JsonDict:
        self.ensure_conversation(conversation_id)
        current = self.get_state(conversation_id)
        next_state = {**current, **{key: value for key, value in state.items() if value is not None}}
        self.conn.execute(
            """
            INSERT INTO conversation_states (
                conversation_id, active_project, current_objective, canonical_definitions_json,
                accepted_decisions_json, rejected_options_json, unresolved_questions_json,
                recent_summary, required_next_action, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                active_project = excluded.active_project,
                current_objective = excluded.current_objective,
                canonical_definitions_json = excluded.canonical_definitions_json,
                accepted_decisions_json = excluded.accepted_decisions_json,
                rejected_options_json = excluded.rejected_options_json,
                unresolved_questions_json = excluded.unresolved_questions_json,
                recent_summary = excluded.recent_summary,
                required_next_action = excluded.required_next_action,
                updated_at = excluded.updated_at
            """,
            (
                conversation_id,
                next_state.get("active_project", ""),
                next_state.get("current_objective", ""),
                _dump(next_state.get("canonical_definitions", [])),
                _dump(next_state.get("accepted_decisions", [])),
                _dump(next_state.get("rejected_options", [])),
                _dump(next_state.get("unresolved_questions", [])),
                next_state.get("recent_summary", ""),
                next_state.get("required_next_action", ""),
                _now(),
            ),
        )
        self.conn.commit()
        return self.get_state(conversation_id)

    def get_state(self, conversation_id: str = "main") -> JsonDict:
        row = self.conn.execute("SELECT * FROM conversation_states WHERE conversation_id = ?", (conversation_id,)).fetchone()
        if row is None:
            return {
                "conversation_id": conversation_id,
                "active_project": "",
                "current_objective": "",
                "canonical_definitions": [],
                "accepted_decisions": [],
                "rejected_options": [],
                "unresolved_questions": [],
                "recent_summary": "",
                "required_next_action": "",
            }
        return self._state(row)

    def create_arrival(self, *, agent_id: str, topic: str, contribution_type: str = "new_contribution", priority: str = "normal", novelty: float = 0.5, conversation_id: str = "main", message_id: int | None = None, summary: str = "", payload: JsonDict | None = None) -> JsonDict:
        self.ensure_conversation(conversation_id)
        cursor = self.conn.execute(
            """
            INSERT INTO agent_arrivals (conversation_id, agent_id, message_id, topic, contribution_type, priority, novelty, state, summary, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'NEW', ?, ?)
            """,
            (conversation_id, agent_id, message_id, topic, contribution_type, priority, novelty, summary, _dump(payload or {})),
        )
        self.conn.commit()
        return self.get_arrival(int(cursor.lastrowid))

    def list_arrivals(self, conversation_id: str = "main", *, include_archived: bool = False) -> list[JsonDict]:
        clause = "conversation_id = ?" + ("" if include_archived else " AND state NOT IN ('DISMISSED','ARCHIVED')")
        rows = self.conn.execute(f"SELECT * FROM agent_arrivals WHERE {clause} ORDER BY created_at DESC", (conversation_id,)).fetchall()
        return [self._arrival(row) for row in rows]

    def get_arrival(self, arrival_id: int) -> JsonDict:
        row = self.conn.execute("SELECT * FROM agent_arrivals WHERE id = ?", (arrival_id,)).fetchone()
        if row is None:
            raise KeyError(f"arrival not found: {arrival_id}")
        return self._arrival(row)

    def set_arrival_state(self, arrival_id: int, state: str) -> JsonDict:
        self.get_arrival(arrival_id)
        self.conn.execute("UPDATE agent_arrivals SET state = ? WHERE id = ?", (state, arrival_id))
        self.conn.commit()
        return self.get_arrival(arrival_id)

    def invite_agent(self, *, agent_id: str, conversation_id: str = "main", joined_at_message_id: int | None = None, context_scope: str = DEFAULT_CONTEXT_SCOPE, response_mode: str = DEFAULT_RESPONSE_MODE, status: str = "listening", permissions: JsonDict | None = None) -> JsonDict:
        self.ensure_conversation(conversation_id)
        merged_permissions = {**DEFAULT_PERMISSIONS, **(permissions or {})}
        self.conn.execute(
            """
            INSERT INTO agent_memberships (conversation_id, agent_id, joined_at_message_id, context_scope, response_mode, status, permissions_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(conversation_id, agent_id) DO UPDATE SET
                context_scope = excluded.context_scope,
                response_mode = excluded.response_mode,
                status = excluded.status,
                permissions_json = excluded.permissions_json,
                updated_at = datetime('now')
            """,
            (conversation_id, agent_id, joined_at_message_id, context_scope, response_mode, status, _dump(merged_permissions)),
        )
        self.conn.commit()
        return self.get_membership(conversation_id, agent_id)

    def get_membership(self, conversation_id: str, agent_id: str) -> JsonDict:
        row = self.conn.execute("SELECT * FROM agent_memberships WHERE conversation_id = ? AND agent_id = ?", (conversation_id, agent_id)).fetchone()
        if row is None:
            raise KeyError(f"membership not found: {conversation_id}/{agent_id}")
        return self._membership(row)

    def list_memberships(self, conversation_id: str = "main") -> list[JsonDict]:
        rows = self.conn.execute("SELECT * FROM agent_memberships WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,)).fetchall()
        return [self._membership(row) for row in rows]

    def create_branch(self, *, parent_conversation_id: str = "main", branched_from_message_id: int | None = None, title: str, participants: list[str] | None = None, shared_state_mode: str = "snapshot", merge_back_policy: str = "manual") -> JsonDict:
        self.ensure_conversation(parent_conversation_id)
        cursor = self.conn.execute(
            """
            INSERT INTO conversation_branches (parent_conversation_id, branched_from_message_id, title, participants_json, shared_state_mode, merge_back_policy)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (parent_conversation_id, branched_from_message_id, title, _dump(participants or []), shared_state_mode, merge_back_policy),
        )
        branch_id = f"branch-{int(cursor.lastrowid)}"
        self.conn.execute("UPDATE conversation_branches SET branch_id = ? WHERE id = ?", (branch_id, int(cursor.lastrowid)))
        self.ensure_conversation(branch_id, title=title)
        self.conn.commit()
        return self.get_branch(branch_id)

    def get_branch(self, branch_id: str) -> JsonDict:
        row = self.conn.execute("SELECT * FROM conversation_branches WHERE branch_id = ?", (branch_id,)).fetchone()
        if row is None:
            raise KeyError(f"branch not found: {branch_id}")
        return self._branch(row)

    def list_branches(self, parent_conversation_id: str = "main") -> list[JsonDict]:
        rows = self.conn.execute("SELECT * FROM conversation_branches WHERE parent_conversation_id = ? ORDER BY created_at DESC", (parent_conversation_id,)).fetchall()
        return [self._branch(row) for row in rows]

    def create_context_grant(self, *, conversation_id: str = "main", agent_id: str, scope: str = DEFAULT_CONTEXT_SCOPE, sources: list[JsonDict] | None = None, expires_at: str | None = None) -> JsonDict:
        self.ensure_conversation(conversation_id)
        cursor = self.conn.execute(
            "INSERT INTO context_grants (conversation_id, agent_id, scope, sources_json, expires_at) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, agent_id, scope, _dump(sources or []), expires_at),
        )
        self.conn.commit()
        return self._context_grant(self.conn.execute("SELECT * FROM context_grants WHERE id = ?", (int(cursor.lastrowid),)).fetchone())

    def create_proposal(self, *, conversation_id: str = "main", agent_id: str, body: str, mode: str = "silent_advisor", metadata: JsonDict | None = None) -> JsonDict:
        self.ensure_conversation(conversation_id)
        cursor = self.conn.execute(
            "INSERT INTO response_proposals (conversation_id, agent_id, mode, body, state, metadata_json) VALUES (?, ?, ?, ?, 'INTERNAL', ?)",
            (conversation_id, agent_id, mode, body, _dump(metadata or {})),
        )
        self.conn.commit()
        return self._proposal(self.conn.execute("SELECT * FROM response_proposals WHERE id = ?", (int(cursor.lastrowid),)).fetchone())

    def list_proposals(self, conversation_id: str = "main") -> list[JsonDict]:
        rows = self.conn.execute("SELECT * FROM response_proposals WHERE conversation_id = ? ORDER BY created_at DESC", (conversation_id,)).fetchall()
        return [self._proposal(row) for row in rows]

    def create_decision(self, *, conversation_id: str = "main", title: str, status: str = "accepted", rationale: str = "", source: str = "user") -> JsonDict:
        self.ensure_conversation(conversation_id)
        cursor = self.conn.execute(
            "INSERT INTO conversation_decisions (conversation_id, title, status, rationale, source) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, title, status, rationale, source),
        )
        self.conn.commit()
        return self._decision(self.conn.execute("SELECT * FROM conversation_decisions WHERE id = ?", (int(cursor.lastrowid),)).fetchone())

    def list_decisions(self, conversation_id: str = "main") -> list[JsonDict]:
        rows = self.conn.execute("SELECT * FROM conversation_decisions WHERE conversation_id = ? ORDER BY created_at DESC", (conversation_id,)).fetchall()
        return [self._decision(row) for row in rows]

    def create_reentry_packet(self, *, conversation_id: str = "main", agent_id: str, inactive_hours: float, last_message_count: int = 10) -> JsonDict:
        state = self.get_state(conversation_id)
        membership = None
        try:
            membership = self.get_membership(conversation_id, agent_id)
        except KeyError:
            membership = {"response_mode": DEFAULT_RESPONSE_MODE, "context_scope": DEFAULT_CONTEXT_SCOPE, "permissions": DEFAULT_PERMISSIONS}
        level = self._reentry_level(inactive_hours)
        template = self._reentry_template(level, state, membership, last_message_count)
        cursor = self.conn.execute(
            "INSERT INTO reentry_packets (conversation_id, agent_id, level, inactive_hours, template, packet_json) VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, agent_id, level, inactive_hours, template, _dump({"state": state, "membership": membership})),
        )
        self.conn.commit()
        return self._reentry_packet(self.conn.execute("SELECT * FROM reentry_packets WHERE id = ?", (int(cursor.lastrowid),)).fetchone())

    @staticmethod
    def _reentry_level(hours: float) -> str:
        if hours < 2:
            return "none"
        if hours < 5:
            return "resume"
        if hours < 12:
            return "reconstruct"
        return "full_packet"

    @staticmethod
    def _reentry_template(level: str, state: JsonDict, membership: JsonDict, last_message_count: int) -> str:
        if level == "none":
            return "No re-entry packet required. Continue normally."
        if level == "resume":
            return f"Resume the current thread. Review the active goal, accepted decisions, open questions, and the last {min(last_message_count, 5)} relevant messages. Do not restart the discussion."
        if level == "reconstruct":
            return "Reconstruct the active session from the conversation state. Identify what was decided, unresolved, and changed while inactive. Continue without repeating settled material."
        return "\n".join([
            f"Agent role/context scope: {membership.get('context_scope')}",
            f"Current project: {state.get('active_project', '')}",
            f"Current objective: {state.get('current_objective', '')}",
            f"Canonical definitions: {_dump(state.get('canonical_definitions', []))}",
            f"Accepted decisions: {_dump(state.get('accepted_decisions', []))}",
            f"Rejected options: {_dump(state.get('rejected_options', []))}",
            f"Unresolved questions: {_dump(state.get('unresolved_questions', []))}",
            f"Recent summary: {state.get('recent_summary', '')}",
            f"Required next action: {state.get('required_next_action', '')}",
        ])

    @staticmethod
    def _conversation(row: sqlite3.Row) -> JsonDict:
        return {"conversation_id": row["conversation_id"], "title": row["title"], "status": row["status"], "metadata": _load(row["metadata_json"], {}), "created_at": row["created_at"], "updated_at": row["updated_at"]}

    @staticmethod
    def _state(row: sqlite3.Row) -> JsonDict:
        return {"conversation_id": row["conversation_id"], "active_project": row["active_project"], "current_objective": row["current_objective"], "canonical_definitions": _load(row["canonical_definitions_json"], []), "accepted_decisions": _load(row["accepted_decisions_json"], []), "rejected_options": _load(row["rejected_options_json"], []), "unresolved_questions": _load(row["unresolved_questions_json"], []), "recent_summary": row["recent_summary"], "required_next_action": row["required_next_action"], "updated_at": row["updated_at"]}

    @staticmethod
    def _arrival(row: sqlite3.Row) -> JsonDict:
        return {"id": row["id"], "conversation_id": row["conversation_id"], "agent_id": row["agent_id"], "message_id": row["message_id"], "topic": row["topic"], "type": row["contribution_type"], "priority": row["priority"], "novelty": row["novelty"], "state": row["state"], "summary": row["summary"], "payload": _load(row["payload_json"], {}), "created_at": row["created_at"]}

    @staticmethod
    def _membership(row: sqlite3.Row) -> JsonDict:
        return {"id": row["id"], "conversation_id": row["conversation_id"], "agent_id": row["agent_id"], "joined_at_message_id": row["joined_at_message_id"], "context_scope": row["context_scope"], "response_mode": row["response_mode"], "status": row["status"], "permissions": _load(row["permissions_json"], DEFAULT_PERMISSIONS), "created_at": row["created_at"], "updated_at": row["updated_at"]}

    @staticmethod
    def _branch(row: sqlite3.Row) -> JsonDict:
        return {"branch_id": row["branch_id"], "parent_conversation_id": row["parent_conversation_id"], "branched_from_message_id": row["branched_from_message_id"], "title": row["title"], "participants": _load(row["participants_json"], []), "shared_state_mode": row["shared_state_mode"], "merge_back_policy": row["merge_back_policy"], "status": row["status"], "created_at": row["created_at"]}

    @staticmethod
    def _context_grant(row: sqlite3.Row) -> JsonDict:
        return {"id": row["id"], "conversation_id": row["conversation_id"], "agent_id": row["agent_id"], "scope": row["scope"], "sources": _load(row["sources_json"], []), "expires_at": row["expires_at"], "created_at": row["created_at"]}

    @staticmethod
    def _proposal(row: sqlite3.Row) -> JsonDict:
        return {"id": row["id"], "conversation_id": row["conversation_id"], "agent_id": row["agent_id"], "mode": row["mode"], "body": row["body"], "state": row["state"], "metadata": _load(row["metadata_json"], {}), "created_at": row["created_at"]}

    @staticmethod
    def _decision(row: sqlite3.Row) -> JsonDict:
        return {"id": row["id"], "conversation_id": row["conversation_id"], "title": row["title"], "status": row["status"], "rationale": row["rationale"], "source": row["source"], "created_at": row["created_at"]}

    @staticmethod
    def _reentry_packet(row: sqlite3.Row) -> JsonDict:
        return {"id": row["id"], "conversation_id": row["conversation_id"], "agent_id": row["agent_id"], "level": row["level"], "inactive_hours": row["inactive_hours"], "template": row["template"], "packet": _load(row["packet_json"], {}), "created_at": row["created_at"]}
