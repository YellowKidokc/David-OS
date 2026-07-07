"""
Batch correct pending files where the path makes domain/subject obvious.
Runs corrections without touching actual files on disk — just updates Postgres status.
"""
import psycopg2, psycopg2.extras, re

conn = psycopg2.connect(host='192.168.1.97', port=5432, dbname='fis_db',
                        user='postgres', password='Moss9pep28$')
conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Path-based correction rules: (path_fragment, correct_domain, correct_subject)
PATH_RULES = [
    ('Logos',            'TP', 'LG'),
    ('V3_P',             'TP', 'LG'),
    ('Logos_Papers',     'TP', 'LG'),
    ('genesis-to-quantum','TP','MQ'),
    ('Theophysics',      'TP', 'MQ'),
    ('THEOPHYSICS_TREE', 'TP', 'MQ'),
    ('Moral-Universe',   'TP', 'MR'),
    ('Soul-Observer',    'TP', 'CS'),
    ('Grace-Function',   'TP', 'GR'),
    ('Hard-Problem',     'TP', 'CS'),
    ('Quantum-Bridge',   'TP', 'QC'),
    ('Stretched-Heavens','TP', 'MQ'),
    ('Algorithm-Reality','TP', 'MQ'),
    ('Logos-Principle',  'TP', 'LG'),
    ('Physics-Principalities', 'TP', 'EN'),
    ('Decalogue-Cosmos', 'TP', 'MR'),
    ('Protocols-Validation', 'TP', 'LG'),
    ('Creatio-Silico',   'TP', 'CS'),
    ('Day-Trading',      'DT', 'JR'),
    ('openclaw',         'AP', 'SC'),
    ('Physics_of_faith', 'TP', 'MQ'),
    ('Forge',            'AP', 'SC'),
]

# Filename-based slug fixes (when slug is clearly wrong like 'untitled' or 'patristic-parallels')
SLUG_FIXES = {
    'Scripture_Equations':     'scripture-equations',
    'VERSION_ANALYSIS':        'version-analysis',
    'Experimental_Predictions':'experimental-predictions',
    'LGS-A':                   'logos-academic',
    'LGS-B':                   'logos-beginner',
    'LGS-M':                   'logos-middle',
    'README':                  'readme',
}

cur.execute("SELECT file_id, original_name, proposed_name, file_path, domain, subject_codes FROM files WHERE status='pending'")
pending = cur.fetchall()
print(f"Processing {len(pending)} pending files...\n")

fixed = 0
for row in pending:
    path = row['file_path'] or ''
    orig = row['original_name'] or ''
    proposed = row['proposed_name'] or ''
    
    new_domain = row['domain']
    new_subj = (row['subject_codes'] or ['GN'])[0]
    changed = False
    
    # Apply path rules
    for frag, dom, subj in PATH_RULES:
        if frag.lower() in path.lower():
            if dom != new_domain or subj != new_subj:
                new_domain = dom
                new_subj = subj
                changed = True
            break
    
    # Fix bad slug
    stem = re.sub(r'\.[^.]+$', '', orig)  # strip extension
    new_slug = None
    for key, slug in SLUG_FIXES.items():
        if key.lower() in stem.lower():
            new_slug = slug
            break
    
    if not new_slug:
        # Build slug from original name
        slug_raw = re.sub(r'[^a-zA-Z0-9]+', '-', stem.lower()).strip('-')
        new_slug = slug_raw[:20].rstrip('-')
    
    # Rebuild proposed name
    ext = ''
    if '.' in orig:
        ext = '.' + orig.rsplit('.', 1)[1]
    
    # Get sequence id from current proposed name
    seq_match = re.search(r'_(\d{6})\.', proposed or '')
    seq = seq_match.group(1) if seq_match else '000000'
    
    new_proposed = f"{new_slug}_{new_domain}.{new_subj}_{seq}{ext}"
    
    if new_proposed != proposed or changed:
        cur.execute("""
            UPDATE files SET
                domain = %s,
                subject_codes = %s,
                proposed_name = %s,
                status = 'pending'
            WHERE file_id = %s
        """, (new_domain, [new_subj], new_proposed, row['file_id']))
        print(f"  FIXED [{row['file_id']}] {orig}")
        print(f"    {proposed}")
        print(f"    -> {new_proposed}")
        fixed += 1

print(f"\nFixed {fixed} of {len(pending)} pending files.")
conn.close()
