def test_clipboard_shelf_save_list_search_copy_import(tmp_path, monkeypatch):
    db_path = tmp_path / "clipboard.sqlite3"
    monkeypatch.setenv("FIHUB_DB_PATH", str(db_path))
    monkeypatch.delenv("FIHUB_API_TOKEN", raising=False)

    from file_intelligence_hub.api import routes_clipboard
    routes_clipboard.DEFAULT_DB_PATH = db_path

    item = routes_clipboard.save_item_alias(routes_clipboard.ClipboardItemRequest(
        body="clipboard alpha text",
        source_app="AutoHotkey.exe",
        source_window="Test Window",
        folder="Clipboard",
        tags="alpha,test",
        pinned=True,
    ))["item"]
    assert item["id"] > 0
    assert item["body"] == "clipboard alpha text"
    assert item["pinned"] is True
    assert item["content_hash"]
    assert item["secret_warning"] is False

    items = routes_clipboard.list_items(query="alpha", source_app="AutoHotkey.exe", tag="alpha")["items"]
    assert [found["id"] for found in items] == [item["id"]]

    assert "AutoHotkey.exe" in routes_clipboard.facets()["facets"]["source_apps"]

    copy_response = routes_clipboard.copy_item(item["id"])
    assert copy_response["item"]["copied_at"] is not None
    assert copy_response["bridge_action"] == "copy_to_windows_clipboard"

    import_response = routes_clipboard.import_items(routes_clipboard.ClipboardImportRequest(items=[{"body": "imported clip", "folder": "Imported"}]))
    assert import_response["stored"] == 1


def test_clipboard_items_route_still_accepts_existing_clients(tmp_path, monkeypatch):
    db_path = tmp_path / "clipboard.sqlite3"
    monkeypatch.setenv("FIHUB_DB_PATH", str(db_path))
    monkeypatch.delenv("FIHUB_API_TOKEN", raising=False)

    from file_intelligence_hub.api import routes_clipboard
    routes_clipboard.DEFAULT_DB_PATH = db_path

    response = routes_clipboard.save_item(routes_clipboard.ClipboardItemRequest(body="legacy route"))

    assert response["item"]["body"] == "legacy route"


def test_clipboard_merge_restore_duplicates_export_and_retention(tmp_path, monkeypatch):
    db_path = tmp_path / "clipboard.sqlite3"
    monkeypatch.setenv("FIHUB_DB_PATH", str(db_path))
    monkeypatch.delenv("FIHUB_API_TOKEN", raising=False)

    from file_intelligence_hub.api import routes_clipboard
    routes_clipboard.DEFAULT_DB_PATH = db_path

    one = routes_clipboard.save_item_alias(routes_clipboard.ClipboardItemRequest(body="same secret_token=abcdef0123456789abcdef0123456789", kind="text"))["item"]
    two = routes_clipboard.save_item_alias(routes_clipboard.ClipboardItemRequest(body="same secret_token=abcdef0123456789abcdef0123456789", kind="text"))["item"]
    assert one["secret_warning"] is True

    dupe_response = routes_clipboard.duplicates()
    assert dupe_response["duplicates"][0]["duplicate_count"] == 2

    merge_response = routes_clipboard.merge_items(routes_clipboard.ClipboardMergeRequest(item_ids=[one["id"], two["id"]], save=True))
    assert merge_response["merge"]["count"] == 2
    assert merge_response["merge"]["item"]["folder"] == "Merged"

    delete_response = routes_clipboard.delete_item(one["id"])
    assert delete_response["item"]["deleted"] is True
    restore_response = routes_clipboard.restore_item(one["id"])
    assert restore_response["item"]["deleted"] is False

    export_response = routes_clipboard.export_items(routes_clipboard.ClipboardExportRequest(item_ids=[one["id"]], format="markdown"))
    assert "clipboard:" in export_response.body.decode()

    retention_response = routes_clipboard.set_retention(routes_clipboard.ClipboardRetentionRequest(days=30, include_pinned=True))
    assert retention_response["retention"]["days"] == 30
