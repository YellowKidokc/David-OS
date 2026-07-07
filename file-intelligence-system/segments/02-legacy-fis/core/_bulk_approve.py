"""
Bulk approve and rename files that meet quality threshold.
Criteria: conf>=70, no 'untitled/tbd' slug, domain known, file exists on disk.
Logs every action. Skips anything that looks wrong.
"""
import psycopg2, psycopg2.extras, re, sys, os
from pathlib import Path

sys.path.insert(0, r'D:\GitHub\file-intelligence-system')
os.environ['PYTHONIOENCODING'] = 'utf-8'

conn = psycopg2.connect(host='192.168.1.97', port=5432, dbname='fis_db', user='postgres', password='Moss9pep28$')
conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Pull safe candidates
cur.execute("""
    SELECT file_id, sequence_id, original_name, proposed_name, 
           file_path, domain, subject_codes, confidence
    FROM files 
    WHERE status = 'pending'
      AND confidence >= 70
      AND proposed_name IS NOT NULL
      AND proposed_name NOT ILIKE '%untitled%'
      AND proposed_name NOT ILIKE '%tbd%'
      AND proposed_name NOT ILIKE '%--%'
      AND domain IN ('TP','DT','SY','AP','EV','OB','MD','DC')
    ORDER BY confidence DESC
""")
candidates = cur.fetchall()
print(f"Candidates: {len(candidates)}\n", flush=True)

approved = skipped = errors = already = 0

for row in candidates:
    file_id = row['file_id']
    orig_path = Path(row['file_path'])
    proposed = row['proposed_name']
    
    # Safety checks
    if not orig_path.exists():
        try:
            print(f"  SKIP (not found): {row['original_name']}", flush=True)
        except:
            print(f"  SKIP (not found): [unicode name]", flush=True)
        cur.execute("UPDATE files SET status='skipped' WHERE file_id=%s", (file_id,))
        skipped += 1
        continue
    
    # Build new path
    new_path = orig_path.parent / proposed
    
    # Don't rename if already has FIS format
    if re.match(r'^[a-z0-9\-]+_[A-Z]{2}\.[A-Z]{2}', orig_path.name):
        cur.execute("UPDATE files SET status='confirmed', final_name=%s WHERE file_id=%s",
                    (orig_path.name, file_id))
        already += 1
        continue
    
    # Don't overwrite existing
    if new_path.exists() and new_path != orig_path:
        try:
            print(f"  SKIP (target exists): {proposed}", flush=True)
        except:
            pass
        skipped += 1
        continue
    
    # Do the rename
    try:
        orig_path.rename(new_path)
        cur.execute("""
            UPDATE files SET status='confirmed', final_name=%s, file_path=%s
            WHERE file_id=%s
        """, (proposed, str(new_path), file_id))
        try:
            print(f"  OK [{row['confidence']:.0f}%] {row['original_name'][:40]:40} -> {proposed}", flush=True)
        except UnicodeEncodeError:
            print(f"  OK [{row['confidence']:.0f}%] [unicode] -> {proposed}", flush=True)
        approved += 1
    except Exception as e:
        try:
            print(f"  ERR {row['original_name']}: {e}", flush=True)
        except:
            print(f"  ERR [unicode]: {e}", flush=True)
        errors += 1

print(f"\n{'='*50}", flush=True)
print(f"  Approved & renamed: {approved}", flush=True)
print(f"  Already FIS format: {already}", flush=True)
print(f"  Skipped:            {skipped}", flush=True)
print(f"  Errors:             {errors}", flush=True)

conn.close()
