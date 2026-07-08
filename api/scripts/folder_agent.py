"""Folder agent: one watcher process, many folders, driven by profiles.

Design (matches docs/folder-agents/README.md and config/folder_profiles.json):
  * The agent is the HANDS: it watches, scans, evaluates, and tags.
  * The hub is the BRAIN: it records decisions and performs file work.
  * The agent NEVER mutates files directly. It POSTs observations and
    review_required proposals to the hub.

There is deliberately NO script copied into each folder. Folders opt in via:
  1. config/folder_profiles.json  (central registry), or
  2. an optional .folderagent.json data-marker dropped in the folder itself.

Run:
    python folder_agent.py --once            # one scan pass over all profiles
    python folder_agent.py --watch           # keep watching (watchdog or polling)
    python folder_agent.py --once --path X    # scan a single ad-hoc folder

Env:
    FIHUB_BASE_URL   default http://127.0.0.1:10000
    FIHUB_API_TOKEN  sent as X-API-Token when set
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

BASE_URL = os.environ.get("FIHUB_BASE_URL", "http://127.0.0.1:10000")
API_TOKEN = os.environ.get("FIHUB_API_TOKEN", "")
PROFILES_PATH = Path(
    os.environ.get(
        "FIHUB_FOLDER_PROFILES",
        Path(__file__).resolve().parents[1] / "config" / "folder_profiles.json",
    )
)
MARKER_NAME = ".folderagent.json"

# Extensions grouped into content families (for the symptom engine).
FAMILIES = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".svg"},
    "video": {".mp4", ".mov", ".mkv", ".avi", ".webm"},
    "audio": {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
    "doc": {".pdf", ".docx", ".doc", ".xlsx", ".csv", ".md", ".txt", ".pptx"},
    "archive": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "code": {".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".c", ".cpp", ".cs"},
}
# Presence of any of these marks a folder as a protected project/app root.
PROJECT_MARKERS = {
    "package.json", "node_modules", ".git", "venv", ".venv", "pyproject.toml",
    "requirements.txt", "setup.py", "Cargo.toml", "go.mod", "composer.json",
    "package-lock.json", "pnpm-lock.yaml", ".env", "docker-compose.yml", "Dockerfile",
}


# ── config ──────────────────────────────────────────────────────────
def load_profiles() -> tuple[dict, list[dict]]:
    if not PROFILES_PATH.exists():
        return ({}, [])
    data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    return (data.get("defaults", {}), data.get("profiles", []))


def resolve_profile(path: Path, defaults: dict, profiles: list[dict]) -> dict:
    """Merge defaults < central profile < in-folder marker for one path."""
    merged = dict(defaults)
    for p in profiles:
        if p.get("path") and Path(p["path"]) == path:
            merged.update(p)
    marker = path / MARKER_NAME
    if marker.exists():
        try:
            merged.update(json.loads(marker.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    merged["path"] = str(path)
    return merged


# ── scan ────────────────────────────────────────────────────────────
def scan(path: Path, *, hash_dupes: bool = True) -> dict:
    files, folders = [], []
    for entry in path.iterdir():
        if entry.name == MARKER_NAME:
            continue
        if entry.is_dir():
            folders.append(entry.name)
        elif entry.is_file():
            stat = entry.stat()
            files.append({"name": entry.name, "ext": entry.suffix.lower(),
                          "size": stat.st_size, "mtime": stat.st_mtime})
    inv = {"path": str(path), "file_count": len(files), "folder_count": len(folders),
           "files": files, "folders": folders}
    if hash_dupes:
        inv["dupe_pairs"] = _find_dupes(path, files)
    return inv


def _find_dupes(path: Path, files: list[dict]) -> int:
    """Cheap duplicate signal: hash only within same-size clusters."""
    by_size: dict[int, list[str]] = {}
    for f in files:
        by_size.setdefault(f["size"], []).append(f["name"])
    pairs = 0
    for size, names in by_size.items():
        if len(names) < 2 or size == 0:
            continue
        seen: dict[str, int] = {}
        for name in names:
            try:
                digest = hashlib.sha256((path / name).read_bytes()).hexdigest()
            except OSError:
                continue
            seen[digest] = seen.get(digest, 0) + 1
        pairs += sum(c - 1 for c in seen.values() if c > 1)
    return pairs


# ── evaluate (the symptom engine) ───────────────────────────────────
def evaluate(inv: dict) -> dict:
    files = inv["files"]
    total = max(1, len(files))
    fam = Counter()
    for f in files:
        for name, exts in FAMILIES.items():
            if f["ext"] in exts:
                fam[name] += 1
                break
        else:
            fam["other"] += 1
    families = {k: round(v / total, 2) for k, v in fam.items()}

    names = {f["name"] for f in files} | set(inv["folders"])
    symptoms: list[dict] = []

    if names & PROJECT_MARKERS:
        symptoms.append(_sym("program_root_danger", "critical", 99,
                             f"markers: {sorted(names & PROJECT_MARKERS)}",
                             ["protect", "no_auto_move", "never_auto_delete"]))
    if families.get("image", 0) + families.get("video", 0) + families.get("audio", 0) >= 0.6:
        symptoms.append(_sym("media_dump", "medium", 90,
                             "media-heavy folder", ["separate_by_source_type_date"]))
    distinct_ext = len({f["ext"] for f in files if f["ext"]})
    if distinct_ext >= 6 and families.get("other", 0) >= 0.3:
        symptoms.append(_sym("extension_swamp", "medium", 75,
                             f"{distinct_ext} distinct extensions", ["split_by_family"]))
    if families.get("archive", 0) >= 0.25:
        symptoms.append(_sym("archive_pile", "medium", 80,
                             "archives mixed with live files", ["archive_lane_or_unpack_review"]))
    if inv.get("dupe_pairs", 0) > 0:
        symptoms.append(_sym("duplicate_cluster", "high", 85,
                             f"{inv['dupe_pairs']} identical pair(s) by hash",
                             ["choose_keeper", "review_before_delete"]))

    sev_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    risk = max((sev_rank[s["severity"]] for s in symptoms), default=0)
    risk_level = ["low", "medium", "high", "critical"][risk]

    blocked = ["delete_without_hash"]
    if any(s["symptom_id"] == "program_root_danger" for s in symptoms):
        blocked.append("rename_or_move_project_assets_without_review")

    return {
        "folder_path": inv["path"],
        "diagnosis_version": "file-intel-v1",
        "file_count": inv["file_count"],
        "content_families": families,
        "symptoms": symptoms,
        "risk_level": risk_level,
        "blocked_actions": blocked,
        "recommended_plan": _plan(symptoms),
    }


def _sym(sid, severity, confidence, evidence, actions) -> dict:
    return {"symptom_id": sid, "severity": severity, "confidence": confidence,
            "evidence": evidence, "recommended_actions": actions}


def _plan(symptoms: list[dict]) -> list[str]:
    plan = ["snapshot", "scan"]
    if any(s["symptom_id"] == "duplicate_cluster" for s in symptoms):
        plan.append("hash_duplicates")
    if any(s["symptom_id"] in ("media_dump", "extension_swamp") for s in symptoms):
        plan.append("separate_by_source_type_date")
    plan += ["preview", "approve", "record_ledger"]
    return plan


# ── tag (writes a data sidecar, reversible; not file content) ───────
def write_marker(path: Path, diagnosis: dict, profile: dict) -> None:
    marker = path / MARKER_NAME
    payload = {
        "folder_role": profile.get("folder_role", "general"),
        "protected": profile.get("protected", False)
                     or diagnosis["risk_level"] == "critical",
        "last_diagnosis": {
            "risk_level": diagnosis["risk_level"],
            "symptoms": [s["symptom_id"] for s in diagnosis["symptoms"]],
            "content_families": diagnosis["content_families"],
        },
    }
    marker.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ── hub client (stdlib only) ────────────────────────────────────────
def hub_post(route: str, body: dict) -> tuple[int, str]:
    req = urllib.request.Request(
        BASE_URL + route, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 **({"X-API-Token": API_TOKEN} if API_TOKEN else {})},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]
    except urllib.error.URLError as e:
        return 0, f"unreachable: {e.reason}"


def report_to_hub(diagnosis: dict, *, offline: bool) -> None:
    symptom_ids = [s["symptom_id"] for s in diagnosis["symptoms"]]
    summary = (f"Diagnosed {diagnosis['folder_path']} — risk {diagnosis['risk_level']}, "
               f"symptoms: {symptom_ids or 'none'}")
    # Structured observation travels in metadata so the hub/desk can render the
    # full diagnosis, not just the summary line. Observation only -- no file work.
    payload = {
        "source_id": "folder-agent",
        "source_label": "Folder Agent",
        "role": "assistant",
        "folder": "Folder Agent",
        "body": summary,
        "pinned": diagnosis["risk_level"] == "critical",
        "metadata": {
            "kind": "folder_diagnosis",
            "folder_path": diagnosis["folder_path"],
            "risk_level": diagnosis["risk_level"],
            "file_count": diagnosis["file_count"],
            "content_families": diagnosis["content_families"],
            "symptoms": diagnosis["symptoms"],
            "blocked_actions": diagnosis["blocked_actions"],
            "recommended_plan": diagnosis["recommended_plan"],
        },
    }
    if offline:
        print("   [offline] " + summary)
        return
    status, _ = hub_post("/top-of-mind/messages", payload)
    print(f"   -> hub /messages: {status}")


# ── run ─────────────────────────────────────────────────────────────
def process(path: Path, defaults: dict, profiles: list[dict], *,
            offline: bool, do_tag: bool) -> dict:
    profile = resolve_profile(path, defaults, profiles)
    inv = scan(path)
    diagnosis = evaluate(inv)
    print(f"[{diagnosis['risk_level'].upper():8}] {path}  "
          f"({inv['file_count']} files)  "
          f"symptoms: {[s['symptom_id'] for s in diagnosis['symptoms']] or '-'}")
    if do_tag and not profile.get("protected", False):
        write_marker(path, diagnosis, profile)
    report_to_hub(diagnosis, offline=offline)
    return diagnosis


def watched_paths(defaults, profiles) -> list[Path]:
    out = []
    for p in profiles:
        raw = p.get("path")
        if raw and Path(raw).is_dir() and p.get("watch_enabled", defaults.get("watch_enabled", True)):
            out.append(Path(raw))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Top of Mind folder agent (watch/scan/evaluate/tag).")
    ap.add_argument("--once", action="store_true", help="single scan pass, then exit")
    ap.add_argument("--watch", action="store_true", help="keep watching (watchdog or polling)")
    ap.add_argument("--path", help="scan a single ad-hoc folder instead of the profiles")
    ap.add_argument("--tag", action="store_true", help="write .folderagent.json markers (off by default)")
    ap.add_argument("--offline", action="store_true", help="print instead of POSTing to the hub")
    ap.add_argument("--interval", type=int, default=15, help="polling seconds for --watch fallback")
    args = ap.parse_args()

    defaults, profiles = load_profiles()
    targets = [Path(args.path)] if args.path else watched_paths(defaults, profiles)
    if not targets:
        print("No folders to watch. Add paths to folder_profiles.json or pass --path.")
        return

    def sweep():
        for t in targets:
            if t.is_dir():
                process(t, defaults, profiles, offline=args.offline, do_tag=args.tag)

    print(f"Folder agent | hub={BASE_URL} | targets={len(targets)} | "
          f"mode={'observe+propose (read-only)'}")
    sweep()
    if args.watch:
        print(f"Watching (polling every {args.interval}s). Ctrl+C to stop.")
        seen = {t: _fingerprint(t) for t in targets}
        try:
            while True:
                time.sleep(args.interval)
                for t in targets:
                    fp = _fingerprint(t)
                    if fp != seen.get(t):
                        seen[t] = fp
                        process(t, defaults, profiles, offline=args.offline, do_tag=args.tag)
        except KeyboardInterrupt:
            print("\nstopped.")


def _fingerprint(path: Path) -> tuple:
    try:
        return tuple(sorted((e.name, e.stat().st_mtime, e.stat().st_size)
                            for e in path.iterdir() if e.is_file() and e.name != MARKER_NAME))
    except OSError:
        return ()


if __name__ == "__main__":
    main()
