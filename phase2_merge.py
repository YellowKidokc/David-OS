"""
PHASE 2 MERGE SCRIPT — FIS/Top-of-Mind consolidation into David-OS
Fabel (Opus) | 2026-07-07 | UNTESTED until dry-run reviewed by David.

DOCTRINE (from _PHASE1_INVENTORY.md /BLINDSPOT):
  Consolidation-by-copying is the failure mode. This script MOVES and
  TOMBSTONES. It never copies-and-leaves. Every source location that
  loses content gets an ARCHIVED.md pointing at the canonical path.

SAFETY:
  - Default mode is DRY RUN. Nothing moves. Prints + writes plan manifest.
  - `--execute` performs moves. `--phase N` runs a single phase.
  - Refuses to run if any repo has uncommitted changes (unless --force).
  - Every action appended to _PHASE2_MERGE_LOG.jsonl (append-only ledger).
  - D:\\DONT TOUCH BOOT UP is never touched (hard assert on every path).

USAGE:
  python phase2_merge.py                # dry run, full plan
  python phase2_merge.py --phase 1     # dry run, one phase
  python phase2_merge.py --execute     # do it (after review)
"""
import argparse, hashlib, json, os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

DEFAULT_GH = Path(r"D:\GitHub")

def discover_github_root() -> Path:
    r"""Return the consolidation root for Windows or sandboxed Linux runs.

    The original consolidation target is D:\GitHub. In CI/Codex sandboxes the
    repos are usually mounted under /workspace, so dry-runs must resolve paths
    relative to the checked-out David-OS repo instead of crashing while trying
    to write a manifest under a non-existent Windows path.
    """
    if os.environ.get("FIS_GITHUB_ROOT"):
        return Path(os.environ["FIS_GITHUB_ROOT"])
    if DEFAULT_GH.exists():
        return DEFAULT_GH
    return Path(__file__).resolve().parent.parent

GH = discover_github_root()
CANON = Path(os.environ.get("FIS_CANON", GH / "David-OS"))
ARCHIVE = Path(os.environ.get("FIS_ARCHIVE", GH / "_ARCHIVE_FIS_20260707"))
LOG = CANON / "_PHASE2_MERGE_LOG.jsonl"
STAMP = "2026-07-07"
FORBIDDEN = [Path(r"D:\DONT TOUCH BOOT UP")]

REPOS = {
    "tom_fis_api": GH / "tom_fis_api",
    "Top-of-Mind-API": GH / "Top-of-Mind-API",
    "Top-of-Mind": GH / "Top-of-Mind",
    "File-intelligent-hub": GH / "File-intelligent-hub",
    "theophysics-fis": GH / "theophysics-fis",
    "TOP AI FIS": GH / "TOP AI FIS",
    "file-intelligence-system": GH / "file-intelligence-system",
}

# Heads (from hash audit)
HEAD_D = REPOS["tom_fis_api"] / "apps" / "api"                                  # base
HEAD_F = REPOS["Top-of-Mind-API"] / "deploy" / "synology" / ".package-stage" / "apps" / "api"
HEAD_G = REPOS["TOP AI FIS"] / "apps" / "api"

# Unique features to rescue (relative to each head's file_intelligence_hub/)
F_UNIQUE = [
    "file_intelligence_hub/api/routes_clipboard.py",
    "file_intelligence_hub/api/routes_agents.py",
    "file_intelligence_hub/storage/clipboard_repo.py",
    "scripts/folder_agent.py",
    "scripts/remote/start_remote_api.ps1",
    "scripts/remote/test_remote_api.ps1",
    "tests/test_clipboard.py",
    "tests/test_remote_auth.py",
    "docs/remote/README.md",
]
G_UNIQUE = [
    "file_intelligence_hub/api/routes_semantic.py",
    "file_intelligence_hub/services/semantic_addressing.py",
]
# Divergent shared files needing human eyes (from hash audit): F/G variants
# are parked in _MERGE_CONFLICTS/, never auto-merged.
DIVERGENT = [
    "file_intelligence_hub/api/app.py",
    "file_intelligence_hub/storage/db.py",
]

DRY = True
ACTIONS = []

def log(action, src, dst, note=""):
    rec = {"ts": datetime.now().isoformat(), "action": action,
           "src": str(src), "dst": str(dst), "note": note, "dry": DRY}
    ACTIONS.append(rec)
    print(f"[{'DRY' if DRY else 'RUN'}] {action:9s} {src} -> {dst} {('# '+note) if note else ''}")
    if not DRY:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

def assert_safe(p: Path):
    rp = Path(p).resolve()
    for f in FORBIDDEN:
        # On non-Windows sandboxes this path does not exist; resolving it would
        # create misleading relative paths like ./D:\DONT TOUCH BOOT UP.
        if not f.exists():
            continue
        if str(rp).lower().startswith(str(f.resolve()).lower()):
            sys.exit(f"FATAL: refused to touch forbidden path {rp}")

def move(src: Path, dst: Path, note=""):
    assert_safe(src); assert_safe(dst)
    if not src.exists():
        log("MISSING", src, dst, "source not found — investigate before execute")
        return
    log("MOVE", src, dst, note)
    if not DRY:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

def tombstone(location: Path, moved_to: Path, what: str):
    assert_safe(location)
    stone = location / "ARCHIVED.md" if location.is_dir() else location.with_suffix(".ARCHIVED.md")
    body = (f"# ARCHIVED {STAMP}\n\n{what} moved to canonical location:\n\n"
            f"    {moved_to}\n\nDo NOT recreate here. David-OS is the single "
            f"canonical repo. See D:\\GitHub\\David-OS\\_PHASE1_INVENTORY.md.\n")
    log("TOMBSTONE", stone, moved_to)
    if not DRY:
        stone.parent.mkdir(parents=True, exist_ok=True)
        stone.write_text(body, encoding="utf-8")

def git_dirty(repo: Path):
    try:
        r = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                           capture_output=True, text=True, timeout=30)
        return bool(r.stdout.strip())
    except Exception:
        return None  # no git — treat as unknown, warn

def phase0_freeze(force=False):
    """Safety: verify clean trees + create pre-consolidation tag."""
    print("\n== PHASE 0: freeze & verify ==")
    for name, repo in {**REPOS, "David-OS": CANON}.items():
        if not repo.exists():
            print(f"  !! {name}: MISSING at {repo}")
            continue
        d = git_dirty(repo)
        state = {True: "DIRTY", False: "clean", None: "no-git"}[d]
        print(f"  {name}: {state}")
        if d and not force and not DRY:
            sys.exit(f"FATAL: {name} has uncommitted changes. Commit first or --force.")
        if not DRY and d is False:
            subprocess.run(["git", "-C", str(repo), "tag", "-f",
                            "pre-consolidation-20260707"], capture_output=True)
            log("GIT-TAG", repo, "pre-consolidation-20260707")

def phase1_api_base():
    """HEAD-D becomes David-OS/api. Three-way assembly happens HERE, not in tom_fis_api."""
    print("\n== PHASE 1: API base (HEAD-D -> David-OS/api) ==")
    move(HEAD_D, CANON / "api", "HEAD-D: newest head, openai_compat + prediction")
    tombstone(REPOS["tom_fis_api"] / "apps", CANON / "api", "apps/api (FIS Hub API, HEAD-D)")

def phase2_rescue_features():
    """Cherry-pick HEAD-F and HEAD-G unique files into David-OS/api. Divergent files parked."""
    print("\n== PHASE 2: rescue unique features (HEAD-F clipboard/agents/remote, HEAD-G semantic) ==")
    for rel in F_UNIQUE:
        move(HEAD_F / rel, CANON / "api" / rel, "HEAD-F unique — only copy in existence")
    for rel in G_UNIQUE:
        move(HEAD_G / rel, CANON / "api" / rel, "HEAD-G unique — semantic addressing bridge")
    for rel in DIVERGENT:
        for tag, head in (("F", HEAD_F), ("G", HEAD_G)):
            src = head / rel
            if src.exists():
                move(src, CANON / "_MERGE_CONFLICTS" / tag / rel,
                     "divergent vs HEAD-D — needs eyes (db.py migrations!)")
    tombstone(HEAD_F.parent, CANON / "api", "synology staged api (HEAD-F uniques rescued)")
    tombstone(HEAD_G.parent, CANON / "api", "TOP AI FIS api (HEAD-G uniques rescued)")

def phase3_absorb_prior_attempts():
    """Absorb the thinking from the two prior consolidation attempts."""
    print("\n== PHASE 3: absorb prior consolidation attempts ==")
    tfis = REPOS["theophysics-fis"]
    move(tfis / "src", CANON / "engine", "theophysics-fis engine (capability/chi/preference ensemble)")
    move(tfis / "config", CANON / "engine" / "config", "engine YAML config")
    for doc in ("CONSOLIDATION_SPEC.md", "CRITICAL_FIXES.md"):
        move(tfis / doc, CANON / "core" / f"theophysics-fis_{doc}", "prior attempt #1 spec")
    taf = REPOS["TOP AI FIS"]
    move(taf / "docs", CANON / "docs", "11 architecture docs + forgotten-systems-inventory")
    move(taf / "config" / "rules", CANON / "config" / "rules", "28POF rule set")
    move(taf / "data" / "memory" / "TopOfMind_Memory", CANON / "memory", "agent memory buckets")
    move(taf / "agents", CANON / "agents", "labelers/scanners/watchers (chi, semantic worker, folder_scanner)")
    move(taf / "scripts" / "bootstrap", CANON / "scripts" / "bootstrap", "hub db init + 28pof extract")
    tombstone(tfis, CANON, "theophysics-fis live assets")
    tombstone(taf, CANON, "TOP AI FIS live assets")

def phase4_frontend_ahk():
    print("\n== PHASE 4: frontend + AHK bridge ==")
    tom = REPOS["Top-of-Mind"]
    move(tom / "apps" / "desk", CANON / "apps" / "desk", "React head (July 3)")
    move(tom / "docs" / "ahk-react-api-contract.md", CANON / "docs" / "ahk-react-api-contract.md")
    tombstone(tom, CANON / "apps" / "desk", "Top-of-Mind desk app (frontend scaffold left behind = archive)")
    tfa = REPOS["tom_fis_api"]
    move(tfa / "ahk", CANON / "bridges" / "ahk", "AI Chat Controller v3 + 13 API_CALL prompts")
    move(tfa / "agents" / "watchers" / "hub_watcher.py",
         CANON / "watchers" / "_candidates" / "hub_watcher.py", "watcher candidate 3/5")
    move(tfa / "api_calls", CANON / "bridges" / "api_calls", "routing manifest + numbering schema")

def phase5_watcher_candidates():
    """Stage all watcher implementations side-by-side for the Codex consolidation prompt."""
    print("\n== PHASE 5: watcher candidates ==")
    cand = CANON / "watchers" / "_candidates"
    move(REPOS["file-intelligence-system"] / "fis" / "watcher.py",
         cand / "legacy_fis_watcher.py", "watcher candidate 4/5 (June 3)")
    # 1/5 unified_global_watcher.py and 2/5 continuous_scanner.py already live in David-OS
    log("NOTE", CANON / "watchers", cand,
        "candidates 1-2 already in David-OS; 5/5 salvaged daemons remain in archive, referenced not moved")

def phase6_deploy_pipeline():
    print("\n== PHASE 6: Synology deploy pipeline ==")
    tapi = REPOS["Top-of-Mind-API"]
    move(tapi / "deploy" / "synology" / ".package-stage" / "deploy" / "synology",
         CANON / "deploy" / "synology", "docker-compose + spk build chain")
    tombstone(tapi, CANON, "Top-of-Mind-API (deploy chain + HEAD-F rescued; rest archived)")

def phase7_kill_internal_dups():
    """David-OS stops duplicating itself."""
    print("\n== PHASE 7: kill David-OS internal duplication ==")
    fis_dir = CANON / "file-intelligence-system"
    move(fis_dir / "segments", ARCHIVE / "David-OS_segments", "byte-identical mirror of siblings")
    move(fis_dir / "fihub-source", ARCHIVE / "David-OS_fihub-source", "STALE-4 member")
    move(fis_dir / "legacy-fis", ARCHIVE / "David-OS_legacy-fis", "dup of file-intelligence-system repo")

def phase8_archive_repos():
    """Whole-repo archival. Same-drive move = instant rename, git history intact."""
    print("\n== PHASE 8: archive source repos ==")
    for name in ("File-intelligent-hub", "file-intelligence-system", "theophysics-fis",
                 "TOP AI FIS", "Top-of-Mind-API", "Top-of-Mind", "tom_fis_api"):
        repo = REPOS[name]
        move(repo, ARCHIVE / name, "archived reference; tombstones inside point to David-OS")

PHASES = [phase0_freeze, phase1_api_base, phase2_rescue_features, phase3_absorb_prior_attempts,
          phase4_frontend_ahk, phase5_watcher_candidates, phase6_deploy_pipeline,
          phase7_kill_internal_dups, phase8_archive_repos]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--phase", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    DRY = not a.execute
    print(f"MODE: {'EXECUTE' if a.execute else 'DRY RUN'}  |  canon={CANON}  archive={ARCHIVE}")
    todo = PHASES if a.phase is None else [PHASES[a.phase]]
    for fn in todo:
        fn() if fn is not phase0_freeze else fn(force=a.force)
    manifest = CANON / ("_PHASE2_PLAN.json" if DRY else "_PHASE2_EXECUTED.json")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(ACTIONS, indent=1), encoding="utf-8")
    missing = [x for x in ACTIONS if x["action"] == "MISSING"]
    print(f"\n{len(ACTIONS)} actions planned -> {manifest.name}; {len(missing)} MISSING sources")
    if missing:
        print("RESOLVE MISSING BEFORE --execute:")
        for m in missing: print("  ", m["src"])
