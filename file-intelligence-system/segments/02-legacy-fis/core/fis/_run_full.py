#!/usr/bin/env python
"""FIS Full Classification Run — set it free.

Complete pipeline per file:
  1. Extract text
  2. Score 10 chi-variables (semantic_scorer)
  3. Encode coordinate hash (hash_codec)
  4. Classify CONTEXT→DOMAIN→FUNCTION→STATE (meta_mapper)
  5. Infer relational context from path
  6. Store all four layers in Postgres
  7. Write scoring session + per-file audit record
  8. Print live output

Usage:
    python fis\_run_full.py --path "D:\GitHub\file-intelligence-system" --dry-run
    python fis\_run_full.py --path "D:\GitHub\file-intelligence-system" --limit 50
"""

import argparse, sys, time, traceback, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fis.nlp.extractor import extract_text
from fis.nlp.semantic_scorer import SemanticScorer
from fis.nlp.meta_mapper import MetaMapper
from fis.nlp.hash_codec import human_score_string, encode_hash
from fis.db.semantic_store import (
    upsert_file_identity, upsert_meta_classification,
    infer_relational_context, store_relational_context
)
from fis.db.scoring_store import (
    create_session, write_file_score, write_dimension_confidence, finalize_session
)

SKIP_EXT = {'.exe','.dll','.sys','.iso','.bin','.lnk',
            '.db','.sqlite','.idx','.pak','.lock'}
SKIP_DIR = {'.git','node_modules','__pycache__','.obsidian',
            'AppData','$Recycle.Bin'}
MAX_MB   = 50


def get_conn():
    import configparser, psycopg2
    cfg = configparser.ConfigParser()
    cfg.read(Path(__file__).parent.parent / 'config' / 'settings.ini')
    d = cfg['database']
    return psycopg2.connect(
        host=d.get('host','192.168.1.97'), port=d.getint('port',5432),
        dbname=d.get('dbname','fis_db'), user=d.get('user','fis_user'),
        password=d.get('password',''),
    )


def collect(root: Path, limit=None):
    files = []
    for p in root.rglob('*'):
        if not p.is_file(): continue
        if any(s in p.parts for s in SKIP_DIR): continue
        if p.suffix.lower() in SKIP_EXT: continue
        try:
            if p.stat().st_size > MAX_MB * 1024 * 1024: continue
        except OSError:
            continue
        files.append(p)
        if limit and len(files) >= limit: break
    return files


def fmt(i, total, path, address, meta, rc, t):
    dom  = ''.join(address.dominant) or 'E'
    mp   = f"{meta.context}/{meta.domain}/{meta.function}/{meta.state}" if meta else "?"
    rc_s = ' '.join(f"{r['key']}:{r['value']}" for r in rc[:2])
    return (f"[{i:>4}/{total}] {path.name[:40]:<40} "
            f"{address.coord_hash_full:<22} {mp:<38} {rc_s:<28} {t:.1f}s")


def run(root: Path, limit=None, dry_run=False, conn=None) -> dict:
    scorer = SemanticScorer()
    mapper = MetaMapper(conn)
    files  = collect(root, limit)
    total  = len(files)

    # Create scoring session
    session_id = None
    if not dry_run and conn:
        session_id = create_session(
            conn, str(root),
            run_mode='tier1',
            session_name=f"scan_{root.name}_{time.strftime('%Y%m%d_%H%M%S')}"
        )
        print(f"[SESSION {session_id}] {root} | {total} files")

    W = 140
    print(f"\n{'='*W}")
    print(f"FIS FULL RUN | {root} | {total} files | dry_run={dry_run}")
    print(f"{'='*W}")
    print(f"{'#':>9} {'FILENAME':<40} {'SEMANTIC ADDRESS':<22} "
          f"{'META PATH':<38} {'RELATIONAL':<28} TIME")
    print(f"{'-'*W}")

    stats = {'total':total,'success':0,'skipped':0,'errors':0,
             'by_context':{},'by_domain':{},'by_function':{},'by_dominant':{},
             'entropy_count':0}

    for i, path in enumerate(files, 1):
        t0 = time.time()
        try:
            text    = extract_text(str(path)) or ''
            address = scorer.score_file(str(path), text)
            # Enrich address with full codec hash
            from fis.nlp.hash_codec import encode_hash
            _hashes = encode_hash(address.vector, address.magnitude, address.state, address.dominant)
            address.coord_hash_full = _hashes['coord_hash_full']
            address.coord_hash_raw  = _hashes['coord_hash_raw']
            meta    = mapper.classify(address, path.suffix.lower())
            rc      = infer_relational_context(path)
            from fis.nlp.dqm import dqm_from_vector, dqm_label
            dq, dconf, dflags = dqm_from_vector(address.vector)
            dqm_str = dqm_label(dq, dconf, dflags)
            elapsed = time.time() - t0
            print(fmt(i, total, path, address, meta, rc, elapsed) + f'  {dqm_str}')

            if not dry_run and conn:
                from fis.db.models import compute_sha256, file_exists_by_hash
                sha256   = compute_sha256(str(path))
                existing = file_exists_by_hash(sha256)
                file_id  = existing['file_id'] if existing else None

                iid      = upsert_file_identity(conn, sha256, path, text, address, meta, file_id)
                upsert_meta_classification(conn, sha256, iid, meta, address)
                store_relational_context(conn, sha256, rc)

                if session_id:
                    sid = write_file_score(conn, session_id, sha256, path, address, meta)
                    write_dimension_confidence(conn, sid, sha256, address.vector, address)

            # Stats
            stats['success'] += 1
            dom = ''.join(address.dominant) or 'E'
            if dom == 'E': stats['entropy_count'] += 1
            stats['by_dominant'][dom] = stats['by_dominant'].get(dom,0)+1
            if meta:
                stats['by_context'][meta.context]   = stats['by_context'].get(meta.context,0)+1
                stats['by_domain'][meta.domain]     = stats['by_domain'].get(meta.domain,0)+1
                stats['by_function'][meta.function] = stats['by_function'].get(meta.function,0)+1

        except KeyboardInterrupt:
            print("\n[INTERRUPTED]"); break
        except Exception as ex:
            stats['errors'] += 1
            print(f"[{i:>4}/{total}] ERROR {path.name[:50]}: {ex}")
            if '--verbose' in sys.argv: traceback.print_exc()

    if not dry_run and conn and session_id:
        finalize_session(conn, session_id, stats)
        print(f"\n[SESSION {session_id}] Finalized and stored in Postgres.")

    return stats


def summary(stats, total_time):
    W = 100
    print(f"\n{'='*W}")
    print(f"COMPLETE | {stats['total']} files | {total_time:.1f}s "
          f"| {stats['total']/max(total_time,1):.1f} files/s")
    print(f"  Success:{stats['success']}  Errors:{stats['errors']}  "
          f"Entropy flags:{stats['entropy_count']}")
    for label, d in [('CONTEXT',stats['by_context']),
                     ('DOMAIN',stats['by_domain']),
                     ('FUNCTION',stats['by_function'])]:
        if not d: continue
        print(f"\n  {label}:")
        for k, v in sorted(d.items(), key=lambda x:-x[1]):
            print(f"    {k:<16} {v:>4}  {'█'*min(v,50)}")
    print(f"\n  TOP SEMANTIC CLUSTERS:")
    for k, v in sorted(stats['by_dominant'].items(), key=lambda x:-x[1])[:12]:
        print(f"    {k:<10} {v:>4}  {'█'*min(v,50)}")
    print(f"\n{'='*W}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--path', default=r'D:\GitHub\file-intelligence-system')
    p.add_argument('--limit', type=int, default=None)
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--verbose', action='store_true')
    args = p.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"ERROR: {root}"); sys.exit(1)

    conn = None
    if not args.dry_run:
        try:
            conn = get_conn()
            print("[DB] Connected")
        except Exception as ex:
            print(f"[DB] {ex} — dry-run mode")
            args.dry_run = True

    t0    = time.time()
    stats = run(root, args.limit, args.dry_run, conn)
    summary(stats, time.time()-t0)
    if conn: conn.close()


if __name__ == '__main__':
    main()
