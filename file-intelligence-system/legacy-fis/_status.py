import psycopg2, psycopg2.extras
conn = psycopg2.connect(host='192.168.1.97', port=5432, dbname='fis_db', user='postgres', password='Moss9pep28$')
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT status, COUNT(*) as n FROM files GROUP BY status ORDER BY n DESC")
for r in cur.fetchall():
    print(f"  {r['status']}: {r['n']}")

cur.execute("SELECT COUNT(*) as n FROM files WHERE status='pending' AND domain='DT' AND file_path LIKE '%Logos%'")
print(f"\n  DT misclassified in Logos (remaining): {cur.fetchone()['n']}")
conn.close()
