from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[3] / "agents" / "watchers" / "hub_watcher.py"
spec = importlib.util.spec_from_file_location("hub_watcher", MODULE_PATH)
hub_watcher = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["hub_watcher"] = hub_watcher
spec.loader.exec_module(hub_watcher)


class RecordingClient(hub_watcher.HubClient):
    def __init__(self) -> None:
        super().__init__("http://hub.test", dry_run=True)
        self.calls: list[tuple[str, dict]] = []

    def post(self, endpoint: str, payload: dict) -> dict:
        self.calls.append((endpoint, payload))
        return {"ok": True}


def test_created_file_becomes_cache_job_semantic_and_message_payloads(tmp_path: Path) -> None:
    root = tmp_path / "watch-inbox"
    root.mkdir()
    config = {"source_node_id": "test-node", "profiles": [{"path": str(root), "folder_role": "inbox", "watch_enabled": True, "review_only": True}]}
    client = RecordingClient()
    watcher = hub_watcher.HubWatcher(config, client, hub_watcher.JsonlQueue(tmp_path / "queue"))

    created = root / "note.txt"
    created.write_text("hello", encoding="utf-8")
    events = watcher.poll_once()

    assert events[0]["event_type"] == "created"
    assert events[0]["folder_profile"] == "inbox"
    assert events[0]["review_status"] == "review"
    endpoints = [endpoint for endpoint, _ in client.calls]
    assert endpoints == ["/files/cache", "/jobs/file-events", "/semantic/score", "/top-of-mind/messages"]
    assert client.calls[0][1]["full_path"] == str(created)
    assert client.calls[1][1]["path"] == str(created)


def test_offline_mode_queues_events_without_touching_watched_file(tmp_path: Path) -> None:
    root = tmp_path / "watch-inbox"
    root.mkdir()
    config = {"source_node_id": "test-node", "profiles": [{"path": str(root), "folder_role": "inbox", "watch_enabled": True}]}
    queue = hub_watcher.JsonlQueue(tmp_path / "queue")
    watcher = hub_watcher.HubWatcher(config, hub_watcher.HubClient("http://hub.test", offline=True), queue)

    created = root / "queued.txt"
    created.write_text("do not edit me", encoding="utf-8")
    before = created.read_text(encoding="utf-8")
    watcher.poll_once()

    assert created.read_text(encoding="utf-8") == before
    queued = [json.loads(line) for line in queue.queue_file.read_text(encoding="utf-8").splitlines()]
    assert queued[0]["path"] == str(created)
    assert queued[0]["event_type"] == "created"


def test_program_root_and_secret_names_are_blocked(tmp_path: Path) -> None:
    root = tmp_path / "program-root"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    secret = root / ".env"
    secret.write_text("TOKEN=x", encoding="utf-8")
    config = {"source_node_id": "test-node", "profiles": [{"path": str(root), "folder_role": "program_root", "watch_enabled": True, "protected": False}]}

    event = hub_watcher.normalize_event("created", secret, old_path=None, source_node_id="test-node", profiles=hub_watcher.iter_profiles(config))

    assert event["review_status"] == "block"
    assert event["blocked_reason"] in {"secret_or_credential_name", "program_root"}
    endpoints = [endpoint for endpoint, _, _ in hub_watcher.build_payloads(event)]
    assert "/semantic/score" not in endpoints
