"""FIS Context-Aware Folder Classifier — Chow-style decomposition.

Strategy:
1. Scan all folders first, build a "folder context" for each
2. Process loose root files FIRST (hardest — no folder context)
3. Then process each folder: read folder name + sibling files,
   determine min-pattern decomposition, classify with context prior
4. Files already classified in the DB are left alone unless forced

The Chow insight: Can 1 equation explain the whole folder?
If yes -> P(1 pattern) = high, classify everything under it
If not -> split into 2, 3... until each cluster is uniform
"""
import sys, os, re
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fis.nlp.extractor import extract_text
from fis.nlp.engines import YakeEngine
from fis.nlp.path_heuristics import _tokenize_filename as tokenize_name, SYSTEM_FILE_NAMES, CODE_EXTENSIONS, SYSTEM_EXTENSIONS
from fis.db.connection import get_connection
from fis.log import get_logger

log = get_logger("context_classifier")

# Domain signal word sets (same as path_heuristics but used for context)
TP_SIGNALS = {
    'theophysics', 'coherence', 'axiom', 'grace', 'entropy', 'quantum',
    'faith', 'logos', 'moral', 'resurrection', 'salvation', 'isomorphism',
    'trinity', 'christ', 'jesus', 'prayer', 'spirit', 'spiritual',
    'church', 'bible', 'prophecy', 'kingdom', 'redemption', 'sin',
    'judgment', 'hope', 'restoration', 'decline', 'equation', 'master',
    'chi', 'lagrangian', 'framework', 'god', 'prayer', 'scripture',
    'covenant', 'atonement', 'holiness', 'sanctification',
    'consciousness', 'observer', 'qualia', 'free will', 'collapse',
    'decoherence', 'entanglement', 'wavefunction',
}
SY_SIGNALS = {
    'install', 'setup', 'config', 'readme', 'build', 'deploy',
    'webpack', 'server', 'api', 'endpoint', 'pipeline', 'watcher',
    'handler', 'test', 'spec', 'debug', 'sync', 'migrate', 'schema',
    'script', 'batch', 'autostart', 'converter', 'dashboard',
    'download', 'transcribe', 'powershell', 'python', 'run',
}
DT_SIGNALS = {
    'trade', 'trading', 'stock', 'option', 'ticker', 'backtest',
    'setup', 'entry', 'exit', 'pnl', 'spy', 'qqq', 'chart',
    'candle', 'breakout', 'swing', 'scalp',
}
EV_SIGNALS = {
    'sellvia', 'fraud', 'scam', 'evidence', 'court', 'legal',
    'witness', 'deposition', 'testimony',
}


def compute_folder_context(folder_path: Path) -> dict:
    """Pre-read a folder to build a classification context.

    Returns:
        domain: most likely domain for the folder
        confidence: how sure we are (based on Chow decomposition)
        n_patterns: minimum number of clusters needed
        top_tokens: most frequent meaningful tokens
        file_count: number of files
    """
    files = [f for f in folder_path.rglob('*') if f.is_file()
             and not f.name.startswith('.')]

    if not files:
        return {"domain": None, "confidence": 0, "n_patterns": 0,
                "top_tokens": [], "file_count": 0}

    # Collect tokens from folder name + all filenames
    folder_tokens = tokenize_name(folder_path.name)
    all_tokens = list(folder_tokens) * 3  # Folder name weighted 3x

    ext_counts = Counter()
    for f in files:
        all_tokens.extend(tokenize_name(f.name))
        ext_counts[f.suffix.lower()] += 1

    token_freq = Counter(all_tokens)
    top_tokens = token_freq.most_common(10)
    total = sum(token_freq.values())

    # Domain scoring from token overlap
    token_set = set(t for t, _ in token_freq.most_common(30))
    tp_score = len(token_set & TP_SIGNALS)
    sy_score = len(token_set & SY_SIGNALS)
    dt_score = len(token_set & DT_SIGNALS)
    ev_score = len(token_set & EV_SIGNALS)

    # Extension-based scoring
    code_count = sum(ext_counts.get(e, 0) for e in CODE_EXTENSIONS)
    sys_count = sum(ext_counts.get(e, 0) for e in SYSTEM_EXTENSIONS)
    if code_count > len(files) * 0.5:
        sy_score += 5
    if sys_count > len(files) * 0.5:
        sy_score += 3

    scores = {"TP": tp_score, "SY": sy_score, "DT": dt_score, "EV": ev_score}
    best_domain = max(scores, key=scores.get)
    best_score = scores[best_domain]

    # Chow decomposition: how many patterns needed?
    top3_mass = sum(c for _, c in token_freq.most_common(3))
    coverage = top3_mass / total if total > 0 else 0

    if coverage > 0.4:
        n_patterns = 1
        base_conf = 85.0
    elif coverage > 0.25:
        n_patterns = 2
        base_conf = 65.0
    else:
        n_patterns = 3
        base_conf = 45.0

    # Adjust confidence by domain signal strength
    if best_score >= 5:
        confidence = min(base_conf + 10, 95.0)
    elif best_score >= 3:
        confidence = base_conf
    elif best_score >= 1:
        confidence = max(base_conf - 15, 30.0)
    else:
        confidence = max(base_conf - 25, 20.0)

    return {
        "domain": best_domain if best_score > 0 else None,
        "confidence": confidence,
        "n_patterns": n_patterns,
        "top_tokens": [t for t, _ in top_tokens],
        "file_count": len(files),
        "scores": scores,
        "coverage": coverage,
    }


def classify_with_context(file_path: Path, folder_context: dict = None) -> dict:
    """Classify a single file using both NLP and folder context.

    If folder_context is provided and strong (1-pattern, high confidence),
    it acts as a Bayesian prior — the file inherits the folder's domain
    unless the NLP strongly disagrees.
    """
    from fis.pipeline import FISPipeline

    pipeline = FISPipeline()
    result = pipeline.process(str(file_path))

    if result.get("status") == "duplicate" or result.get("error"):
        return result

    # If we have folder context and it's strong, apply it
    if folder_context and folder_context.get("domain"):
        ctx_domain = folder_context["domain"]
        ctx_conf = folder_context["confidence"]
        ctx_patterns = folder_context["n_patterns"]

        file_domain = result.get("domain", "--")

        if ctx_patterns == 1 and ctx_conf >= 70:
            # UNIFORM folder — strong prior. Override unless NLP is very confident
            # in a different domain
            if file_domain != ctx_domain and result.get("confidence", 0) < 85:
                result["domain"] = ctx_domain
                result["confidence"] = max(ctx_conf - 10, 50.0)
                result["_context"] = f"folder_uniform_override:{ctx_domain}"
                log.info("CTX OVERRIDE %s: %s -> %s (folder uniform)",
                         file_path.name, file_domain, ctx_domain)
            elif file_domain == ctx_domain:
                # Agreement — boost confidence
                result["confidence"] = min(result["confidence"] + 15, 100.0)
                result["_context"] = f"folder_confirm:{ctx_domain}"

        elif ctx_patterns == 2 and ctx_conf >= 50:
            # SPLIT folder — weaker prior, but still useful
            if file_domain == "--" or result.get("confidence", 0) < 50:
                result["domain"] = ctx_domain
                result["confidence"] = max(ctx_conf - 20, 35.0)
                result["_context"] = f"folder_split_fallback:{ctx_domain}"

        # For MIXED folders (3+ patterns), context is too weak to override

    return result


def process_desktop_stay(root: str = r"B:\transfer\Desktop STAY",
                         dry_run: bool = True, force: bool = False):
    """Process Desktop STAY with context-aware classification.

    Order:
    1. Loose files in root (no folder context — hardest)
    2. Each folder (with folder context)

    Args:
        dry_run: If True, just show what would happen
        force: If True, reclassify even if file is already in DB
    """
    root_path = Path(root)
    if not root_path.exists():
        print(f"ERROR: {root} not found")
        return

    # Separate folders and loose files
    dirs = sorted([d for d in root_path.iterdir() if d.is_dir()
                   and not d.name.startswith('.')])
    loose_files = sorted([f for f in root_path.iterdir() if f.is_file()
                          and not f.name.startswith('.')
                          and f.name != 'desktop.ini'])

    print(f"\n{'='*60}")
    print(f"FIS CONTEXT-AWARE CLASSIFICATION")
    print(f"Root: {root}")
    print(f"{len(loose_files)} loose files, {len(dirs)} folders")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}")

    # === PHASE 1: LOOSE FILES (no context, honest baseline) ===
    print(f"\n--- PHASE 1: LOOSE FILES ({len(loose_files)}) ---")
    print("These have no folder context. Classification is NLP + heuristics only.")
    print("Short names and ambiguous files get lower confidence — that's correct.\n")

    for f in loose_files:
        tokens = tokenize_name(f.name)
        token_count = len(tokens)
        ext = f.suffix.lower()

        # Quick pre-classification by extension
        if ext in CODE_EXTENSIONS | SYSTEM_EXTENSIONS | {'.bat', '.cmd', '.lnk', '.ini'}:
            domain_hint = "SY"
        elif ext in {'.mp3', '.mp4', '.wav'}:
            domain_hint = "MD"
        else:
            domain_hint = None

        # Filename length assessment
        if token_count <= 1:
            difficulty = "HARD"
        elif token_count <= 2:
            difficulty = "MEDIUM"
        else:
            difficulty = "EASY"

        if dry_run:
            print(f"  [{difficulty:6s}] {f.name[:55]:55s} ext={ext:5s} "
                  f"tok={token_count} hint={domain_hint or '--'}")
        else:
            result = classify_with_context(f, folder_context=None)
            status = result.get("status", "?")
            domain = result.get("domain", "--")
            conf = result.get("confidence", 0)
            print(f"  [{status:9s}] {f.name[:45]:45s} -> {domain} "
                  f"({conf:.0f}%) {result.get('_heuristic', '')}")

    # === PHASE 2: FOLDERS (with context) ===
    print(f"\n--- PHASE 2: FOLDERS ({len(dirs)}) ---")

    for d in dirs:
        if d.name.startswith('_') or d.name == 'ParameterExplorer':
            continue

        ctx = compute_folder_context(d)
        if ctx["file_count"] == 0:
            print(f"\n  [{d.name}] EMPTY — skipping")
            continue

        label = {1: "UNIFORM", 2: "SPLIT"}.get(ctx["n_patterns"], "MIXED")
        print(f"\n  [{d.name}] {ctx['file_count']} files  "
              f"{label} -> {ctx['domain'] or '??'} ({ctx['confidence']:.0f}%)  "
              f"scores={ctx['scores']}  top={ctx['top_tokens'][:5]}")

        if not dry_run:
            # Process each file in the folder with context
            folder_files = sorted(f for f in d.rglob('*') if f.is_file()
                                  and not f.name.startswith('.'))
            for f in folder_files:
                result = classify_with_context(f, folder_context=ctx)
                status = result.get("status", "?")
                domain = result.get("domain", "--")
                conf = result.get("confidence", 0)
                ctx_flag = result.get("_context", "")
                print(f"    [{status:9s}] {f.name[:40]:40s} -> {domain} "
                      f"({conf:.0f}%) {ctx_flag}")

    print(f"\n{'='*60}")
    print(f"DONE. {'DRY RUN — no changes made.' if dry_run else 'Classification complete.'}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Actually classify (default: dry run)")
    parser.add_argument("--force", action="store_true", help="Reclassify already-classified files")
    args = parser.parse_args()
    process_desktop_stay(dry_run=not args.live, force=args.force)
