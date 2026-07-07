"""FIS Upgrade Script — Add missing codes, path heuristics, batch train.
Run: cd /d D:\GitHub\file-intelligence-system && python fis/_upgrade_v2.py

What this does:
1. Adds SY (System) domain with subject codes (CF=Config, SC=Script, GT=Git, LG=Log)
2. Adds missing subject codes that corrections reference (CF, OB, etc.)  
3. Adds MD (Media/Content) domain for HTML exports, articles
4. Registers path-based heuristic rules in a new table
5. Batch-trains the ML classifier from all confirmed+auto files
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras

DB = dict(host='192.168.1.97', port=5432, dbname='fis_db',
          user='postgres', password='Moss9pep28$')


def add_missing_codes(cur):
    """Add domain and subject codes that are missing."""
    print("\n=== ADDING MISSING CODES ===")

    # Ensure SY domain exists
    cur.execute("""
        INSERT INTO domain_codes (code, label, description, is_active)
        VALUES ('SY', 'System', 'System files, configs, scripts, git artifacts', TRUE)
        ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, is_active = TRUE
    """)
    print("  Domain SY (System) ensured")

    # Ensure MD domain exists (Media/Content exports)
    cur.execute("""
        INSERT INTO domain_codes (code, label, description, is_active)
        VALUES ('MD', 'Media/Content', 'HTML exports, articles, presentations, media files', TRUE)
        ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, is_active = TRUE
    """)
    print("  Domain MD (Media/Content) ensured")

    # Ensure all other domains exist
    for code, label in [('TP', 'Theophysics'), ('DT', 'Day Trading'),
                        ('EV', 'Evidence'), ('CB', 'Clipboard')]:
        cur.execute("""
            INSERT INTO domain_codes (code, label, is_active)
            VALUES (%s, %s, TRUE)
            ON CONFLICT (code) DO UPDATE SET is_active = TRUE
        """, (code, label))

    # Add SY subject codes
    sy_subjects = [
        ('CF', 'Config/Setup', 'SY', '{config, configuration, setup, settings, ini, yaml, yml, toml, env}',
         '{README, INSTALL, START_HERE, QUICKSTART, SETUP, HOW_TO, MENU, FEATURES, TOOLS, ENHANCED}'),
        ('SC', 'Script/Code', 'SY', '{script, code, program, module, function, class, def, import}',
         '{.py, .js, .ts, .sh, .bat, .ps1, .ahk, pipeline, watcher, handler}'),
        ('GT', 'Git Artifact', 'SY', '{git, commit, branch, merge, HEAD, exclude, gitignore}',
         '{HEAD, COMMIT_EDITMSG, exclude, packed-refs, FETCH_HEAD, config, description}'),
        ('LF', 'Log File', 'SY', '{log, debug, trace, error, warning, info}',
         '{service.log, error.log, debug.log, output.log}'),
    ]
    for code, label, domain, aliases, triggers in sy_subjects:
        cur.execute("""
            INSERT INTO subject_codes (code, label, domain, parent_domain, aliases,
                                       trigger_words, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (code) DO UPDATE SET
                label = EXCLUDED.label, domain = EXCLUDED.domain,
                trigger_words = EXCLUDED.trigger_words, is_active = TRUE
        """, (code, label, domain, domain, aliases, triggers))
        print(f"  Subject {code} ({label}) added to {domain}")

    # Add MD subject codes for article/export content
    md_subjects = [
        ('AR', 'Article/Essay', 'MD', '{article, essay, paper, post, blog}',
         '{article, essay, paper, blog, post, substack, chapter, introduction, conclusion}'),
        ('EX', 'Export/Archive', 'MD', '{export, archive, backup, dump}',
         '{export, archive, backup, dump, EXPORT}'),
        ('PR', 'Presentation', 'MD', '{presentation, slides, deck, pptx}',
         '{presentation, slides, deck, slide, keynote}'),
    ]
    for code, label, domain, aliases, triggers in md_subjects:
        cur.execute("""
            INSERT INTO subject_codes (code, label, domain, parent_domain, aliases,
                                       trigger_words, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (code) DO UPDATE SET
                label = EXCLUDED.label, domain = EXCLUDED.domain,
                trigger_words = EXCLUDED.trigger_words, is_active = TRUE
        """, (code, label, domain, domain, aliases, triggers))
        print(f"  Subject {code} ({label}) added to {domain}")

    # Add OB (Obsidian) subject under TP since it's vault-related
    cur.execute("""
        INSERT INTO subject_codes (code, label, domain, parent_domain, aliases,
                                   trigger_words, is_active)
        VALUES ('OB', 'Obsidian/Vault', 'TP', 'TP',
                '{obsidian, vault, dataview, frontmatter, wikilink}',
                '{obsidian, vault, dataview, frontmatter, wikilink, .md, note, zettelkasten}',
                TRUE)
        ON CONFLICT (code) DO UPDATE SET
            label = EXCLUDED.label, trigger_words = EXCLUDED.trigger_words, is_active = TRUE
    """)
    print("  Subject OB (Obsidian/Vault) added to TP")


def create_path_rules_table(cur):
    """Create a table for path-based classification hints."""
    print("\n=== CREATING PATH RULES ===")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS path_rules (
            rule_id    SERIAL PRIMARY KEY,
            pattern    TEXT NOT NULL,
            domain     TEXT NOT NULL,
            subjects   TEXT[],
            confidence_boost INT DEFAULT 20,
            priority   INT DEFAULT 0,
            description TEXT,
            is_active  BOOLEAN DEFAULT TRUE
        )
    """)

    # Insert path rules
    rules = [
        # GitHub = almost always system/code
        ('D:\\GitHub\\', 'SY', ['SC'], 30, 10, 'GitHub repos are system/code files'),
        # Git internals
        ('.git\\', 'SY', ['GT'], 50, 20, 'Git internal files'),
        # Theophysics vault
        ('O:\\_Theophysics', 'TP', None, 20, 5, 'Theophysics vault files'),
        # Moral Decline exports — these are TP articles, not DT
        ('Moral decline of America', 'TP', ['MR'], 25, 15, 'Moral Decline research articles'),
        ('EXPORT\\', 'MD', ['EX'], 15, 3, 'Export folder content'),
        # Node modules, build dirs — definitely system
        ('node_modules', 'SY', ['SC'], 50, 20, 'Node modules'),
        ('__pycache__', 'SY', ['SC'], 50, 20, 'Python cache'),
        # ShareX = system config
        ('ShareX', 'SY', ['CF'], 30, 10, 'ShareX configuration'),
        # Desktop STAY — mixed content, mostly TP and MD
        ('Desktop STAY\\EXPORT\\', 'MD', ['EX', 'AR'], 20, 8, 'Desktop STAY exports'),
    ]

    cur.execute("DELETE FROM path_rules")  # Fresh start
    for pattern, domain, subjects, boost, priority, desc in rules:
        cur.execute("""
            INSERT INTO path_rules (pattern, domain, subjects, confidence_boost, priority, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (pattern, domain, subjects, boost, priority, desc))
        print(f"  Rule: '{pattern}' -> {domain}/{subjects} (+{boost})")


def fix_dt_misclassifications(cur):
    """Fix the known DT misclassifications for Moral Decline articles."""
    print("\n=== FIXING DT MISCLASSIFICATIONS ===")

    # Count how many Moral Decline articles are wrongly DT
    cur.execute("""
        SELECT COUNT(*) as cnt FROM files
        WHERE file_path LIKE '%%Moral decline%%'
          AND domain = 'DT'
    """)
    count = cur.fetchone()['cnt']
    print(f"  Found {count} Moral Decline files misclassified as DT")

    if count > 0:
        cur.execute("""
            UPDATE files SET domain = 'TP', status = 'corrected'
            WHERE file_path LIKE '%%Moral decline%%'
              AND domain = 'DT'
        """)
        print(f"  Fixed {count} files: DT -> TP")

    # Fix GitHub files misclassified as TP/DT
    cur.execute("""
        SELECT COUNT(*) as cnt FROM files
        WHERE file_path LIKE '%%\\GitHub\\%%'
          AND domain NOT IN ('SY', '--')
          AND original_name IN ('HEAD', 'exclude', 'index', 'config', 'description',
                                'packed-refs', 'FETCH_HEAD', 'COMMIT_EDITMSG')
    """)
    count = cur.fetchone()['cnt']
    if count > 0:
        cur.execute("""
            UPDATE files SET domain = 'SY', subject_codes = ARRAY['GT'], status = 'corrected'
            WHERE file_path LIKE '%%\\GitHub\\%%'
              AND domain NOT IN ('SY', '--')
              AND original_name IN ('HEAD', 'exclude', 'index', 'config', 'description',
                                    'packed-refs', 'FETCH_HEAD', 'COMMIT_EDITMSG')
        """)
        print(f"  Fixed {count} git artifact files -> SY/GT")

    # Fix ShareX config classified as EV/FD
    cur.execute("""
        UPDATE files SET domain = 'SY', subject_codes = ARRAY['CF'], status = 'corrected'
        WHERE file_path LIKE '%%ShareX%%'
          AND domain NOT IN ('SY')
    """)
    print(f"  Fixed ShareX files -> SY/CF")


def batch_train_classifier(cur):
    """Train the ML classifier from all confirmed+auto+corrected files."""
    print("\n=== BATCH TRAINING ML CLASSIFIER ===")

    # Get all labeled files (auto, confirmed, corrected)
    cur.execute("""
        SELECT f.file_id, f.file_path, f.domain, f.subject_codes,
               array_agg(t.tag) as tags
        FROM files f
        LEFT JOIN file_tags t ON f.file_id = t.file_id
        WHERE f.status IN ('auto', 'confirmed', 'corrected')
          AND f.domain IS NOT NULL
          AND f.domain != '--'
        GROUP BY f.file_id, f.file_path, f.domain, f.subject_codes
    """)
    rows = cur.fetchall()
    print(f"  Found {len(rows)} labeled files for training")

    if len(rows) < 10:
        print("  Not enough labeled data to train. Skipping.")
        return

    # Extract text for each file (use tags as proxy if file not accessible)
    from fis.nlp.extractor import extract_text
    from fis.nlp.classifier import FISClassifier
    from pathlib import Path

    texts = []
    keywords_list = []
    domains = []
    subjects = []
    skipped = 0

    for row in rows:
        fp = row['file_path']
        # Try to read the file, fall back to tags
        if Path(fp).exists():
            text = extract_text(fp)
            if not text.strip():
                text = " ".join(str(t) for t in (row['tags'] or []) if t)
        else:
            text = " ".join(str(t) for t in (row['tags'] or []) if t)

        if not text.strip():
            skipped += 1
            continue

        texts.append(text)
        tags = row['tags'] or []
        keywords_list.append([{"keyword": str(t), "source": "db"} for t in tags if t])
        domains.append(row['domain'])
        # Use first subject code
        subs = row['subject_codes'] or ['GN']
        subjects.append(subs[0] if subs else 'GN')

    print(f"  Prepared {len(texts)} training samples ({skipped} skipped — no text)")

    if len(texts) < 10:
        print("  Not enough readable files. Skipping training.")
        return

    # Train the classifier
    classifier = FISClassifier()
    classifier.learn(texts, keywords_list, domains, subjects)
    print(f"  ML classifier trained and saved to models/saved/classifier.pkl")
    print(f"  Domain classes: {list(classifier.domain_encoder.classes_)}")
    print(f"  Subject classes: {list(classifier.subject_encoder.classes_)}")


def main():
    c = psycopg2.connect(**DB)
    c.autocommit = False
    cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        add_missing_codes(cur)
        create_path_rules_table(cur)
        fix_dt_misclassifications(cur)
        c.commit()
        print("\n  Database changes committed.")

        # Training uses its own connection via FIS internals
        batch_train_classifier(cur)

    except Exception as e:
        c.rollback()
        print(f"\n  ERROR: {e}")
        raise
    finally:
        c.close()

    print("\n=== UPGRADE COMPLETE ===")


if __name__ == "__main__":
    main()
