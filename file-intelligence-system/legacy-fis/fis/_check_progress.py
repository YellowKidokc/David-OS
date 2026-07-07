from fis.db.connection import get_connection
c = get_connection()
cur = c.cursor()
cur.execute("SELECT COUNT(*) as cnt FROM files")
print("Total files in DB:", cur.fetchone()["cnt"])
cur.execute("SELECT status, COUNT(*) as cnt FROM files GROUP BY status ORDER BY cnt DESC")
for r in cur.fetchall():
    print(f"  {r['status']}: {r['cnt']}")
c.close()
