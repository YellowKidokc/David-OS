"""
One-time script to enrich subject_codes trigger_words with broader semantic coverage.
Run once: python _enrich_clusters.py
"""
import psycopg2

DB = dict(host='192.168.1.97', port=5432, dbname='fis_db', user='postgres', password='Moss9pep28$')

ENRICHMENTS = {
    # Theophysics general catch-all terms
    'AX': ['axiom', 'axioms', 'formal', 'tier', 'postulate', 'foundational', 'versions',
            'archive', 'old', 'consolidated', 'expanded', 'principles', 'definitions'],
    'LG': ['paper', 'papers', 'publication', 'logos', 'sequential', 'series', 'formal',
            'document', 'manuscript', 'draft', 'essay', 'article', 'writings', 'volume'],
    'MQ': ['master', 'equation', 'chi', 'convergence', 'kernel', 'theophysics', 'framework',
            'variables', 'integral', 'superfactor', 'lowe', 'coherence', 'lagrangian'],
    'CS': ['consciousness', 'observer', 'qualia', 'awareness', 'mind', 'subjective',
            'parameter', 'explorer', 'parameterexplorer', 'brain', 'neural'],
    'IS': ['isomorphism', 'mapping', 'structural', 'correspondence', 'bridge', 'dual',
            'parallel', 'symmetry', 'adam', 'eve', 'creation', 'genesis', 'origin'],
    'JS': ['jesus', 'christ', 'christology', 'incarnation', 'messiah', 'savior', 'lord',
            'cross', 'gospel', 'adam', 'eve', 'fall', 'redemption'],
    'EN': ['entropy', 'disorder', 'decay', 'judgment', 'thermodynamic', 'heat', 'chaos',
            'noise', 'breakdown', 'decline', 'moral', 'america'],
    'MR': ['moral', 'ethics', 'alignment', 'righteousness', 'good', 'evil', 'america',
            'decline', 'culture', 'society', 'values', 'virtue', 'character'],
    'CO': ['coherence', 'unity', 'integration', 'consistency', 'harmony', 'whole',
            'master', 'obsidian', 'vault', 'system', 'knowledge', 'base', 'wiki'],
    'WV': ['worldview', 'philosophy', 'metaphysics', 'ontology', 'naturalism', 'theism',
            'perspective', 'framework', 'paradigm', 'model', 'theory'],
    'FH': ['faith', 'trust', 'belief', 'pistis', 'confidence', 'commitment', 'hope'],
    'GR': ['grace', 'reentanglement', 'gravity', 'force', 'gift', 'mercy', 'favor'],
    
    # System/Infrastructure
    'GN': ['general', 'misc', 'uncategorized', 'other', 'temp', 'temporary', 'scratch',
            'export', 'exports', 'output', 'outputs', 'archive', 'backup', 'old',
            'sequential', 'papers', 'adam', 'eve', 'zzz', 'review', 'folder',
            'transfer', 'stay', 'desktop', 'files', 'docs', 'documents'],
}

# Domain-level path triggers  
DOMAIN_PATH_TRIGGERS = {
    'TP': ['theophysics', 'theophy', 'logos', 'faiththruphysics', 'convergence'],
    'DT': ['daytrading', 'day trading', 'trading', 'stocks', 'thinkorswim'],
    'SY': ['github', 'appdata', 'programfiles', 'windows', 'node_modules'],
    'OB': ['obsidian', 'vault', '_theophysics'],
    'EV': ['evidence', 'legal', 'sellvia', 'court'],
}

conn = psycopg2.connect(**DB)
conn.autocommit = True
cur = conn.cursor()

for code, new_words in ENRICHMENTS.items():
    cur.execute("""
        UPDATE subject_codes
        SET trigger_words = (
            SELECT array_agg(DISTINCT w)
            FROM unnest(COALESCE(trigger_words, '{}') || %s::text[]) AS w
        )
        WHERE code = %s
    """, (new_words, code))
    print(f"  enriched {code}")

print(f"\nDone. {len(ENRICHMENTS)} codes enriched.")
conn.close()
