import sys, os
sys.path.insert(0, r'D:\GitHub\file-intelligence-system')

from fis.nlp.engines import YakeEngine
from fis.nlp.classifier import FISClassifier
from fis.nlp.path_heuristics import apply_path_rules, apply_filename_heuristic

clf = FISClassifier(model_dir=r'D:\GitHub\file-intelligence-system\models\saved')
yake_eng = YakeEngine()

test_folders = [
    ('ARCHIVE_OLD_AXIOM_VERSIONS', r'B:\transfer\Desktop STAY'),
    ('Master Obsidian', r'B:\transfer\Desktop STAY'),
    ('Theophysics_Master', r'B:\transfer\Desktop STAY'),
    ('Sequential_Papers', r'B:\transfer\Desktop STAY'),
    ('Adam and EVE', r'B:\transfer\Desktop STAY'),
    ('ParameterExplorer', r'B:\transfer\Desktop STAY'),
    ('Moral decline of America', r'B:\transfer\Desktop STAY\EXPORT'),
    ('01-Laws', r'B:\transfer\Desktop STAY\Theophysics_Master'),
    ('00-Index', r'B:\transfer\Desktop STAY\Theophysics_Master'),
    ('99-Glossary', r'B:\transfer\Desktop STAY\Theophysics_Master'),
]

for folder_name, parent_path in test_folders:
    text = folder_name.replace('_', ' ').replace('-', ' ')
    raw_kws = yake_eng.extract(text)
    keywords = raw_kws
    
    result = clf.classify(text, keywords, [])
    result = apply_path_rules(result, parent_path)
    result = apply_filename_heuristic(result, folder_name, '')
    
    domain = result.get('domain', 'DC')
    subjects = result.get('subjects', ['GN'])
    conf = result.get('confidence', 0)
    kws = [k["keyword"] for k in keywords[:3]]
    
    print(f"{folder_name}")
    print(f"  -> {domain}.{subjects[0] if subjects else 'GN'}  conf={conf:.0f}%  kws={kws}")
    print()
