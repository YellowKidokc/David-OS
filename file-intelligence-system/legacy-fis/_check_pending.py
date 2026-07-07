import psycopg2, psycopg2.extras

conn = psycopg2.connect(host='192.168.1.97', port=5432, dbname='fis_db', user='postgres', password='Moss9pep28$')
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Pending files — what the popup would show
cur.execute("""
    SELECT file_id, sequence_id, original_name, proposed_name,
           file_path, domain, subject_codes, confidence
    FROM files
    WHERE status = 'pending'
    ORDER BY confidence ASC, created_at DESC
    LIMIT 50
""")
rows = cur.fetchall()
print(f"PENDING: {len(rows)} shown (of 1149 total)\n")
for r in rows:
    print(f"  [{r['confidence']:.0f}%] {r['original_name']}")
    print(f"    -> {r['proposed_name']}")
    print(f"    domain={r['domain']} subj={r['subject_codes']}")
    print(f"    {r['file_path'][:80]}")
    print()

# Kickouts — files FIS flagged as needing human review
print("\n=== KICKOUTS (846 total, sample) ===\n")
cur.execute("""
    SELECT file_id, original_name, proposed_name, file_path, domain, confidence
    FROM files
    WHERE status = 'kickout'
    ORDER BY created_at DESC
    LIMIT 20
""")
for r in cur.fetchall():
    print(f"  [{r['confidence']:.0f}%] {r['original_name']}")
    print(f"    -> {r['proposed_name']}")
    print(f"    {r['file_path'][:80]}")
    print()

conn.close()
