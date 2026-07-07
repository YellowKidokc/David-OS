#!/usr/bin/env python3
"""
Preference Engine Folder Builder v1.0
POF 2828 | June 2026

Builds standardized folder structure for all preference engines (P01-P07).
Each engine gets the same interface: inbox, outbox, front door, scripts.
Any AI or human drops files in inbox → engine processes → output in outbox.

Safety: Creates missing only. Never deletes. Preserves existing files.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(r"X:\Models")

ENGINES = [
    {
        "id": "P01", "name": "implicit",
        "library": "implicit",
        "desc": "Collaborative filtering from implicit feedback (co-occurrence patterns)",
        "status": "scaffolded",
        "port": 20101,
        "learns_from": "Co-occurrence of file actions — 'David always renames X then Y'",
        "outputs": "Item-item similarity matrix, recommendation scores",
        "depends_on": ["P05_ppk"],
    },
    {
        "id": "P02", "name": "recbole",
        "library": "recbole",
        "desc": "General-purpose recommendation framework (future)",
        "status": "scaffolded",
        "port": 20102,
        "learns_from": "Structured interaction logs",
        "outputs": "Ranked recommendations",
        "depends_on": [],
    },
    {
        "id": "P03", "name": "lightfm",
        "library": "lightfm",
        "desc": "Hybrid collaborative + content-based recommendations (blocked on Windows build)",
        "status": "blocked",
        "port": 20103,
        "learns_from": "User-item interactions + item metadata",
        "outputs": "Hybrid recommendation scores",
        "depends_on": [],
    },
    {
        "id": "P04", "name": "paper_recommender",
        "library": "custom",
        "desc": "Research paper relevance scoring for Theophysics corpus",
        "status": "scaffolded",
        "port": 20104,
        "learns_from": "Paper approve/reject, citation patterns, reading time",
        "outputs": "Paper relevance scores, reading order suggestions",
        "depends_on": ["P06_river", "P05_ppk"],
    },
    {
        "id": "P05", "name": "ppk",
        "library": "custom",
        "desc": "Portable Preference Kernel — compressed identity export from all engines",
        "status": "has_content",
        "port": 20105,
        "learns_from": "Periodic exports from River and other engines",
        "outputs": "naming_ppk.json — portable preference identity file",
        "depends_on": ["P06_river"],
    },
    {
        "id": "P06", "name": "river",
        "library": "river",
        "desc": "Online streaming ML — real-time learning from every approve/reject",
        "status": "active",
        "port": 20106,
        "learns_from": "File naming approve/reject events via FIS API",
        "outputs": "Microsecond predictions, periodic PPK exports, slug corpus for Markovify",
        "depends_on": [],
    },
    {
        "id": "P07", "name": "markovify",
        "library": "markovify",
        "desc": "Markov chain text prediction for slug/name generation",
        "status": "active",
        "port": 20107,
        "learns_from": "Approved slug corpus from River",
        "outputs": "Predicted file names/slugs based on learned patterns",
        "depends_on": ["P06_river"],
    },
]

STANDARD_SUBDIRS = [
    ("_front_door",     "Engine metadata, config, health check, status"),
    ("_inbox",          "Drop files here for processing. Engine picks them up automatically."),
    ("_outbox",         "Processed results land here. Human or AI picks them up."),
    ("_processed",      "Archive of processed inbox items with timestamps"),
    ("_logs",           "Runtime logs, error logs, health reports"),
    ("_state",          "Trained model weights, pkl files, learned state"),
    ("_exports",        "Periodic exports (PPK snapshots, reports, metrics)"),
]

def safe_write(path: Path, text: str):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"  + {path.relative_to(ROOT)}")

def mkdir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def build_engine(engine: dict):
    eid = engine["id"]
    name = engine["name"]
    folder = ROOT / f"{eid}_{name}"
    mkdir(folder)

    # Create standard subdirectories
    for subdir, desc in STANDARD_SUBDIRS:
        p = folder / subdir
        mkdir(p)
        safe_write(p / "README.md", f"# {eid} {name} — {subdir.strip('_')}\n\n{desc}\n")

    # Front door config
    safe_write(folder / "_front_door" / "config.json", json.dumps({
        "engine_id": eid,
        "engine_name": name,
        "library": engine["library"],
        "description": engine["desc"],
        "status": engine["status"],
        "port": engine["port"],
        "learns_from": engine["learns_from"],
        "outputs": engine["outputs"],
        "depends_on": engine["depends_on"],
        "created": datetime.now().isoformat(timespec="seconds"),
        "version": "1.0",
    }, indent=2))

    # Front door health check
    safe_write(folder / "_front_door" / "health.py", "\n".join([
        "#!/usr/bin/env python3",
        f'"""Health check for {eid}_{name}"""',
        "import json, importlib, sys",
        "from pathlib import Path",
        "",
        "def check():",
        "    status = {'engine': '" + eid + "', 'name': '" + name + "', 'checks': {}}",
        "",
        "    # Check library import",
        "    try:",
        f"        importlib.import_module('{engine['library']}')",
        f"        status['checks']['library_{engine['library']}'] = 'OK'",
        "    except ImportError:",
        f"        status['checks']['library_{engine['library']}'] = 'MISSING'",
        "",
        "    # Check state files",
        "    state_dir = Path(__file__).parent.parent / '_state'",
        "    pkl_files = list(state_dir.glob('*.pkl'))",
        "    status['checks']['trained_models'] = len(pkl_files)",
        "",
        "    # Check inbox",
        "    inbox = Path(__file__).parent.parent / '_inbox'",
        "    pending = list(inbox.glob('*')) if inbox.exists() else []",
        "    pending = [p for p in pending if p.name != 'README.md']",
        "    status['checks']['inbox_pending'] = len(pending)",
        "",
        "    status['healthy'] = status['checks'].get(f'library_{engine[\"library\"]}') == 'OK'",
        "    return status",
        "",
        "if __name__ == '__main__':",
        "    result = check()",
        "    print(json.dumps(result, indent=2))",
        "",
    ]))

    # Start script
    safe_write(folder / "START.bat", "\n".join([
        "@echo off",
        f"echo Starting {eid}_{name} preference engine...",
        f"cd /d %~dp0",
        f'python _front_door\\health.py',
        f"echo.",
        f"echo {eid} ready on port {engine['port']}",
        "pause",
        "",
    ]))

    # Healthcheck script
    safe_write(folder / "HEALTHCHECK.bat", "\n".join([
        "@echo off",
        f"echo Running health check for {eid}_{name}...",
        f"cd /d %~dp0",
        f'python _front_door\\health.py',
        "pause",
        "",
    ]))

    # Process inbox script
    safe_write(folder / "PROCESS_INBOX.bat", "\n".join([
        "@echo off",
        f"echo Processing inbox for {eid}_{name}...",
        f"cd /d %~dp0",
        f'python _front_door\\process_inbox.py',
        "pause",
        "",
    ]))

    # Inbox processor stub
    safe_write(folder / "_front_door" / "process_inbox.py", "\n".join([
        "#!/usr/bin/env python3",
        f'"""Process inbox items for {eid}_{name}"""',
        "import json, shutil",
        "from pathlib import Path",
        "from datetime import datetime",
        "",
        "ENGINE_ROOT = Path(__file__).parent.parent",
        "INBOX = ENGINE_ROOT / '_inbox'",
        "OUTBOX = ENGINE_ROOT / '_outbox'",
        "PROCESSED = ENGINE_ROOT / '_processed'",
        "",
        "def process():",
        "    items = [f for f in INBOX.iterdir() if f.name != 'README.md']",
        "    if not items:",
        "        print('Inbox empty — nothing to process.')",
        "        return",
        "",
        "    print(f'Found {len(items)} items in inbox:')",
        "    for item in items:",
        "        print(f'  → {item.name}')",
        "        # TODO: Wire to actual engine processing",
        "        # For now, move to processed with timestamp",
        "        ts = datetime.now().strftime('%Y%m%d_%H%M%S')",
        "        dest = PROCESSED / f'{ts}_{item.name}'",
        "        shutil.move(str(item), str(dest))",
        "        print(f'    Moved to _processed/{dest.name}')",
        "",
        "if __name__ == '__main__':",
        "    process()",
        "",
    ]))

    # Engine README
    safe_write(folder / "README.md", "\n".join([
        f"# {eid} — {name.title()}",
        "",
        f"**Library:** `{engine['library']}`",
        f"**Port:** {engine['port']}",
        f"**Status:** {engine['status']}",
        "",
        f"## What it does",
        f"{engine['desc']}",
        "",
        f"## Learns from",
        f"{engine['learns_from']}",
        "",
        f"## Outputs",
        f"{engine['outputs']}",
        "",
        f"## Dependencies",
        f"{', '.join(engine['depends_on']) if engine['depends_on'] else 'None (independent)'}",
        "",
        "## Folder structure",
        "```",
        f"{eid}_{name}/",
        "  _front_door/    Config, health check, processing scripts",
        "  _inbox/          Drop files here for processing",
        "  _outbox/         Processed results",
        "  _processed/      Archive of processed items",
        "  _logs/           Runtime logs",
        "  _state/          Trained model weights (pkl, json)",
        "  _exports/        Periodic exports (PPK snapshots)",
        "  START.bat         Boot the engine",
        "  HEALTHCHECK.bat   Check engine health",
        "  PROCESS_INBOX.bat Process pending inbox items",
        "```",
        "",
    ]))

def build_master_files():
    """Build master registry and healthcheck at the Models root."""

    # Master registry
    safe_write(ROOT / "PREFERENCE_ENGINE_REGISTRY.json", json.dumps({
        "version": "1.0",
        "built": datetime.now().isoformat(timespec="seconds"),
        "port_scheme": "20100 + engine number (5-digit ports, 20xxx = APIs/services)",
        "engines": {e["id"]: {
            "name": e["name"],
            "port": e["port"],
            "status": e["status"],
            "library": e["library"],
        } for e in ENGINES}
    }, indent=2))

    # Master healthcheck
    safe_write(ROOT / "HEALTHCHECK_ALL_ENGINES.bat", "\n".join([
        "@echo off",
        "echo ═══════════════════════════════════════",
        "echo   PREFERENCE ENGINE HEALTH CHECK",
        "echo ═══════════════════════════════════════",
        "echo.",
    ] + [
        f'echo [{e["id"]}] {e["name"]}...\npython "{ROOT / f"{e["id"]}_{e["name"]}" / "_front_door" / "health.py"}"\necho.'
        for e in ENGINES
    ] + [
        "echo.",
        "echo Done.",
        "pause",
        "",
    ]))

    # Master start script
    safe_write(ROOT / "START_ALL_ENGINES.bat", "\n".join([
        "@echo off",
        "echo Starting all preference engines...",
        "echo.",
    ] + [
        f'echo Starting {e["id"]}_{e["name"]}...\nstart "" /min cmd /c "{ROOT / f"{e["id"]}_{e["name"]}" / "START.bat"}"'
        for e in ENGINES if e["status"] in ("active", "has_content")
    ] + [
        "echo.",
        "echo Active engines started.",
        "pause",
        "",
    ]))


def build():
    print("=" * 60)
    print("PREFERENCE ENGINE FOLDER BUILDER v1.0")
    print("POF 2828 | " + datetime.now().strftime("%B %Y"))
    print("=" * 60)
    print(f"Root: {ROOT}")
    print()

    for engine in ENGINES:
        print(f"\n[{engine['id']}] {engine['name']} ({engine['status']})")
        build_engine(engine)

    print("\n--- Master files ---")
    build_master_files()

    print("\n" + "=" * 60)
    print(f"Built {len(ENGINES)} preference engine folders")
    print(f"Port range: {ENGINES[0]['port']} - {ENGINES[-1]['port']}")
    print("Nothing was deleted. Existing files preserved.")
    print("=" * 60)


if __name__ == "__main__":
    build()

