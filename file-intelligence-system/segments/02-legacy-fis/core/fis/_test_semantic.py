"""Test the semantic scorer on Desktop STAY loose files.
Run: cd /d D:\GitHub\file-intelligence-system && python fis/_test_semantic.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fis.nlp.semantic_scorer import SemanticScorer, project_name, VAR_NAMES
from fis.nlp.extractor import extract_text


def main():
    scorer = SemanticScorer()
    root = Path(r"B:\transfer\Desktop STAY")

    # Get loose files only
    files = sorted([f for f in root.iterdir()
                    if f.is_file() and not f.name.startswith('.')])

    print(f"Scoring {len(files)} files from Desktop STAY\n")
    print(f"{'FILE':<45s} {'HASH':<10s} {'VEC (G M E S T K R Q F C)':<35s} {'PROJECTED NAME'}")
    print("-" * 130)

    for f in files:
        if f.name == 'desktop.ini':
            continue
        try:
            addr = scorer.score_file(str(f))
            projected = project_name(addr, f, mode="personal")
            vec_str = " ".join(f"{v:.1f}" for v in addr.vector)
            print(f"{f.name[:44]:<45s} {addr.coord_hash:<10s} [{vec_str}] {projected[:40]}")
        except Exception as e:
            print(f"{f.name[:44]:<45s} ERROR: {e}")


if __name__ == "__main__":
    main()
