import sys
sys.path.insert(0, r'D:\GitHub\file-intelligence-system')

print("=== Checking NLP dependencies ===\n")

deps = [
    ('yake', 'yake'),
    ('spacy', 'spacy'),
    ('keybert', 'keybert'),
    ('sklearn', 'scikit-learn'),
    ('river', 'river'),
    ('faster_whisper', 'faster-whisper'),
]

for mod, name in deps:
    try:
        m = __import__(mod)
        ver = getattr(m, '__version__', '?')
        print(f"  OK  {name} ({ver})")
    except ImportError as e:
        print(f"  MISSING  {name}  -- {e}")

print()
print("=== Checking spaCy model ===")
try:
    import spacy
    nlp = spacy.load('en_core_web_sm')
    print(f"  OK  en_core_web_sm loaded")
except Exception as e:
    print(f"  MISSING  en_core_web_sm -- {e}")

print()
print("=== Checking FIS NLP modules ===")
fis_mods = [
    'fis.nlp.engines',
    'fis.nlp.classifier',
    'fis.nlp.path_heuristics',
    'fis.nlp.semantic_scorer',
    'fis.nlp.extractor',
]
for mod in fis_mods:
    try:
        __import__(mod)
        print(f"  OK  {mod}")
    except Exception as e:
        print(f"  ERROR  {mod} -- {e}")

print()
print("=== Testing YAKE on folder names ===")
try:
    import yake
    kw_extractor = yake.KeywordExtractor(lan='en', n=2, top=5)
    test = "ARCHIVE_OLD_AXIOM_VERSIONS master equation theophysics"
    kws = kw_extractor.extract_keywords(test)
    print(f"  Input: {test}")
    print(f"  Keywords: {kws}")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=== Testing classifier (rule-based) ===")
try:
    from fis.nlp.classifier import FISClassifier
    clf = FISClassifier()
    result = clf.classify(
        "master equation theophysics axioms coherence",
        [{"keyword": "master equation"}, {"keyword": "axioms"}],
        []
    )
    print(f"  Result: {result}")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=== Classifier model trained? ===")
import os
model_path = r'D:\GitHub\file-intelligence-system\models\saved\classifier.pkl'
if os.path.exists(model_path):
    size = os.path.getsize(model_path)
    print(f"  YES - {model_path} ({size} bytes)")
else:
    print(f"  NO - no trained model at {model_path}")
    print(f"  (rule-based fallback only)")
