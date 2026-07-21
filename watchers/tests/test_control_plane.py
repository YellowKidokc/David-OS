from pathlib import Path

from watchers.control_plane import HubClient, JsonlQueue, WatcherControlPlane, build_event, is_forbidden


class FakeClient(HubClient):
    def __init__(self):
        super().__init__("http://hub", dry_run=True)
        self.posts = []
        self.gets = []
    def post(self, endpoint, payload):
        self.posts.append((endpoint, payload))
        return {"ok": True}
    def get(self, endpoint):
        self.gets.append(endpoint)
        return {"ok": True}


def config(root: Path, queue: Path):
    return {"source_node_id": "test-node", "roots": [{"path": str(root), "enabled": True}], "ignore_globs": [], "queue_file": str(queue)}


def test_build_event_uses_hub_normalizer(tmp_path):
    p = tmp_path / "note.txt"
    p.write_text("hello", encoding="utf-8")
    event = build_event("created", p, source_node_id="node-1")
    assert event["source"] == "watcher_control_plane"
    assert event["event_type"] == "created"
    assert event["source_node_id"] == "node-1"
    assert event["extension"] == ".txt"
    assert event["cheap_labels"] == ["document"]


def test_reconcile_emits_create_modify_delete(tmp_path):
    client = FakeClient()
    plane = WatcherControlPlane(config(tmp_path, tmp_path / "queue.jsonl"), client, JsonlQueue(tmp_path / "queue.jsonl"))
    plane.snapshot = plane.scan()
    p = tmp_path / "a.txt"
    p.write_text("one", encoding="utf-8")
    assert [e["event_type"] for e in plane.reconcile_once()] == ["created"]
    p.write_text("two plus", encoding="utf-8")
    assert [e["event_type"] for e in plane.reconcile_once()] == ["modified"]
    p.unlink()
    assert [e["event_type"] for e in plane.reconcile_once()] == ["deleted"]
    assert [endpoint for endpoint, _ in client.posts].count("/jobs/file-events") == 3


def test_unknown_extension_creates_help_request(tmp_path):
    client = FakeClient()
    plane = WatcherControlPlane(config(tmp_path, tmp_path / "queue.jsonl"), client, JsonlQueue(tmp_path / "queue.jsonl"))
    p = tmp_path / "mystery"
    p.write_text("?", encoding="utf-8")
    plane.emit(build_event("created", p, source_node_id="test-node"))
    assert any(endpoint == "/jobs/help-requests" for endpoint, _ in client.posts)


def test_status_reports_hub_and_roots(tmp_path):
    client = FakeClient()
    plane = WatcherControlPlane(config(tmp_path, tmp_path / "queue.jsonl"), client, JsonlQueue(tmp_path / "queue.jsonl"))
    text = "\n".join(plane.status_lines())
    assert "David-OS Watcher Control Plane" in text
    assert str(tmp_path) in text
    assert "reachable" in text


def test_forbidden_boot_root_is_never_watched():
    assert is_forbidden(Path("D:/DONT TOUCH BOOT UP/anything.txt"))
