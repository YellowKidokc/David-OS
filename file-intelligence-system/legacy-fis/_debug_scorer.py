import sys, re
sys.path.insert(0, '.')
import psycopg2, psycopg2.extras

DB = dict(host='192.168.1.97', port=5432, dbname='fis_db', user='postgres', password='Moss9pep28$')

test_folders = [
    ('ARCHIVE_OLD_AXIOM_VERSIONS', r'B:\transfer\Desktop STAY'),
    ('Master Obsidian', r'B:\transfer\Desktop STAY'),
    ('Theophysics_Master', r'B:\transfer\Desktop STAY'),
    ('Sequential_Papers', r'B:\transfer\Desktop STAY'),
    ('EXPORT', r'B:\transfer\Desktop STAY'),
    ('Adam and EVE', r'B:\transfer\Desktop STAY'),
    ('ParameterExplorer', r'B:\transfer\Desktop STAY'),
]

conn = psycopg2.connect(**DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute('SELECT code, label, domain, trigger_words, aliases FROM subject_codes')
rows = cur.fetchall()
conn.close()

clusters = {}
for r in rows:
    words = set()
    if r['trigger_words']:
        words.update(w.lower() for w in r['trigger_words'])
    if r['aliases']:
        words.update(a.lower() for a in r['aliases'])
    words.add(r['label'].lower())
    clusters[r['code']] = {'label': r['label'], 'domain': r['domain'], 'words': words}

print(f"Loaded {len(clusters)} subject code clusters\n")

for folder_name, parent_path in test_folders:
    name_tokens = set(re.findall(r'[a-zA-Z]+', folder_name.lower()))
    path_tokens = set(re.findall(r'[a-zA-Z]+', parent_path.lower()))
    
    scores = {}
    for code, c in clusters.items():
        name_hits = len(name_tokens & c['words'])
        path_hits = len(path_tokens & c['words'])
        score = (name_hits * 2) + path_hits
        if score > 0:
            scores[code] = score
    
    top = sorted(scores.items(), key=lambda x: -x[1])[:3]
    total = sum(scores.values()) or 1
    
    if top:
        best_code, best_score = top[0]
        conf = round(min((best_score / total) * 100, 95), 1)
        domain = clusters[best_code]['domain']
        print(f"{folder_name}")
        print(f"  -> {domain}.{best_code}  conf={conf}%  top={top}")
    else:
        print(f"{folder_name}")
        print(f"  -> NO MATCH (name_tokens={name_tokens})")
    print()
