"""FIS Context-Aware Classifier — Chow-style folder decomposition.
Scans B:\transfer\Desktop STAY with folder-context-first approach.
"""
import sys, os, re, json
from pathlib import Path
from collections import Counter

ROOT = Path(r"B:\transfer\Desktop STAY")

def tokenize_name(name):
    stem = Path(name).stem
    stem = re.sub(r'^\d+[_\-]*', '', stem)
    tokens = re.split(r'[_\-.\s]+', stem)
    expanded = []
    for t in tokens:
        parts = re.sub(r'([a-z])([A-Z])', r'\1 \2', t).split()
        expanded.extend(parts)
    return [t.lower() for t in expanded if len(t) > 1]

def survey():
    """Survey the root: folders vs loose files, file types, name patterns."""
    dirs = sorted([d for d in ROOT.iterdir() if d.is_dir()
                   and not d.name.startswith('.')])
    files = sorted([f for f in ROOT.iterdir() if f.is_file()
                    and not f.name.startswith('.')])

    print(f"=== B:\\transfer\\Desktop STAY ===")
    print(f"  {len(dirs)} folders, {len(files)} loose files\n")

    # Folder inventory
    print("=== FOLDERS ===")
    for d in dirs:
        contents = list(d.iterdir())
        n_files = sum(1 for c in contents if c.is_file())
        n_dirs = sum(1 for c in contents if c.is_dir())
        exts = Counter(c.suffix.lower() for c in contents if c.is_file())
        top_ext = exts.most_common(3)
        print(f"  {d.name:45s} {n_files:3d} files, {n_dirs:2d} subdirs  {top_ext}")

    # Loose file inventory
    print(f"\n=== LOOSE FILES ({len(files)}) ===")
    ext_counts = Counter(f.suffix.lower() for f in files)
    print(f"  Extensions: {dict(ext_counts.most_common(10))}")

    # Categorize loose files by extension
    by_ext = {}
    for f in files:
        ext = f.suffix.lower()
        by_ext.setdefault(ext, []).append(f.name)

    # Show loose files grouped
    for ext in sorted(by_ext, key=lambda e: -len(by_ext[e])):
        names = by_ext[ext]
        print(f"\n  [{ext}] ({len(names)} files)")
        for n in names[:8]:
            tokens = tokenize_name(n)
            print(f"    {n[:60]:60s} tokens={tokens[:5]}")
        if len(names) > 8:
            print(f"    ... and {len(names)-8} more")

    # Folder content analysis — Chow decomposition preview
    print("\n=== CHOW DECOMPOSITION (folder homogeneity) ===")
    for d in dirs:
        if d.name.startswith('.') or d.name.startswith('_'):
            continue
        sub_files = [f for f in d.rglob('*') if f.is_file()]
        if not sub_files:
            continue

        # Collect all filename tokens across folder
        all_tokens = []
        for f in sub_files:
            all_tokens.extend(tokenize_name(f.name))

        token_freq = Counter(all_tokens)
        top_tokens = token_freq.most_common(8)

        # How many distinct "themes" in this folder?
        # If top 3 tokens cover >60% of all token mass, it's 1-pattern
        total = sum(token_freq.values())
        top3_mass = sum(c for _, c in token_freq.most_common(3))
        coverage = top3_mass / total if total > 0 else 0

        if coverage > 0.4:
            patterns = 1
        elif coverage > 0.25:
            patterns = 2
        else:
            patterns = 3

        label = {1: "UNIFORM", 2: "SPLIT", 3: "MIXED"}[patterns]
        print(f"  {d.name:35s} {len(sub_files):4d} files  "
              f"{label} (top3={coverage:.0%})  {top_tokens[:5]}")


if __name__ == "__main__":
    survey()
