from file_intelligence_hub.storage.db import Database
from file_intelligence_hub.storage.top_of_mind_repo import TopOfMindRepo


def test_top_of_mind_http_message_flow(tmp_path):
    from fastapi.testclient import TestClient

    from file_intelligence_hub.api import routes_top_of_mind
    from file_intelligence_hub.api.app import create_app

    routes_top_of_mind.DEFAULT_DB_PATH = tmp_path / "hub.sqlite3"
    client = TestClient(create_app())

    source_response = client.post(
        "/top-of-mind/sources",
        json={"source_id": "kimi-cli", "label": "Kimi", "kind": "cli", "priority": 4},
    )
    message_response = client.post(
        "/top-of-mind/messages",
        json={"source_id": "kimi-cli", "body": "Checkpoint question", "wall": "wall-1", "folder": "Code"},
    )
    list_response = client.get("/top-of-mind/messages", params={"wall": "wall-1", "folder": "Code"})

    assert source_response.status_code == 200
    assert message_response.status_code == 200
    assert list_response.status_code == 200
    assert list_response.json()["messages"][0]["body"] == "Checkpoint question"


def test_top_of_mind_sources_messages_and_combine(tmp_path):
    db = Database(tmp_path / "hub.sqlite3")
    repo = TopOfMindRepo(db.conn)

    source = repo.upsert_source("kimi-cli", label="Kimi", kind="cli", priority=4)
    first = repo.post_message(source_id="kimi-cli", body="Question from Kimi", wall="wall-1", folder="Code")
    second = repo.post_message(source_id="codex", source_label="Codex", body="Answer from Codex", wall="wall-1", folder="Code")
    combined = repo.combine_messages([first["id"], second["id"]], wall="wall-1", folder="Code")
    stopped = repo.stop_all_sources()

    assert source["label"] == "Kimi"
    assert first["source_label"] == "Kimi"
    assert second["source_label"] == "Codex"
    assert combined["pinned"] is True
    assert combined["combined_from"] == [first["id"], second["id"]]
    assert "[Kimi] Question from Kimi" in combined["body"]
    assert "[Codex] Answer from Codex" in combined["body"]
    assert all(item["paused"] is True for item in stopped)


def test_top_of_mind_list_messages_defaults_to_newest_and_unarchived(tmp_path):
    db = Database(tmp_path / "hub.sqlite3")
    repo = TopOfMindRepo(db.conn)

    first = repo.post_message(source_id="clipboard", source_label="Clipboard", body="old")
    second = repo.post_message(source_id="clipboard", source_label="Clipboard", body="new")
    repo.set_message_state(first["id"], archived=True)

    messages = repo.list_messages(limit=75)
    archived = repo.list_messages(include_archived=True, limit=75)

    assert [message["id"] for message in messages] == [second["id"]]
    assert [message["id"] for message in archived] == [second["id"], first["id"]]
