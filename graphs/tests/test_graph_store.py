#!/usr/bin/env python3
"""Unit tests for graphs/store.py.

Purpose: Verify graph CRUD operations work correctly against a temporary SQLite database.
Date: 2026-07-14
codex: graphs/tests/test_graph_store.py — unit tests for graph store
Status: TESTED
"""
import sqlite3
import sys
import unittest
from pathlib import Path

# Add repo root so we can import graphs
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "api"))
sys.path.insert(0, str(REPO_ROOT))

from graphs.store import GraphStore, Node, Edge, AntiEdge, IndexEntry
from file_intelligence_hub.storage.db import connect, initialize, _migration_14


class TestGraphStore(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        initialize(self.conn)
        # Ensure migration 14 is applied even if schema version is older in code
        _migration_14(self.conn)
        self.store = GraphStore(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_create_and_get_node(self):
        nid = self.store.create_node(hub="ai-hub", type="doc", label="Test Node")
        node = self.store.get_node(nid)
        self.assertIsNotNone(node)
        self.assertEqual(node.label, "Test Node")
        self.assertEqual(node.hub, "ai-hub")
        self.assertEqual(node.type, "doc")

    def test_list_nodes_by_hub(self):
        self.store.create_node(hub="ai-hub", type="doc", label="A")
        self.store.create_node(hub="ai-hub", type="doc", label="B")
        self.store.create_node(hub="framework", type="axiom", label="C")
        ai_nodes = self.store.list_nodes(hub="ai-hub")
        self.assertEqual(len(ai_nodes), 2)
        fw_nodes = self.store.list_nodes(hub="framework")
        self.assertEqual(len(fw_nodes), 1)

    def test_update_node(self):
        nid = self.store.create_node(hub="ai-hub", type="doc", label="Old")
        self.store.update_node(nid, label="New", chi_score=2.5)
        node = self.store.get_node(nid)
        self.assertEqual(node.label, "New")
        self.assertEqual(node.chi_score, 2.5)

    def test_delete_node_cascades(self):
        n1 = self.store.create_node(hub="ai-hub", type="doc", label="A")
        n2 = self.store.create_node(hub="ai-hub", type="doc", label="B")
        self.store.create_edge(src=n1, dst=n2, type="supports", force="F2")
        self.store.create_anti_edge(src=n1, dst=n2, status="contradicts")
        self.store.upsert_index(n1, keywords="test", one_liner="test")
        self.store.delete_node(n1)
        self.assertIsNone(self.store.get_node(n1))
        edges = self.store.get_edges(n2)
        self.assertEqual(len(edges), 0)

    def test_create_and_get_edge(self):
        n1 = self.store.create_node(hub="ai-hub", type="doc", label="A")
        n2 = self.store.create_node(hub="ai-hub", type="doc", label="B")
        eid = self.store.create_edge(src=n1, dst=n2, type="supports", force="F2", weight=0.8)
        edges = self.store.get_edges(n1)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].type, "supports")
        self.assertEqual(edges[0].weight, 0.8)

    def test_anti_edge(self):
        n1 = self.store.create_node(hub="ai-hub", type="doc", label="A")
        n2 = self.store.create_node(hub="ai-hub", type="doc", label="B")
        self.store.create_anti_edge(src=n1, dst=n2, status="unbridged", why_not="No derivation yet")
        aes = self.store.get_anti_edges(n1)
        self.assertEqual(len(aes), 1)
        self.assertEqual(aes[0].status, "unbridged")

    def test_graph_index(self):
        n1 = self.store.create_node(hub="ai-hub", type="doc", label="A")
        self.store.upsert_index(n1, keywords="physics faith", one_liner="The intersection of physics and faith")
        results = self.store.search_index("physics")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].node_id, n1)

    def test_export_import_hub(self):
        n1 = self.store.create_node(hub="ai-hub", type="doc", label="A", node_id="node-1")
        n2 = self.store.create_node(hub="ai-hub", type="doc", label="B", node_id="node-2")
        self.store.create_edge(src=n1, dst=n2, type="supports", force="F2", edge_id="edge-1")
        data = self.store.export_hub("ai-hub")
        self.assertEqual(len(data["nodes"]), 2)
        self.assertEqual(len(data["edges"]), 1)
        # Import into fresh store
        conn2 = connect(":memory:")
        initialize(conn2)
        _migration_14(conn2)
        store2 = GraphStore(conn2)
        store2.import_hub(data)
        self.assertEqual(store2.count_nodes("ai-hub"), 2)
        self.assertEqual(store2.count_edges("ai-hub"), 1)
        conn2.close()

    def test_count_nodes(self):
        self.store.create_node(hub="ai-hub", type="doc", label="A")
        self.store.create_node(hub="ai-hub", type="doc", label="B")
        self.assertEqual(self.store.count_nodes("ai-hub"), 2)
        self.assertEqual(self.store.count_nodes("framework"), 0)

    def test_node_exists(self):
        nid = self.store.create_node(hub="ai-hub", type="doc", label="A")
        self.assertTrue(self.store.node_exists(nid))
        self.assertFalse(self.store.node_exists("nonexistent"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
