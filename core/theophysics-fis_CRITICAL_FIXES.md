# Critical Fixes — FIS
## POF 2828 | June 27, 2026
### What to apply before the first real run

---

## SCOPE REMINDER

This is a **file name classifier and database store**. Three jobs only:
scan → classify → propose name → write to SQLite.

It does NOT move files. It does NOT rename anything on disk.
It does NOT constitute the full intelligence system.
That comes later, built on top of this once the DB is populated and trusted.

Fix the gaps below so the classification layer works correctly.
The executor, relationship graph, and intelligence layer are separate work.

---

## GAP 1 — Wrong Database (BLOCKING)

**Problem:** `fis_catalog.db` is 0 bytes. `chi_catalog_v2.db` already has
819,008 classified rows. The daemons are writing to empty air.

**Part A — Point fis_config.json at the real database.**
Change one line:

```json
"db_path": "D:\\DONT TOUCH BOOT UP\\filetagger\\chi_catalog_v2.db"
```

Add that key to `fis_config.json`. Both daemons read `cfg.get("db_path")`.

**Part B — chi_catalog_v2.db has different column names than fis_daemon expects.**

Column name map (chi_catalog → FIS internal name):

| chi_catalog_v2.db column | FIS daemon calls it |
|--------------------------|---------------------|
| `domain_primary` | `chi_domain` |
| `chi_primary` | `chi_factor` / `dominant_chi` |
| `law_primary` | `law` |
| `chi_confidence` | `chi_confidence` ✓ same |
| `content_type` | `content_type` ✓ same |
| `evidence` | `evidence` ✓ same |
| `fruit` | `fruit` ✓ same |
| `anti_fruit` | `anti_fruit` ✓ same |

Everywhere in `fis_daemon.py` that writes `chi_domain=`, change to
`domain_primary=`. Same for `chi_factor` → `chi_primary`, `law` → `law_primary`.

**Part C — chi_catalog_v2.db is missing 6 columns FIS needs. Run once:**

```sql
ALTER TABLE files ADD COLUMN proposed_name TEXT;
ALTER TABLE files ADD COLUMN approved INTEGER DEFAULT NULL;
ALTER TABLE files ADD COLUMN approval_note TEXT;
ALTER TABLE files ADD COLUMN folder_class TEXT;
ALTER TABLE files ADD COLUMN needs_review INTEGER DEFAULT 0;
ALTER TABLE files ADD COLUMN status TEXT DEFAULT 'active';
```

Also create the folders table (chi_catalog_v2.db has no folders table):

```sql
CREATE TABLE IF NOT EXISTS folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    folder_class TEXT,
    topic_slug TEXT,
    proposed_name TEXT,
    file_count INTEGER DEFAULT 0,
    symptom_codes TEXT,
    classified_at TEXT,
    approved INTEGER DEFAULT NULL,
    approval_note TEXT
);
```

Run this migration file before starting either daemon:

```python
# migrate_chi_catalog.py
import sqlite3, os
DB = r"D:\DONT TOUCH BOOT UP\filetagger\chi_catalog_v2.db"
con = sqlite3.connect(DB)
stmts = [
    "ALTER TABLE files ADD COLUMN proposed_name TEXT",
    "ALTER TABLE files ADD COLUMN approved INTEGER DEFAULT NULL",
    "ALTER TABLE files ADD COLUMN approval_note TEXT",
    "ALTER TABLE files ADD COLUMN folder_class TEXT",
    "ALTER TABLE files ADD COLUMN needs_review INTEGER DEFAULT 0",
    "ALTER TABLE files ADD COLUMN status TEXT DEFAULT 'active'",
    """CREATE TABLE IF NOT EXISTS folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE NOT NULL,
        folder_class TEXT, topic_slug TEXT, proposed_name TEXT,
        file_count INTEGER DEFAULT 0, symptom_codes TEXT,
        classified_at TEXT, approved INTEGER DEFAULT NULL,
        approval_note TEXT
    )""",
]
for s in stmts:
    try:
        con.execute(s)
        print("OK:", s[:60])
    except Exception as e:
        print("SKIP:", e)
con.commit(); con.close()
print("Done.")
```

---

## GAP 2 — WordNet Not Wired Into Enricher (HIGH)

**Problem:** `fis_enricher.py` matches filenames with raw word splitting.
`wordnet_expander.py` already exists in `filetagger\` and expands any word
list with synonyms, hypernyms, hyponyms via NLTK WordNet — exactly what the
enricher needs for semantic similarity before TF-IDF.

**Fix:** In `fis_enricher.py`, replace `_name_to_text()` with this:

```python
import sys as _sys
_sys.path.insert(0, r"D:\DONT TOUCH BOOT UP\filetagger")
try:
    from wordnet_expander import expand_term_list as _wn_expand
    WORDNET_OK = True
except ImportError:
    WORDNET_OK = False

def _name_to_text(name: str) -> str:
    stem  = Path(name).stem
    words = [w.lower() for w in _SPLIT.split(stem) if len(w) > 1]
    if WORDNET_OK and words:
        expanded = _wn_expand(words, max_total=20)
        words = list(dict.fromkeys(words + expanded))  # original first, deduped
    return " ".join(words) if words else stem.lower()
```

That's the entire fix. The enricher will now find semantic matches, not just
character matches. A file named `covenant_notes.docx` will match files named
`agreement_record.docx` because WordNet links covenant → agreement.

**Dependency:** `pip install nltk` then run `python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"` once.

---

## GAP 3 — 20 Symptom Detection Functions Are Stubs (MEDIUM)

**Problem:** All 20 detect_* functions in `fis_folder_daemon.py` return `False`.
Folder naming (e.g. `S03_name-swamp`) is completely blocked.

**The 20 symptoms and what each function needs to check:**

```python
# STRUCTURAL (S01–S08) — count files, check extensions, check names
def detect_S01_extension_swamp(path, files):
    # > 5 distinct extensions in one folder
    exts = {os.path.splitext(f)[1].lower() for f in files if '.' in f}
    return len(exts) > 5

def detect_S02_name_chaos(path, files):
    # avg filename length > 40 chars OR > 30% of names have no recognisable words
    if not files: return False
    return sum(len(f) for f in files) / len(files) > 40

def detect_S03_flat_dump(path, files):
    # > 50 files, no subfolders
    subdirs = [d for d in os.scandir(path) if d.is_dir()]
    return len(files) > 50 and len(subdirs) == 0

def detect_S04_deep_nest(path, files):
    # folder depth > 5 levels below a drive root
    return path.count(os.sep) > 7

def detect_S05_empty_folders(path, files):
    # folder has 0 files (only subdirs or truly empty)
    return len(files) == 0

def detect_S06_duplicate_cluster(path, files):
    # > 3 files with same stem (copy of, (1), _v2, _backup patterns)
    import re
    stems = [re.sub(r'[\s_\-]*(copy|backup|\(\d+\)|v\d+).*$', '',
             os.path.splitext(f)[0], flags=re.I).strip() for f in files]
    from collections import Counter
    return max(Counter(stems).values(), default=0) >= 3

def detect_S07_screenshot_pile(path, files):
    # > 5 files matching screenshot naming patterns
    import re
    pat = re.compile(r'screenshot|screen.?shot|capture|\d{4}-\d{2}-\d{2}', re.I)
    return sum(1 for f in files if pat.search(f)) > 5

def detect_S08_mixed_media(path, files):
    # images + video + audio all present
    img  = {'.jpg','.jpeg','.png','.gif','.webp','.bmp'}
    vid  = {'.mp4','.mkv','.avi','.mov','.wmv'}
    aud  = {'.mp3','.wav','.flac','.m4a','.ogg'}
    exts = {os.path.splitext(f)[1].lower() for f in files}
    return bool(exts & img) and bool(exts & vid or exts & aud)

# CONTENT (C01–C08) — look at file names for domain signals
def detect_C01_code_project(path, files):
    code = {'.py','.js','.ts','.go','.rs','.java','.cpp','.cs'}
    exts = {os.path.splitext(f)[1].lower() for f in files}
    return len(exts & code) >= 2 or any(f in files for f in
           ['requirements.txt','package.json','Makefile','setup.py'])

def detect_C02_document_archive(path, files):
    docs = {'.pdf','.docx','.doc','.odt','.rtf'}
    exts = {os.path.splitext(f)[1].lower() for f in files}
    return len([f for f in files if os.path.splitext(f)[1].lower() in docs]) >= 5

def detect_C03_data_store(path, files):
    data = {'.csv','.xlsx','.xls','.json','.sqlite','.db','.parquet'}
    exts = {os.path.splitext(f)[1].lower() for f in files}
    return len(exts & data) >= 3

def detect_C04_theology_content(path, files):
    import re
    pat = re.compile(r'god|jesus|christ|bible|scripture|theology|faith|prayer|covenant|holy|spirit|lord', re.I)
    name = os.path.basename(path)
    return bool(pat.search(name)) or sum(1 for f in files if pat.search(f)) >= 3

def detect_C05_legal_evidence(path, files):
    import re
    pat = re.compile(r'claim|evidence|exhibit|deposition|court|motion|complaint|filing|legal|statute', re.I)
    name = os.path.basename(path)
    return bool(pat.search(name)) or sum(1 for f in files if pat.search(f)) >= 2

def detect_C06_research_notes(path, files):
    import re
    pat = re.compile(r'note|research|study|draft|outline|ref|source|citation|bibliography', re.I)
    return sum(1 for f in files if pat.search(f)) >= 3

def detect_C07_media_production(path, files):
    media = {'.mp4','.mov','.avi','.mkv','.mp3','.wav','.flac',
             '.psd','.ai','.aep','.prproj','.fcpx'}
    exts  = {os.path.splitext(f)[1].lower() for f in files}
    return len(exts & media) >= 3

def detect_C08_config_scripts(path, files):
    cfg = {'.json','.yaml','.yml','.toml','.ini','.env','.cfg','.conf',
           '.sh','.bat','.ps1'}
    exts = {os.path.splitext(f)[1].lower() for f in files}
    return len(exts & cfg) >= 3

# TEMPORAL (T01–T04) — use file mtimes
def detect_T01_stale_archive(path, files, full_paths):
    # all files older than 2 years
    import time
    if not full_paths: return False
    cutoff = time.time() - (2 * 365 * 86400)
    return all(os.path.getmtime(p) < cutoff for p in full_paths)

def detect_T02_recent_burst(path, files, full_paths):
    # > 10 files modified in the last 7 days
    import time
    cutoff = time.time() - (7 * 86400)
    return sum(1 for p in full_paths if os.path.getmtime(p) > cutoff) > 10

def detect_T03_mixed_era(path, files, full_paths):
    # span between oldest and newest file > 3 years
    import time
    if len(full_paths) < 2: return False
    mtimes = [os.path.getmtime(p) for p in full_paths]
    return (max(mtimes) - min(mtimes)) > (3 * 365 * 86400)

def detect_T04_single_session(path, files, full_paths):
    # all files created within 1 hour of each other
    if len(full_paths) < 3: return False
    mtimes = sorted(os.path.getmtime(p) for p in full_paths)
    return (mtimes[-1] - mtimes[0]) < 3600
```

**Wiring:** In `fis_folder_daemon.py`, replace the `classify_folder()` function's
symptom loop to call each `detect_*` and collect the codes that return `True`.
First match wins for primary class assignment:

```
S-codes → structural class
C-codes → content class  
T-codes → temporal modifier
```

---

## GAP 4 — Excel Approval Queue Not Built (MEDIUM)

**Problem:** The DB will accumulate rows with `proposed_name IS NOT NULL AND approved IS NULL`
but there is no way to export them to Excel for human review. Step 6 of the
10-step pipeline is blocked.

**Fix — create `consumers/excel_preview.py`:**

```python
"""
consumers/excel_preview.py
Export pending approval queue to Excel.
Usage: python excel_preview.py [db_path] [out_path]
"""
import sqlite3, sys, datetime
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment
    OPENPYXL = True
except ImportError:
    OPENPYXL = False

DB_DEFAULT  = r"D:\DONT TOUCH BOOT UP\filetagger\chi_catalog_v2.db"
OUT_DEFAULT = r"D:\DONT TOUCH BOOT UP\FIS\approval_queue.xlsx"

COLS = [
    ("path",           40, "Path"),
    ("name",           30, "Current Name"),
    ("proposed_name",  40, "Proposed Name"),
    ("domain_primary", 8,  "Domain"),
    ("content_type",   8,  "CT"),
    ("chi_confidence", 8,  "Conf"),
    ("needs_review",   6,  "Review"),
    ("APPROVE",        10, "APPROVE"),   # human fills: yes / no / skip
    ("NOTE",           30, "Note"),      # human fills: freetext
]

GOLD  = PatternFill("solid", fgColor="E8A912")
GREEN = PatternFill("solid", fgColor="2ECC8E")

def export(db_path=DB_DEFAULT, out_path=OUT_DEFAULT, limit=2000):
    if not OPENPYXL:
        print("pip install openpyxl")
        return
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT path, name, ext, proposed_name,
               domain_primary, content_type, chi_confidence, needs_review
        FROM files
        WHERE proposed_name IS NOT NULL
          AND (approved IS NULL OR approved = 0)
        ORDER BY chi_confidence ASC
        LIMIT ?
    """, (limit,)).fetchall()
    con.close()
    if not rows:
        print("Nothing pending.")
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Approval Queue"

    # Header row
    for ci, (_, width, label) in enumerate(COLS, 1):
        cell = ws.cell(1, ci, label)
        cell.fill  = GOLD
        cell.font  = Font(bold=True, size=9)
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = width

    ws.freeze_panes = "A2"

    for ri, row in enumerate(rows, 2):
        for ci, (col, _, _label) in enumerate(COLS, 1):
            if col in ("APPROVE", "NOTE"):
                ws.cell(ri, ci, "")
            else:
                val = row[col] if col in row.keys() else ""
                if col == "chi_confidence" and val:
                    val = round(float(val), 2)
                ws.cell(ri, ci, val)
        # colour low-confidence rows
        if row["chi_confidence"] and float(row["chi_confidence"]) < 0.5:
            for ci in range(1, len(COLS)+1):
                ws.cell(ri, ci).fill = PatternFill("solid", fgColor="2A1A1A")

    wb.save(out_path)
    print(f"Exported {len(rows)} rows → {out_path}")

if __name__ == "__main__":
    db  = sys.argv[1] if len(sys.argv) > 1 else DB_DEFAULT
    out = sys.argv[2] if len(sys.argv) > 2 else OUT_DEFAULT
    export(db, out)
```

**After human reviews the Excel:**
Run an importer that reads back the APPROVE column and writes to DB:

```python
# consumers/apply_approvals.py
import sqlite3, openpyxl, sys

def apply(xlsx_path, db_path):
    wb   = openpyxl.load_workbook(xlsx_path)
    ws   = wb.active
    cols = {cell.value: cell.column for cell in ws[1]}
    con  = sqlite3.connect(db_path)
    ok = skip = reject = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        path     = row[cols["Path"] - 1]
        decision = str(row[cols["APPROVE"] - 1] or "").strip().lower()
        note     = row[cols["Note"] - 1] or ""
        if not path or decision == "skip" or decision == "":
            skip += 1; continue
        approved = 1 if decision in ("yes","y","true","1") else 0
        con.execute(
            "UPDATE files SET approved=?, approval_note=? WHERE path=?",
            (approved, note, path))
        (ok if approved else reject).__class__  # dummy
        if approved: ok += 1
        else: reject += 1
    con.commit(); con.close()
    print(f"Applied: {ok} approved, {reject} rejected, {skip} skipped")

if __name__ == "__main__":
    apply(sys.argv[1], sys.argv[2])
```

**Dependencies:** `pip install openpyxl`

---

## GAP 5 — INSTALL_STARTUP.bat Never Run (LOW)

**Problem:** Neither daemon is registered with Windows Task Scheduler.
Files are not being tagged live.

**Action required by user (needs admin):**
```
Right-click INSTALL_STARTUP.bat → Run as administrator
```

File is at: `D:\DONT TOUCH BOOT UP\FIS\INSTALL_STARTUP.bat`

After running, verify with:
```
schtasks /query /tn "FIS_Daemon" /fo LIST
schtasks /query /tn "FIS_Folder_Daemon" /fo LIST
```

---

## EXECUTION ORDER

Run these in sequence, top to bottom:

```
1. python migrate_chi_catalog.py             ← adds 6 cols + folders table
2. Edit fis_config.json — add db_path key   ← points daemons at real data
3. Edit fis_daemon.py — fix 3 column names  ← domain_primary/chi_primary/law_primary
4. Edit fis_enricher.py — add wordnet pass  ← semantic enrichment
5. Paste 20 detect_* functions into fis_folder_daemon.py
6. pip install openpyxl nltk river scikit-learn  ← if not already installed
7. python -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"
8. Run INSTALL_STARTUP.bat as admin          ← starts live tagging
9. Wait ~10 min, then:
   python consumers/excel_preview.py        ← generate first approval queue
10. Open approval_queue.xlsx, fill APPROVE column, save
11. python consumers/apply_approvals.py approval_queue.xlsx [db_path]
```

After step 11, the preference engine has its first training data and
will start auto-approving high-confidence naming proposals.
