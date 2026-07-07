"""
FIS Folder Triage v2 — Compact, streaming, bulk-select, AI suggest
"""
import sys
import os
import re
import requests
from pathlib import Path
FIS_REPO = r"D:\GitHub\file-intelligence-system"
sys.path.insert(0, FIS_REPO)

import streamlit as st
import psycopg2
import psycopg2.extras
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────
DB = dict(host="192.168.1.97", port=5432, dbname="fis_db",
          user="postgres", password="Moss9pep28$")

DEFAULT_ROOTS = [
    r"B:\transfer\Desktop STAY",
    r"C:\Users\lowes\Documents",
    r"D:\GitHub",
    r"O:\_Theophysics_v4",
]

SKIP_DIRS = {".git", "__pycache__", ".obsidian", "node_modules", ".vs", "venv", ".venv"}

RATINGS = ["", "✅ keep", "✏️ rename", "🗑️ delete", "🔀 merge", "👀 review"]
RATING_VALS = {"✅ keep": "keep", "✏️ rename": "rename", "🗑️ delete": "delete",
               "🔀 merge": "merge", "👀 review": "review", "": ""}

# ── Word cluster — trigger word confidence scorer ──────────────────────────────
# Loaded once from Postgres subject_codes table. Used for local confidence scoring
# without any API call. This IS the semantic knowledge graph seed.

@st.cache_data(ttl=300)
def load_word_clusters() -> dict:
    """Load subject code trigger words from Postgres.
    Returns {code: {label, domain, words: set}}
    """
    rows = run("""
        SELECT code, label, domain, trigger_words, aliases
        FROM subject_codes ORDER BY domain, code
    """, fetch=True)
    clusters = {}
    for r in (rows or []):
        words = set()
        if r["trigger_words"]:
            words.update(w.lower() for w in r["trigger_words"])
        if r["aliases"]:
            words.update(a.lower() for a in r["aliases"])
        words.add(r["label"].lower())
        clusters[r["code"]] = {
            "label": r["label"],
            "domain": r["domain"],
            "words": words,
        }
    return clusters


def _tokenize(text: str) -> set:
    """Tokenize folder name or path — splits camelCase, underscores, hyphens, spaces."""
    # Split camelCase: ParameterExplorer -> Parameter Explorer
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)
    tokens = re.findall(r'[a-zA-Z]+', text.lower())
    # Also add the original unsplit version for compound words
    return set(tokens)

def score_folder_locally(folder_name: str, parent_path: str) -> dict:
    """Score using the real FIS NLP pipeline — YAKE + classifier + path heuristics."""
    try:
        from fis.nlp.engines import YakeEngine
        from fis.nlp.classifier import FISClassifier
        from fis.nlp.path_heuristics import apply_path_rules, apply_filename_heuristic
        import os

        text = folder_name.replace('_', ' ').replace('-', ' ')
        keywords = YakeEngine().extract(text)

        # Classify
        clf = FISClassifier(model_dir=os.path.join(
            r'D:\GitHub\file-intelligence-system', 'models', 'saved'))
        result = clf.classify(text, keywords, [])

        # Apply path heuristics
        result = apply_path_rules(result, parent_path)
        result = apply_filename_heuristic(result, folder_name, '')

        domain = result.get('domain', 'DC')
        subjects = result.get('subjects', ['GN'])
        subject = subjects[0] if subjects else 'GN'
        confidence = round(float(result.get('confidence', 50)), 1)

        return {
            "domain": domain,
            "subject": subject,
            "confidence": confidence,
            "keywords": [k["keyword"] for k in keywords[:3]],
        }

    except Exception as e:
        # Fallback to simple token matching if FIS pipeline fails
        clusters = load_word_clusters()
        name_tokens = _tokenize(folder_name)
        path_tokens = _tokenize(parent_path)
        best_code, best_domain, best_score, all_scores = None, "DC", 0, {}
        for code, cluster in clusters.items():
            score = (len(name_tokens & cluster["words"]) * 2) + len(path_tokens & cluster["words"])
            if code == "GN": score *= 0.4
            if score > 0: all_scores[code] = score
            if score > best_score:
                best_score, best_code, best_domain = score, code, cluster["domain"]
        total = sum(all_scores.values()) or 1
        conf = round(min((best_score / total) * 100, 95), 1) if best_score else 0
        return {"domain": best_domain, "subject": best_code or "GN",
                "confidence": conf, "keywords": [], "error": str(e)}


def get_next_seq_id() -> str:
    """Get next sequence ID from Postgres files table."""
    rows = run("SELECT COALESCE(MAX(CAST(sequence_id AS INTEGER)), 0) + 1 AS nxt FROM files WHERE sequence_id ~ '^[0-9]+$'", fetch=True)
    nxt = rows[0]["nxt"] if rows else 1
    return f"{nxt:06d}"


# ── Naming schema (injected into AI prompt) ────────────────────────────────────
NAMING_SCHEMA = """
## FIS FOLDER NAMING SCHEMA

Format: slug_DOMAIN.SUBJECT
- slug: Top keywords, kebab-case, 20 char max, lowercase
- DOMAIN: 2-letter uppercase code
- SUBJECT: 2-letter uppercase code

## DOMAINS
TP=Theophysics  DT=DayTrading  EV=Evidence  AP=Apps  SY=System  DC=Documents  OB=Obsidian  MD=Media

## THEOPHYSICS SUBJECTS
MQ=MasterEquation  LG=LogosPapers  IS=Isomorphism  JS=JesusSeries  SV=Salvation
RS=Resurrection  GR=Grace  CS=Consciousness  EN=Entropy  AX=Axioms  WV=Worldviews
PH=Personhood  TM=Time  KN=Knowledge  MR=MoralAlignment  QC=QuantumConsciousness
FH=Faith  CO=Coherence  RO=RedemptiveOrder

## DAY TRADING SUBJECTS
ST=Setups  JR=Journal  BT=Backtests  TK=Tickers

## EVIDENCE SUBJECTS
SL=SellviaFraud  LW=Legal  FD=Fraud

## RULES
1. Output JSON only: {"name": "slug_DOMAIN.SUBJECT", "confidence": 0-100, "reason": "one line"}
2. Slug: kebab-case, max 20 chars, no timestamps/version numbers
3. Old/archive content: prefix slug with 'archive-'
4. Confidence: how certain are you? Be honest. <50 if ambiguous.
5. Strip export suffixes, dates, hash strings from slug
"""

# ── AI suggest ─────────────────────────────────────────────────────────────────
def ai_suggest_name(folder_name: str, parent_path: str) -> tuple[str, float, str]:
    """Call Claude Haiku to suggest FIS name. Returns (name, confidence, reason)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    
    # Always run local scorer first
    local = score_folder_locally(folder_name, parent_path)
    local_hint = f"Local scorer says: domain={local['domain']} subject={local['subject']} confidence={local['confidence']}%"

    if not api_key:
        # No API key — use local scoring only, ask Claude just for slug
        slug = re.sub(r'[^a-z0-9]+', '-', folder_name.lower())[:20].strip('-')
        name = f"{slug}_{local['domain']}.{local['subject']}"
        return name, local['confidence'], "local-scorer-only"

    prompt = f"""{NAMING_SCHEMA}

Folder name: {folder_name}
Parent path: {parent_path}
{local_hint}

Output JSON only."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 120,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=12,
        )
        import json as _json
        text = resp.json()["content"][0]["text"].strip()
        # Strip markdown fences if present
        text = re.sub(r"```json|```", "", text).strip()
        parsed = _json.loads(text)
        name = re.sub(r"[^\w\-\.]", "_", parsed.get("name", "")).strip("_")
        # Blend AI confidence with local scorer (average, weighted toward AI)
        ai_conf = float(parsed.get("confidence", 50))
        blended = round((ai_conf * 0.6) + (local["confidence"] * 0.4), 1)
        reason = parsed.get("reason", "")
        return name, blended, reason
    except Exception as e:
        # Fallback to local
        slug = re.sub(r'[^a-z0-9]+', '-', folder_name.lower())[:20].strip('-')
        name = f"{slug}_{local['domain']}.{local['subject']}"
        return name, local['confidence'], f"ai-error: {e}"


def ai_suggest_bulk(ids: list) -> dict:
    """Suggest names for multiple folders. Returns {id: (name, confidence, reason)}."""
    rows = run("""
        SELECT id, folder_name, parent_path FROM folder_triage
        WHERE id = ANY(%s)
    """, (ids,), fetch=True)
    return {r["id"]: ai_suggest_name(r["folder_name"], r["parent_path"]) for r in (rows or [])}

# ── DB ─────────────────────────────────────────────────────────────────────────
def get_conn():
    conn = psycopg2.connect(**DB)
    conn.autocommit = False
    return conn

def run(sql, params=None, fetch=False):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            conn.commit()
            if fetch:
                return [dict(r) for r in cur.fetchall()]
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def ensure_table():
    conn = psycopg2.connect(**DB)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS folder_triage (
                    id            SERIAL PRIMARY KEY,
                    full_path     TEXT UNIQUE NOT NULL,
                    folder_name   TEXT NOT NULL,
                    parent_path   TEXT,
                    depth         INT,
                    root          TEXT,
                    rating        TEXT DEFAULT NULL,
                    new_name      TEXT DEFAULT NULL,
                    notes         TEXT DEFAULT NULL,
                    action_taken  TEXT DEFAULT NULL,
                    new_full_path TEXT DEFAULT NULL,
                    error_msg     TEXT DEFAULT NULL,
                    scanned_at    TIMESTAMPTZ DEFAULT NOW(),
                    rated_at      TIMESTAMPTZ DEFAULT NULL,
                    applied_at    TIMESTAMPTZ DEFAULT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_ft_rating ON folder_triage(rating);
                CREATE INDEX IF NOT EXISTS idx_ft_root   ON folder_triage(root);
                CREATE INDEX IF NOT EXISTS idx_ft_depth  ON folder_triage(depth);
            """)
    finally:
        conn.close()

def upsert_folder(r):
    run("""
        INSERT INTO folder_triage (full_path, folder_name, parent_path, depth, root)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (full_path) DO UPDATE SET
            folder_name = EXCLUDED.folder_name,
            scanned_at  = NOW()
    """, (r["full_path"], r["folder_name"], r["parent_path"], r["depth"], r["root"]))

def save_rating(row_id, rating, new_name, notes, confidence=None):
    run("""
        UPDATE folder_triage
        SET rating=%s, new_name=%s, notes=%s, rated_at=NOW(),
            confidence=COALESCE(%s, confidence)
        WHERE id=%s
    """, (rating or None, new_name or None, notes or None, confidence, row_id))

def bulk_rate(ids, rating):
    if not ids:
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE folder_triage
                SET rating=%s, rated_at=NOW()
                WHERE id = ANY(%s)
            """, (rating, ids))
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def apply_renames(dry_run=True):
    rows = run("""
        SELECT * FROM folder_triage
        WHERE rating='rename' AND new_name IS NOT NULL
          AND (action_taken IS NULL OR action_taken='error')
        ORDER BY depth DESC
    """, fetch=True)
    results = []
    for row in rows:
        folder = Path(row["full_path"])
        new_path = folder.parent / row["new_name"]
        status, error = None, None
        if not folder.exists():
            status, error = "skipped", "not found"
        elif new_path.exists():
            status, error = "skipped", f"target exists"
        elif dry_run:
            status = "dry_run"
        else:
            try:
                folder.rename(new_path)
                status = "applied"
            except Exception as e:
                status, error = "error", str(e)
        run("""
            UPDATE folder_triage SET action_taken=%s, new_full_path=%s,
                error_msg=%s, applied_at=NOW() WHERE id=%s
        """, (status, str(new_path) if status=="applied" else None, error, row["id"]))
        results.append({**row, "status": status, "error": error})
    return results

def get_stats():
    return run("""
        SELECT
            COUNT(*)                                          AS total,
            COUNT(*) FILTER (WHERE rating IS NULL)           AS unrated,
            COUNT(*) FILTER (WHERE rating='keep')            AS keep,
            COUNT(*) FILTER (WHERE rating='rename')          AS rename,
            COUNT(*) FILTER (WHERE rating='delete')          AS delete,
            COUNT(*) FILTER (WHERE rating='merge')           AS merge,
            COUNT(*) FILTER (WHERE rating='review')          AS review,
            COUNT(*) FILTER (WHERE action_taken='applied')   AS applied
        FROM folder_triage
    """, fetch=True)[0]

# ── Walk ────────────────────────────────────────────────────────────────────────
def _walk(path, max_depth, depth=0):
    try:
        children = sorted(path.iterdir())
    except PermissionError:
        return
    for child in children:
        if not child.is_dir() or child.name in SKIP_DIRS or child.name.startswith("."):
            continue
        yield child, depth + 1
        if depth + 1 < max_depth:
            yield from _walk(child, max_depth, depth + 1)

# ── Page setup ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="FIS Folder Triage", page_icon="📁", layout="wide")
ensure_table()

st.markdown("""
<style>
/* Tighten everything */
.block-container { padding-top: 1rem !important; }
div[data-testid="stHorizontalBlock"] { gap: 4px !important; }
div[data-testid="stHorizontalBlock"] > div { padding: 0 2px !important; }
.stSelectbox > div { font-size: 0.78rem !important; }
.stTextInput > div > div > input { font-size: 0.78rem !important; padding: 2px 6px !important; }
.stButton > button { padding: 2px 8px !important; font-size: 0.75rem !important; }
.stCheckbox { margin: 0 !important; }
hr { margin: 2px 0 !important; }
.row-label { font-size: 0.82rem; font-weight: 600; white-space: nowrap;
             overflow: hidden; text-overflow: ellipsis; }
.row-path  { font-size: 0.68rem; color: #888; white-space: nowrap;
             overflow: hidden; text-overflow: ellipsis; }
.badge-keep   { color: #2ecc71; font-weight:700; }
.badge-rename { color: #3498db; font-weight:700; }
.badge-delete { color: #e74c3c; font-weight:700; }
.badge-merge  { color: #f39c12; font-weight:700; }
.badge-review { color: #9b59b6; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📁 FIS Folder Triage")
    roots_raw = st.text_area("Roots", "\n".join(DEFAULT_ROOTS), height=120)
    max_depth = st.slider("Depth", 1, 6, 3)
    roots = [r.strip() for r in roots_raw.splitlines() if r.strip()]

    if st.button("🔍 Scan (streaming)", use_container_width=True, type="primary"):
        st.session_state["scanning"] = True
        st.session_state["scan_roots"] = roots
        st.session_state["scan_depth"] = max_depth
        st.rerun()

    st.divider()
    st.markdown("### 🤖 AI Naming")
    api_key_input = st.text_input("Anthropic API Key", 
                                   value=os.environ.get("ANTHROPIC_API_KEY",""),
                                   type="password", placeholder="sk-ant-...")
    if api_key_input:
        os.environ["ANTHROPIC_API_KEY"] = api_key_input
    st.caption("Uses claude-haiku — cheap, fast. Reads folder name + path → outputs FIS name.")

    st.divider()
    stats = get_stats()
    st.metric("Total", stats["total"])
    c1, c2 = st.columns(2)
    c1.metric("Unrated", stats["unrated"])
    c2.metric("Applied", stats["applied"])
    st.markdown(
        f"<span class='badge-keep'>✅ {stats['keep']}</span> &nbsp;"
        f"<span class='badge-rename'>✏️ {stats['rename']}</span> &nbsp;"
        f"<span class='badge-delete'>🗑️ {stats['delete']}</span> &nbsp;"
        f"<span class='badge-merge'>🔀 {stats['merge']}</span> &nbsp;"
        f"<span class='badge-review'>👀 {stats['review']}</span>",
        unsafe_allow_html=True
    )

    st.divider()
    st.markdown("### Apply Renames")
    dry = st.checkbox("Dry run", value=True)
    if st.button("▶ Apply", use_container_width=True, type="primary"):
        results = apply_renames(dry_run=dry)
        for r in results:
            icon = "✅" if r["status"]=="applied" else "🔍" if r["status"]=="dry_run" else "⚠️"
            st.write(f"{icon} `{r['folder_name']}` → `{r['new_name']}`")
            if r["error"]:
                st.caption(r["error"])

# ── Streaming scan ──────────────────────────────────────────────────────────────
if st.session_state.get("scanning"):
    st.session_state.pop("scanning")
    scan_roots = st.session_state.pop("scan_roots", roots)
    scan_depth = st.session_state.pop("scan_depth", 3)
    prog = st.progress(0, text="Scanning…")
    count = 0
    all_folders = []
    for root_str in scan_roots:
        root = Path(root_str)
        if root.exists():
            for folder, depth in _walk(root, scan_depth):
                all_folders.append((folder, depth, root_str))
    total = len(all_folders)
    for i, (folder, depth, root_str) in enumerate(all_folders):
        upsert_folder({
            "full_path": str(folder),
            "folder_name": folder.name,
            "parent_path": str(folder.parent),
            "depth": depth,
            "root": root_str,
        })
        count += 1
        if i % 20 == 0:
            prog.progress(i / max(total, 1), text=f"Scanning… {count}/{total}  {folder.name}")
    prog.progress(1.0, text=f"Done — {count} folders")
    st.rerun()

# ── Filters ─────────────────────────────────────────────────────────────────────
fc1, fc2, fc3, fc4 = st.columns([2, 3, 1, 1])
filter_rating = fc1.selectbox("Rating", ["all", "unrated"] + RATINGS[1:], label_visibility="collapsed")
filter_root   = fc2.selectbox("Root",   ["all"] + DEFAULT_ROOTS, label_visibility="collapsed")
filter_depth  = fc3.selectbox("Depth",  ["all","1","2","3","4","5"], label_visibility="collapsed")
page_size     = fc4.selectbox("Show",   [50, 100, 200, 500], label_visibility="collapsed")

where, params = [], []
if filter_rating == "unrated":
    where.append("rating IS NULL")
elif filter_rating not in ("all", ""):
    where.append("rating = %s")
    params.append(RATING_VALS.get(filter_rating, filter_rating))
if filter_root != "all":
    where.append("root = %s"); params.append(filter_root)
if filter_depth != "all":
    where.append("depth <= %s"); params.append(int(filter_depth))
where_sql = ("WHERE " + " AND ".join(where)) if where else ""

rows = run(f"""
    SELECT id, depth, root, folder_name, full_path, rating, new_name, notes, action_taken, error_msg, confidence
    FROM folder_triage {where_sql}
    ORDER BY root, depth, folder_name
    LIMIT {page_size}
""", params or None, fetch=True)

# ── Bulk toolbar ────────────────────────────────────────────────────────────────
if "selected" not in st.session_state:
    st.session_state["selected"] = set()

row_ids = [r["id"] for r in rows]

bc1, bc2, bc3, bc4, bc5, bc6, bc7, bc8, bc9 = st.columns([1,1,1,1,1,1,1,1,2])
if bc1.button("☑ All"):
    st.session_state["selected"] = set(row_ids)
    for rid in row_ids:
        st.session_state[f"chk_{rid}"] = True
    st.rerun()
if bc2.button("☐ None"):
    st.session_state["selected"] = set()
    for rid in row_ids:
        st.session_state[f"chk_{rid}"] = False
    st.rerun()
if bc3.button("✅ Keep", disabled=not st.session_state["selected"]):
    bulk_rate(list(st.session_state["selected"]), "keep")
    st.session_state["selected"] = set()
    st.rerun()
if bc4.button("🗑️ Del", disabled=not st.session_state["selected"]):
    bulk_rate(list(st.session_state["selected"]), "delete")
    st.session_state["selected"] = set()
    st.rerun()
if bc5.button("🔀 Merge", disabled=not st.session_state["selected"]):
    bulk_rate(list(st.session_state["selected"]), "merge")
    st.session_state["selected"] = set()
    st.rerun()
if bc6.button("👀 Review", disabled=not st.session_state["selected"]):
    bulk_rate(list(st.session_state["selected"]), "review")
    st.session_state["selected"] = set()
    st.rerun()
if bc7.button("🤖 Suggest", disabled=not st.session_state["selected"],
              help="AI suggests FIS names for all selected rows"):
    sel_ids = list(st.session_state["selected"])
    with st.spinner(f"AI naming {len(sel_ids)} folders..."):
        suggestions = ai_suggest_bulk(sel_ids)
    for fid, (name, conf, reason) in suggestions.items():
        if name:
            st.session_state[f"nn_{fid}"] = name
            run("UPDATE folder_triage SET new_name=%s, rating='rename', confidence=%s, rated_at=NOW() WHERE id=%s",
                (name, conf, fid))
    st.session_state["selected"] = set()
    st.rerun()
if bc8.button("🤖 All Page", help="AI suggests names for every row on this page"):
    with st.spinner(f"AI naming {len(row_ids)} folders..."):
        suggestions = ai_suggest_bulk(row_ids)
    for fid, (name, conf, reason) in suggestions.items():
        if name:
            st.session_state[f"nn_{fid}"] = name
            run("UPDATE folder_triage SET new_name=%s, rating='rename', confidence=%s, rated_at=NOW() WHERE id=%s",
                (name, conf, fid))
    st.rerun()
bc9.caption(f"{len(st.session_state['selected'])} selected · {len(rows)} shown")

sel = st.session_state["selected"]

st.divider()

# ── Row table ───────────────────────────────────────────────────────────────────
# Logic: name field always visible, pre-filled with current name.
# If user edits it → auto-becomes "rename". Rating dropdown for keep/delete/merge/review.
# Save button writes whatever state is set.

RATING_DISPLAY = {"keep":"✅","rename":"✏️","delete":"🗑️","merge":"🔀","review":"👀","":"-"}
QUICK_RATINGS  = ["", "keep", "delete", "merge", "review"]  # rename handled by name edit
QUICK_LABELS   = ["—", "✅ keep", "🗑️ delete", "🔀 merge", "👀 review"]

for row in rows:
    applied = row["action_taken"] == "applied"
    cur_rating = row["rating"] or ""

    c_chk, c_name, c_newname, c_conf, c_rating, c_ai, c_save = \
        st.columns([0.3, 3, 3, 1.2, 1.6, 0.4, 0.4])

    # Checkbox — driven by session state so ☑ All / ☐ None work
    chk_key = f"chk_{row['id']}"
    if chk_key not in st.session_state:
        st.session_state[chk_key] = row["id"] in sel
    checked = c_chk.checkbox("sel", key=chk_key, label_visibility="hidden")
    if checked:
        sel.add(row["id"])
    else:
        sel.discard(row["id"])

    # Current name (read-only label) + path
    indent = "·· " * max(0, (row["depth"] - 1))
    badge = RATING_DISPLAY.get(cur_rating, "")
    c_name.markdown(
        f"<div class='row-label'>{indent}{badge} 📁 {row['folder_name']}</div>"
        f"<div class='row-path'>{row['full_path']}</div>",
        unsafe_allow_html=True
    )

    # New name — always shown, pre-filled. Editing it means rename.
    new_name_val = row["new_name"] or row["folder_name"]
    new_name = c_newname.text_input(
        "new name", value=new_name_val,
        key=f"nn_{row['id']}", disabled=applied,
        label_visibility="collapsed",
        placeholder="edit to rename…"
    )
    # Auto-detect rename vs keep based on whether name changed
    name_changed = new_name.strip() != row["folder_name"]

    # Rating dropdown — excludes rename (handled by name field)
    cur_quick_idx = QUICK_RATINGS.index(cur_rating) if cur_rating in QUICK_RATINGS else 0
    rating_label = c_rating.selectbox("rating", QUICK_LABELS,
                                      index=cur_quick_idx,
                                      key=f"rat_{row['id']}", disabled=applied,
                                      label_visibility="collapsed")
    new_rating = QUICK_RATINGS[QUICK_LABELS.index(rating_label)]

    # If name was edited, override rating to rename
    if name_changed and new_rating not in ("delete", "merge", "review"):
        new_rating = "rename"

    # Confidence bar
    conf = row.get("confidence")
    if conf is not None:
        conf = float(conf)
        if conf >= 65:
            bar_color = "#2ecc71"
            label = f"✅ {conf:.0f}%"
        elif conf >= 35:
            bar_color = "#f39c12"
            label = f"⚠️ {conf:.0f}%"
        else:
            bar_color = "#e74c3c"
            label = f"❓ {conf:.0f}%"
        c_conf.markdown(
            f"<div style='font-size:0.72rem;color:{bar_color};font-weight:700;padding-top:6px'>{label}</div>"
            f"<div style='background:#333;border-radius:3px;height:4px;margin-top:2px'>"
            f"<div style='background:{bar_color};width:{min(conf,100):.0f}%;height:4px;border-radius:3px'></div></div>",
            unsafe_allow_html=True
        )
    else:
        c_conf.markdown("<div style='font-size:0.72rem;color:#555;padding-top:6px'>—</div>",
                        unsafe_allow_html=True)

    # Per-row AI suggest
    if not applied:
        if c_ai.button("🤖", key=f"ai_{row['id']}", help="AI suggest name"):
            with st.spinner("…"):
                name, conf_val, reason = ai_suggest_name(row["folder_name"], row["parent_path"])
            if name:
                st.session_state[f"nn_{row['id']}"] = name
                run("UPDATE folder_triage SET new_name=%s, rating='rename', confidence=%s, rated_at=NOW() WHERE id=%s",
                    (name, conf_val, row["id"]))
                st.rerun()
    else:
        c_ai.empty()

    # Save
    if not applied:
        if c_save.button("💾", key=f"sv_{row['id']}"):
            save_rating(row["id"], new_rating,
                        new_name.strip() if new_rating == "rename" else None,
                        None)
            st.rerun()
    else:
        c_save.markdown("✅")

    if row["error_msg"]:
        st.warning(f"⚠️ {row['error_msg']}", icon="⚠️")
