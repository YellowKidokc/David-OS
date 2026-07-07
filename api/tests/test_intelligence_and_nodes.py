import json
from pathlib import Path

from file_intelligence_hub.config.folder_profiles import FolderProfileRegistry
from file_intelligence_hub.intelligence.file_feature_builder import build_file_record
from file_intelligence_hub.intelligence.folder_feature_builder import choose_summary_strategy
from file_intelligence_hub.services.node_health import NodeHealthService, RepairPolicy, classify_health
from file_intelligence_hub.storage.db import Database, current_version
from file_intelligence_hub.storage.intelligence_repo import IntelligenceRepo
from file_intelligence_hub.storage.job_repo import JobRepo
from file_intelligence_hub.storage.node_repo import NodeRepo
from file_intelligence_hub.workers.asset_pair_worker import detect_asset_pairs
from file_intelligence_hub.workers.folder_summary_worker import FolderSummaryWorker
from file_intelligence_hub.workers.runner import WorkerRunner


def test_file_record_separates_raw_deterministic_and_ai_provenance(tmp_path):
    sample = tmp_path / "Report 2026.txt"
    sample.write_text("hello", encoding="utf-8")

    record = build_file_record(sample, node_id="node-a")

    assert record["identity"]["node_id"] == "node-a"
    assert record["raw"]["size"] == 5
    assert record["deterministic"]["kind"] == "text"
    assert record["ai_advised"]["provenance"] == "not_run"
    assert record["provenance"]["raw_fields"]["size"] == "filesystem"


def test_folder_summary_tiers_and_action_pressure_persist(tmp_path):
    folder = tmp_path / "inbox"
    folder.mkdir()
    (folder / "A Report.txt").write_text("a", encoding="utf-8")
    (folder / "A Report.json").write_text("{}", encoding="utf-8")
    db = Database(tmp_path / "hub.sqlite3")
    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(json.dumps({"profiles": [{"path": str(folder), "folder_role": "inbox", "review_only": True}]}), encoding="utf-8")

    summary = FolderSummaryWorker(
        IntelligenceRepo(db.conn), JobRepo(db.conn), FolderProfileRegistry.load(profiles_path)
    ).summarize_folder(folder, node_id="node-a")

    assert summary["summary"]["summary_mode"] == "near_full"
    assert summary["provenance"]["summary_source"] == "deterministic_only"
    assert summary["action_pressure"]["dominant"] in {"rename_cleanup", "routing_pressure", "metadata_fill_pressure"}
    assert IntelligenceRepo(db.conn).list_file_records_under(str(folder.resolve()))


def test_summary_strategy_ranges_are_encoded():
    assert choose_summary_strategy(25).mode == "near_full"
    assert choose_summary_strategy(200).mode == "aggregate_plus_representative_sample"
    assert choose_summary_strategy(2_000).mode == "aggregate_first_semantic_sample_second"
    assert choose_summary_strategy(10_000).mode == "compressed_overview"
    assert choose_summary_strategy(10_001).mode == "territory"


def test_asset_pair_detection_promotes_sidecar_logic(tmp_path):
    jpg = tmp_path / "image.jpg"
    xmp = tmp_path / "image.xmp"
    jpg.write_text("primary", encoding="utf-8")
    xmp.write_text("sidecar", encoding="utf-8")

    pairs = detect_asset_pairs([str(jpg), str(xmp)])

    assert pairs[str(jpg)] == [str(xmp)]


def test_node_heartbeat_health_and_safe_repair_logging(tmp_path):
    db = Database(tmp_path / "hub.sqlite3")
    source = tmp_path / "peer"
    target = tmp_path / "local"
    (source / "schemas").mkdir(parents=True)
    (source / "schemas/folder_profiles.schema.json").write_text("{}", encoding="utf-8")
    (target / "schemas").mkdir(parents=True)
    (target / "schemas/folder_profiles.schema.json").write_text("{}", encoding="utf-8")
    service = NodeHealthService(NodeRepo(db.conn), JobRepo(db.conn), node_id="node-a", repo_root=target)

    heartbeat = service.heartbeat()
    repair = service.repair_safe_artifact("schemas/folder_profiles.schema.json", source_root=source, source_node="node-b")

    assert heartbeat["node_id"] == "node-a"
    assert heartbeat["build_signature"] == f"schema-{current_version(db.conn)}"
    assert repair["outcome"] == "success"
    assert NodeRepo(db.conn).list_repairs()[0]["source_node"] == "node-b"


def test_repair_policy_blocks_ledgers_and_secrets():
    policy = RepairPolicy()

    assert policy.is_safe_artifact("schemas/folder_profiles.schema.json") is True
    assert policy.is_safe_artifact("config/secret_token.txt") is False
    assert policy.is_safe_artifact(".data/file-intelligence-hub.sqlite3") is False


def test_health_classification_statuses():
    base = {"sqlite_writable": True, "schema_current": True, "required_assets_present": True, "watcher_health": "ok"}

    assert classify_health({**base, "sqlite_writable": False}, {"queued": 0, "failed_retryable": 0}) == "critical"
    assert classify_health({**base, "required_assets_present": False}, {"queued": 0, "failed_retryable": 0}) == "needs_peer_assist"
    assert classify_health(base, {"queued": 0, "failed_retryable": 11}) == "repairable_local"


def test_folder_summary_job_runs_through_worker_queue(tmp_path):
    folder = tmp_path / "queue-folder"
    folder.mkdir()
    (folder / "queued.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    db = Database(tmp_path / "hub.sqlite3")
    repo = JobRepo(db.conn)
    job = repo.create_job("folder_summary", {"folder_path": str(folder)})

    processed = WorkerRunner(repo).run_once(limit=1)

    assert processed[0]["id"] == job["id"]
    assert processed[0]["status"] == "completed"
    assert IntelligenceRepo(db.conn).get_folder_summary(str(folder.resolve()))["summary"]["file_count"] == 1
