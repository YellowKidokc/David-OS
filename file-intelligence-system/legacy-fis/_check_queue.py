import psycopg2, psycopg2.extras

conn = psycopg2.connect(host='192.168.1.97', port=5432, dbname='fis_db', user='postgres', password='Moss9pep28$')
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT file_id, sequence_id, original_name, proposed_name, final_name,
           file_path, domain, subject_codes, slug, status, confidence
    FROM files
    ORDER BY created_at DESC
    LIMIT 30
""")
rows = cur.fetchall()
print(f"Total rows returned: {len(rows)}\n")
for r in rows:
    print(f"[{r['status']}] {r['original_name']}")
    print(f"  proposed: {r['proposed_name']}")
    print(f"  domain={r['domain']} subj={r['subject_codes']} conf={r['confidence']}")
    print(f"  path: {r['file_path']}")
    print()

cur.execute("SELECT status, COUNT(*) FROM files GROUP BY status ORDER BY count DESC")
print("\n=== STATUS COUNTS ===")
for r in cur.fetchall():
    print(f"  {r['status']}: {r['count']}")

conn.close()
