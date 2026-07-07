import psycopg2, psycopg2.extras

conn = psycopg2.connect(host='192.168.1.97', port=5432, dbname='fis_db', user='postgres', password='Moss9pep28$')
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Analyze pending by confidence and domain to see what's safe to bulk approve
print("=== PENDING BY CONFIDENCE ===")
cur.execute("""
    SELECT 
        CASE 
            WHEN confidence >= 80 THEN 'HIGH (80-100%)'
            WHEN confidence >= 60 THEN 'MED (60-79%)'
            WHEN confidence >= 40 THEN 'LOW (40-59%)'
            ELSE 'VERY LOW (<40%)'
        END as band,
        COUNT(*) as n,
        COUNT(*) FILTER (WHERE proposed_name NOT ILIKE '%untitled%') as has_good_slug
    FROM files WHERE status='pending'
    GROUP BY band ORDER BY band
""")
for r in cur.fetchall():
    print(f"  {r['band']}: {r['n']} files ({r['has_good_slug']} with good slug)")

print("\n=== PENDING BY DOMAIN ===")
cur.execute("""
    SELECT domain, COUNT(*) as n,
           ROUND(AVG(confidence)) as avg_conf,
           COUNT(*) FILTER (WHERE confidence >= 70) as high_conf
    FROM files WHERE status='pending'
    GROUP BY domain ORDER BY n DESC
""")
for r in cur.fetchall():
    print(f"  {r['domain']}: {r['n']} files, avg={r['avg_conf']}%, high_conf={r['high_conf']}")

print("\n=== SAFE TO BULK APPROVE (conf>=70, good slug, domain=TP) ===")
cur.execute("""
    SELECT COUNT(*) as n FROM files 
    WHERE status='pending' 
      AND confidence >= 70
      AND proposed_name NOT ILIKE '%untitled%'
      AND proposed_name NOT ILIKE '%tbd%'
      AND proposed_name IS NOT NULL
      AND domain = 'TP'
""")
print(f"  {cur.fetchone()['n']} files")

print("\n=== RISKY (needs review) ===")
cur.execute("""
    SELECT COUNT(*) as n FROM files 
    WHERE status='pending' 
      AND (confidence < 50 
           OR proposed_name ILIKE '%untitled%'
           OR proposed_name ILIKE '%tbd%'
           OR domain NOT IN ('TP','DT','SY','AP','EV'))
""")
print(f"  {cur.fetchone()['n']} files")

print("\n=== SAMPLE SAFE ONES ===")
cur.execute("""
    SELECT file_id, original_name, proposed_name, domain, confidence, file_path
    FROM files 
    WHERE status='pending' AND confidence >= 70
      AND proposed_name NOT ILIKE '%untitled%'
      AND domain='TP'
    ORDER BY confidence DESC
    LIMIT 15
""")
for r in cur.fetchall():
    print(f"  [{r['confidence']:.0f}%] {r['original_name'][:35]:35} -> {r['proposed_name']}")

conn.close()
