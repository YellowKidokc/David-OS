from dataclasses import replace

from mcp_hub.config import Settings
from mcp_hub.hub import ToolHub
from mcp_hub.mcp_stdio import dispatch


class FakeSiyuan:
    def search(self, query, limit=8, notebook=None, tags=None):
        return [
            {"id": "block-1", "document_id": "doc-1", "title": "Top of Mind Agent Notes", "notebook": notebook or "AI", "path": "/AI Hub/Top of Mind", "excerpt": f"Architecture notes for {query}", "type": "p", "updated": "20260717"},
            {"id": "block-2", "document_id": "doc-2", "title": "Bridge", "notebook": "AI", "path": "/AI Hub/Bridge", "excerpt": "A second result", "type": "p", "updated": "20260716"},
        ][:limit]

    def get(self, block_id):
        return {"id": block_id, "title": "Note", "path": "/Note", "content": "# Note\nReadable kramdown"}


def make_hub(max_context_chars=6000):
    settings = replace(Settings(), max_context_chars=max_context_chars, max_response_chars=20000, remote_servers=())
    return ToolHub(settings=settings, siyuan=FakeSiyuan())


def test_lists_required_tools():
    names = {tool["name"] for tool in make_hub().list_tools()}
    assert {"knowledge.search", "knowledge.get", "knowledge.context_packet", "tool.list", "tool.call"} <= names


def test_context_packet_is_bounded_and_cited():
    response = make_hub(300).call("knowledge.context_packet", {"query": "agent architecture", "max_chars": 5000})
    assert response["ok"] is True
    assert len(response["result"]["context"]) <= 300
    assert "[SiYuan:block-1]" in response["result"]["context"]
    assert response["result"]["sources"][0]["path"] == "/AI Hub/Top of Mind"


def test_nested_tool_call_and_unknown_tool_are_normalized():
    hub = make_hub()
    nested = hub.call("tool.call", {"name": "knowledge.get", "arguments": {"id": "block-1"}})
    assert nested["ok"] is True
    assert nested["result"]["result"]["content"].startswith("# Note")
    assert hub.call("delete.everything", {})["ok"] is False


def test_stdio_dispatch_exposes_tools():
    response = dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, make_hub())
    assert response["result"]["tools"][0]["inputSchema"]["type"] == "object"
