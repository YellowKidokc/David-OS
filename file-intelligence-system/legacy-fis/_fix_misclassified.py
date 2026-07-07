import psycopg2, psycopg2.extras, re, sys

conn = psycopg2.connect(host='192.168.1.97', port=5432, dbname='fis_db', user='postgres', password='Moss9pep28$')
conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Fix remaining DT misclassified in Logos paths
cur.execute("""
    SELECT file_id, original_name, proposed_name, file_path, domain, subject_codes
    FROM files
    WHERE status = 'pending'
      AND domain != 'TP'
      AND (
        file_path ILIKE '%Logos%'
        OR file_path ILIKE '%Theophysics%'
        OR file_path ILIKE '%genesis-to-quantum%'
        OR file_path ILIKE '%faiththruphysics%'
        OR file_path ILIKE '%V3_P%'
        OR file_path ILIKE '%Moral%Universe%'
        OR file_path ILIKE '%Soul%Observer%'
        OR file_path ILIKE '%Grace%Function%'
      )
""")
rows = cur.fetchall()
print(f"Found {len(rows)} non-TP files in TP paths\n", flush=True)

fixed = 0
for row in rows:
    orig = row['original_name'] or ''
    proposed = row['proposed_name'] or ''
    
    # Determine best subject from path
    path = row['file_path'] or ''
    if 'V3_P' in path or 'Logos' in path:
        new_subj = 'LG'
    elif 'Moral' in path:
        new_subj = 'MR'
    elif 'Soul' in path or 'Observer' in path:
        new_subj = 'CS'
    elif 'Grace' in path:
        new_subj = 'GR'
    elif 'genesis-to-quantum' in path.lower():
        new_subj = 'MQ'
    else:
        new_subj = 'MQ'

    # Build slug from original name
    stem = re.sub(r'\.[^.]+$', '', orig)
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', stem.lower()).strip('-')[:20].rstrip('-')
    
    # Get extension
    ext = ('.' + orig.rsplit('.', 1)[1]) if '.' in orig else ''
    
    # Get seq id
    seq_match = re.search(r'_(\d{6})', proposed or '')
    seq = seq_match.group(1) if seq_match else '000000'
    
    new_proposed = f"{slug}_TP.{new_subj}_{seq}{ext}"
    
    cur.execute("""
        UPDATE files SET domain='TP', subject_codes=%s, proposed_name=%s
        WHERE file_id=%s
    """, ([new_subj], new_proposed, row['file_id']))
    
    try:
        print(f"  [{row['file_id']}] {orig[:40]} -> {new_proposed}", flush=True)
    except UnicodeEncodeError:
        print(f"  [{row['file_id']}] (unicode name) -> {new_proposed}", flush=True)
    fixed += 1

print(f"\nFixed {fixed} files.", flush=True)
conn.close()
