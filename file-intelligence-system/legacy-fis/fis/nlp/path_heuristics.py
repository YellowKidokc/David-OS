"""Path and filename heuristics for FIS classification.

Two key insights from David:
1. Short filenames (1-2 words) are usually structural/system files.
   The NLP pipeline tries hardest on these and gets them WRONG because
   it's matching content trigger words against a file that is what it IS,
   not what it's ABOUT. "HEAD" is a git file, not a Theophysics doc
   about headship. "exclude" is a git config, not a moral alignment paper.

2. Long descriptive filenames tell you what the file is. The filename itself
   should be a classification input. "15_architecture_of_hope_restoration_path.html"
   is practically labeling itself.

3. Path contains domain truth. D:\\GitHub = system code. O:\\_Theophysics = TP.
   Moral decline of America folder = TP articles, not DT journal entries.
"""

import re
from pathlib import Path

from fis.log import get_logger

log = get_logger("path_heuristics")

# Known system file patterns — these are ALWAYS system files regardless of content
SYSTEM_FILE_NAMES = {
    'head', 'exclude', 'config', 'index', 'description', 'packed-refs',
    'fetch_head', 'commit_editmsg', 'license', 'licence', 'changelog',
    'makefile', 'dockerfile', 'vagrantfile', 'gemfile', 'rakefile',
    'procfile', 'brewfile', 'cmakelists.txt', 'package.json',
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    'tsconfig.json', 'jsconfig.json', 'webpack.config.js',
    '.gitignore', '.gitattributes', '.editorconfig',
    'requirements.txt', 'setup.py', 'setup.cfg', 'pyproject.toml',
    'cargo.toml', 'cargo.lock', 'go.mod', 'go.sum',
}

SYSTEM_EXTENSIONS = {
    '.bat', '.cmd', '.ps1', '.sh', '.bash', '.zsh',
    '.ini', '.cfg', '.conf', '.toml', '.yaml', '.yml',
    '.json', '.lock', '.pid', '.env',
}

CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.rs', '.go',
    '.java', '.cs', '.cpp', '.c', '.h', '.rb', '.php',
    '.swift', '.kt', '.lua', '.r', '.sql', '.ahk',
}


def _tokenize_filename(name: str) -> list[str]:
    """Split filename into meaningful tokens.
    'HEAD' -> ['head']
    '15_architecture_of_hope_restoration_path' -> ['architecture', 'hope', 'restoration', 'path']
    'obsidian_postgres_sync.py' -> ['obsidian', 'postgres', 'sync']
    """
    stem = Path(name).stem
    # Remove leading numbers and underscores
    stem = re.sub(r'^\d+[_\-]*', '', stem)
    # Split on underscores, hyphens, camelCase, dots
    tokens = re.split(r'[_\-.\s]+', stem)
    # Also split camelCase
    expanded = []
    for token in tokens:
        parts = re.sub(r'([a-z])([A-Z])', r'\1 \2', token).split()
        expanded.extend(parts)
    # Filter empty and very short tokens
    return [t.lower() for t in expanded if len(t) > 1]


def apply_filename_heuristic(classification: dict, filename: str, ext: str) -> dict:
    """Apply filename-length heuristic to adjust classification confidence.

    Short names (1-2 tokens): NLP is probably wrong. Penalize confidence.
    The classifier matched content trigger words but the file is probably
    structural. Trust extension and name pattern over NLP content analysis.

    Long names (4+ tokens): The filename is self-describing. Parse it as
    a supplementary classification signal — it should AGREE with the NLP
    result, and if it doesn't, that's a red flag.
    """
    result = dict(classification)
    name_lower = filename.lower()
    stem_lower = Path(filename).stem.lower()
    ext_lower = ext.lower()
    tokens = _tokenize_filename(filename)
    token_count = len(tokens)

    # === HARD OVERRIDES (known system files) ===
    if stem_lower in SYSTEM_FILE_NAMES or name_lower in SYSTEM_FILE_NAMES:
        result["domain"] = "SY"
        result["subjects"] = ["CF"]
        result["confidence"] = 75.0
        result["_heuristic"] = "known_system_file"
        log.debug("OVERRIDE %s -> SY/CF (known system file)", filename)
        return result

    if ext_lower in SYSTEM_EXTENSIONS:
        if result["domain"] not in ("SY",):
            # System extension but classified as something else — suspicious
            result["confidence"] = max(result["confidence"] - 25, 10.0)
            result["_heuristic"] = "system_ext_penalty"
            log.debug("PENALTY %s: system extension, -25 confidence", filename)

    if ext_lower in CODE_EXTENSIONS:
        if result["domain"] not in ("SY", "CB"):
            # Code file classified as content — probably wrong
            result["domain"] = "SY"
            result["subjects"] = ["SC"]
            result["confidence"] = 70.0
            result["_heuristic"] = "code_extension_override"
            log.debug("OVERRIDE %s -> SY/SC (code extension)", filename)
            return result

    # === SHORT FILENAME PENALTY (1-2 tokens) ===
    # "HEAD", "index", "exclude", "config" — NLP is reading content
    # and hallucinating domain matches. These are structural files.
    if token_count <= 2:
        # The fewer tokens, the less the filename tells us,
        # so the MORE we should distrust content-based NLP
        penalty = 30 if token_count <= 1 else 20
        result["confidence"] = max(result["confidence"] - penalty, 10.0)
        result["_heuristic"] = f"short_name_penalty_{token_count}tok"
        log.debug("PENALTY %s: %d-token name, -%d confidence", filename, token_count, penalty)

    # === LONG FILENAME BOOST (4+ tokens) ===
    # The name is descriptive enough to BE a classification signal.
    # If the name tokens agree with the classification, boost confidence.
    # If they disagree, flag it.
    elif token_count >= 4:
        # Check if filename tokens contain domain-relevant words
        tp_signals = {'theophysics', 'coherence', 'axiom', 'grace', 'entropy',
                      'quantum', 'faith', 'logos', 'moral', 'resurrection',
                      'salvation', 'isomorphism', 'trinity', 'christ', 'jesus',
                      'prayer', 'spirit', 'spiritual', 'church', 'bible',
                      'prophecy', 'kingdom', 'redemption', 'sin', 'judgment',
                      'hope', 'restoration', 'decline', 'architecture',
                      'framework', 'equation', 'master', 'chi', 'lagrangian'}
        dt_signals = {'trade', 'trading', 'stock', 'option', 'ticker',
                      'backtest', 'setup', 'entry', 'exit', 'pnl',
                      'spy', 'qqq', 'chart', 'candle', 'breakout'}
        sy_signals = {'install', 'setup', 'config', 'readme', 'build',
                      'deploy', 'webpack', 'server', 'api', 'endpoint',
                      'pipeline', 'watcher', 'handler', 'test', 'spec',
                      'debug', 'sync', 'migrate', 'schema'}

        token_set = set(tokens)
        tp_hits = len(token_set & tp_signals)
        dt_hits = len(token_set & dt_signals)
        sy_hits = len(token_set & sy_signals)

        if result["domain"] == "TP" and tp_hits > 0:
            result["confidence"] = min(result["confidence"] + 10, 100.0)
            result["_heuristic"] = "long_name_tp_confirm"
        elif result["domain"] == "DT" and tp_hits > dt_hits:
            # Filename says TP but classifier said DT — override
            result["domain"] = "TP"
            result["confidence"] = max(result["confidence"] - 10, 40.0)
            result["_heuristic"] = "long_name_tp_override_dt"
            log.debug("OVERRIDE %s: name says TP, classifier said DT", filename)
        elif result["domain"] not in ("SY",) and sy_hits > 0 and sy_hits >= tp_hits:
            result["confidence"] = max(result["confidence"] - 15, 30.0)
            result["_heuristic"] = "long_name_sy_signal"

    return result


def apply_path_rules(classification: dict, file_path: str) -> dict:
    """Apply path-based heuristics from both hardcoded rules and DB table.

    Path is the strongest signal we have for domain. A .py file in D:\\GitHub
    is system code. An .html file in Moral Decline folder is a TP article.
    The NLP pipeline ignores path entirely — this fixes that.
    """
    result = dict(classification)
    path_lower = file_path.lower()

    # Hardcoded high-priority rules (faster than DB lookup)
    path_rules = [
        # Git internals — always SY
        ('.git\\', 'SY', ['GT'], 50),
        ('.git/', 'SY', ['GT'], 50),
        # GitHub repos — almost always SY/code
        ('\\github\\', 'SY', ['SC'], 25),
        ('/github/', 'SY', ['SC'], 25),
        # Theophysics vault — always TP
        ('_theophysics', 'TP', None, 15),
        # Moral Decline articles — TP, not DT
        ('moral decline', 'TP', ['MR'], 30),
        ('moral-decline', 'TP', ['MR'], 30),
        # ShareX — system config
        ('sharex', 'SY', ['CF'], 30),
        # node_modules — always SY
        ('node_modules', 'SY', ['SC'], 50),
        # EXPORT folder — media/content
        ('\\export\\', 'MD', ['EX'], 10),
    ]

    best_match = None
    best_boost = 0

    for pattern, domain, subjects, boost in path_rules:
        if pattern in path_lower and boost > best_boost:
            best_match = (domain, subjects, boost)
            best_boost = boost

    if best_match:
        domain, subjects, boost = best_match

        if boost >= 40:
            # Hard override — path is authoritative
            result["domain"] = domain
            if subjects:
                result["subjects"] = subjects
            result["confidence"] = max(result["confidence"], 70.0)
            result["_path_rule"] = f"hard_override:{domain}"
            log.debug("PATH HARD %s -> %s (boost %d)", file_path[-50:], domain, boost)
        elif result["domain"] != domain:
            # Soft override — path disagrees with NLP, adjust
            if boost >= 25:
                result["domain"] = domain
                if subjects:
                    # Merge subjects: keep first from path, rest from NLP
                    existing = [s for s in result.get("subjects", []) if s not in subjects]
                    result["subjects"] = subjects + existing[:2]
                result["confidence"] = max(result["confidence"] - 10, 40.0)
                result["_path_rule"] = f"soft_override:{domain}"
                log.debug("PATH SOFT %s -> %s", file_path[-50:], domain)
            else:
                # Weak signal — just penalize confidence if domains disagree
                result["confidence"] = max(result["confidence"] - 10, 30.0)
                result["_path_rule"] = f"weak_disagree:{domain}"
        else:
            # Path agrees with NLP — small confidence boost
            result["confidence"] = min(result["confidence"] + boost // 3, 100.0)
            result["_path_rule"] = f"confirm:{domain}"

    # Also try DB-based path_rules if table exists
    try:
        _apply_db_path_rules(result, path_lower)
    except Exception:
        pass  # Table might not exist yet

    return result


def _apply_db_path_rules(result: dict, path_lower: str):
    """Check path_rules table for additional rules."""
    from fis.db.models import _db

    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pattern, domain, subjects, confidence_boost
                FROM path_rules
                WHERE is_active = TRUE
                ORDER BY priority DESC
            """)
            for row in cur.fetchall():
                pattern = row[0].lower() if row[0] else ''
                if pattern in path_lower:
                    db_domain = row[1]
                    db_subjects = row[2]
                    db_boost = row[3] or 10
                    if db_domain and result["domain"] != db_domain and db_boost >= 20:
                        result["domain"] = db_domain
                        if db_subjects:
                            result["subjects"] = list(db_subjects)
                        result["_path_rule_db"] = f"db:{db_domain}"
                    break  # First match wins (highest priority)
