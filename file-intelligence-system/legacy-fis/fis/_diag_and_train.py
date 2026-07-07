"""FIS Diagnostic + Batch Training Script
Run: cd D:\GitHub\file-intelligence-system && python fis/_diag_and_train.py
"""
import psycopg2
import psycopg2.extras

DB = dict(host='192.168.1.97', port=5432, dbname='fis_db',
          user='postgres', password='Moss9pep28$')

def main():
    c = psycopg2.connect(**DB)
    cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 1. Domain distribution
    cur.execute("SELECT domain, COUNT(*) as cnt FROM files WHERE domain IS NOT NULL GROUP BY domain ORDER BY cnt DESC")
    print("=== DOMAIN DISTRIBUTION ===")
    for r in cur.fetchall():
        print(f"  {r['domain']}: {r['cnt']}")

    # 2. Pending files (lowest confidence)
    print("\n=== PENDING FILES (lowest confidence) ===")
    cur.execute("""SELECT original_name, domain, subject_codes, confidence, file_path
                   FROM files WHERE status = 'pending'
                   ORDER BY confidence ASC LIMIT 20""")
    for r in cur.fetchall():
        print(f"  [{r['confidence']:5.1f}] {r['domain']}/{r['subject_codes']}  {r['original_name'][:55]}")
        print(f"         {r['file_path'][:80]}")

    # 3. Correction patterns
    print("\n=== CORRECTION PATTERNS ===")
    cur.execute("""SELECT c.old_domain, c.new_domain, COUNT(*) as cnt
                   FROM corrections c GROUP BY c.old_domain, c.new_domain
                   ORDER BY cnt DESC""")
    for r in cur.fetchall():
        print(f"  {r['old_domain']} -> {r['new_domain']}: {r['cnt']}x")

    # 4. Recent corrections detail
    print("\n=== RECENT CORRECTIONS (detail) ===")
    cur.execute("""SELECT f.original_name, f.file_path, c.old_domain, c.new_domain,
                          c.old_subjects, c.new_subjects
                   FROM corrections c JOIN files f ON c.file_id = f.file_id
                   ORDER BY c.corrected_at DESC LIMIT 25""")
    for r in cur.fetchall():
        print(f"  {r['original_name'][:45]:45s} D:{r['old_domain']}->{r['new_domain']}  S:{r['old_subjects']}->{r['new_subjects']}")

    # 5. Misclassification analysis: files in GitHub getting TP/DT
    print("\n=== PATH MISMATCHES (GitHub files not classified as SY) ===")
    cur.execute("""SELECT original_name, domain, subject_codes, confidence, file_path
                   FROM files
                   WHERE file_path LIKE '%%GitHub%%'
                     AND domain NOT IN ('SY', '--')
                   ORDER BY confidence DESC LIMIT 20""")
    for r in cur.fetchall():
        print(f"  [{r['confidence']:5.1f}] {r['domain']}/{r['subject_codes']}  {r['original_name'][:50]}")

    # 6. Auto-classified files with high confidence that might be wrong
    print("\n=== HIGH-CONF AUTO (spot check) ===")
    cur.execute("""SELECT original_name, domain, subject_codes, confidence, file_path
                   FROM files WHERE status = 'auto' AND confidence >= 80
                   ORDER BY RANDOM() LIMIT 15""")
    for r in cur.fetchall():
        print(f"  [{r['confidence']:5.1f}] {r['domain']}/{r['subject_codes']}  {r['original_name'][:50]}")
        print(f"         {r['file_path'][:80]}")

    c.close()
    print("\n=== DONE ===")

if __name__ == "__main__":
    main()
