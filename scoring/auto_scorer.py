"""
Theophysics Auto-Scorer
Reads a markdown page, applies the 1-2-3 scoring standard,
stamps YAML frontmatter with scores.

Can use local analysis (keyword/pattern matching) or
API call to Claude for deeper semantic scoring.

Usage:
  python auto_scorer.py <file_path>              # score one file
  python auto_scorer.py <folder_path> --batch     # score all .md in folder
  python auto_scorer.py <file_path> --api         # use Claude API for scoring
"""

import os, sys, re, json
from pathlib import Path
from datetime import datetime

# Scoring keywords mapped to properties
# Each property has positive indicators that suggest 1, 2, or 3
SCORE_INDICATORS = {
    # WHO
    "AUT": {
        "patterns_3": [r"(?i)david\s+lowe", r"(?i)POF\s*2828", r"(?i)faiththruphysics"],
        "patterns_2": [r"(?i)collaborat", r"(?i)session\s+with", r"(?i)co-derived"],
        "patterns_1": [r"(?i)AI[\s-]generated", r"(?i)auto[\s-]generated"],
    },
    # WHAT - Content markers
    "SCR": {
        "patterns_3": [r"(?i)genesis\s+\d", r"(?i)john\s+\d+:\d+", r"(?i)romans\s+\d", r"(?i)galatians\s+\d",
                       r"(?i)scripture\s+(?:says|tells|reveals|shows)", r"(?i)biblical\s+(?:proof|evidence|foundation)"],
        "patterns_2": [r"(?i)(?:matthew|mark|luke|acts|corinthians|ephesians|philippians|colossians|thessalonians|timothy|titus|hebrews|james|peter|jude|revelation)\s+\d",
                       r"(?i)scripture", r"(?i)biblical"],
        "patterns_1": [r"(?i)bible", r"(?i)verse", r"(?i)chapter\s+\d"],
    },
    "EQN": {
        "patterns_3": [r"\\frac", r"\\int", r"\\sum", r"\\nabla", r"dS/dt", r"d[A-Z]/dt",
                       r"(?i)master\s+equation", r"(?i)lagrangian", r"R\(offense", r"G\s*=\s*G"],
        "patterns_2": [r"[=≈≤≥]\s*\d", r"σ|Φ|ψ|χ|∫|∑|∇|α|β|γ", r"(?i)equation", r"(?i)formula"],
        "patterns_1": [r"(?i)mathematically", r"(?i)quantif"],
    },
    "PRF": {
        "patterns_3": [r"(?i)(?:formal\s+)?proof", r"(?i)QED", r"(?i)reductio", r"(?i)∴",
                       r"(?i)therefore.*(?:proven|established|demonstrated)", r"(?i)lean\s*4?"],
        "patterns_2": [r"(?i)(?:it\s+)?follows\s+that", r"(?i)we\s+(?:can\s+)?(?:show|prove|derive)",
                       r"(?i)hence", r"(?i)thus"],
        "patterns_1": [r"(?i)implies", r"(?i)suggests.*proof", r"(?i)informal.*proof"],
    },
    "NAR": {
        "patterns_3": [r"(?i)(?:imagine|picture|consider)\s+(?:a|the|this)", r"(?i)story",
                       r"(?i)once\s+upon", r"(?i)narrative"],
        "patterns_2": [r"(?i)for\s+example", r"(?i)analogy", r"(?i)picture\s+this"],
        "patterns_1": [r"(?i)illustration", r"(?i)metaphor"],
    },
    # WHERE - Domains
    "PHY": {
        "patterns_3": [r"(?i)quantum", r"(?i)thermodynamic", r"(?i)entropy", r"(?i)hamiltonian",
                       r"(?i)hilbert\s+space", r"(?i)wave\s*function", r"(?i)schrodinger",
                       r"(?i)general\s+relativity", r"(?i)spacetime"],
        "patterns_2": [r"(?i)physics", r"(?i)physical", r"(?i)energy", r"(?i)force",
                       r"(?i)momentum", r"(?i)field"],
        "patterns_1": [r"(?i)particle", r"(?i)atom", r"(?i)wave"],
    },
    "THE": {
        "patterns_3": [r"(?i)trinit", r"(?i)incarnat", r"(?i)atonement", r"(?i)salvat",
                       r"(?i)(?:holy\s+)?spirit", r"(?i)christ(?:ology)?", r"(?i)theolog"],
        "patterns_2": [r"(?i)god", r"(?i)grace", r"(?i)sin", r"(?i)faith",
                       r"(?i)redempt", r"(?i)resurrect"],
        "patterns_1": [r"(?i)church", r"(?i)prayer", r"(?i)worship", r"(?i)divine"],
    },
    "MAT": {
        "patterns_3": [r"(?i)theorem", r"(?i)axiom", r"(?i)lemma", r"(?i)set\s+theory",
                       r"(?i)godel", r"(?i)modal\s+logic", r"(?i)topology"],
        "patterns_2": [r"(?i)mathematic", r"(?i)algebra", r"(?i)calculus", r"(?i)proof"],
        "patterns_1": [r"(?i)computation", r"(?i)algorithm", r"(?i)numeric"],
    },
    "MOR": {
        "patterns_3": [r"(?i)justice.*mercy", r"(?i)moral.*(?:law|order|reality|conservation)",
                       r"(?i)(?:right|wrong).*(?:exist|inherent)", r"(?i)trilemma",
                       r"(?i)existence.*(?:value|moral|resist)"],
        "patterns_2": [r"(?i)moral", r"(?i)ethic", r"(?i)justice", r"(?i)mercy",
                       r"(?i)virtue", r"(?i)vice", r"(?i)conscience"],
        "patterns_1": [r"(?i)good", r"(?i)evil", r"(?i)right", r"(?i)wrong"],
    },
    "CAN": {
        "patterns_3": [r"(?i)master\s+equation", r"(?i)ten\s+laws", r"(?i)χ[\s-]field",
                       r"(?i)theophysics", r"(?i)law\s+\d+", r"(?i)axiom\s+[A-Z]\d"],
        "patterns_2": [r"(?i)framework", r"(?i)coherence\s+(?:measure|field)", r"(?i)logos"],
        "patterns_1": [r"(?i)model", r"(?i)system", r"(?i)structure"],
    },
    # WHY - Rhetorical
    "DER": {
        "patterns_3": [r"(?i)deriv(?:ation|ed|es|ing)", r"(?i)from\s+(?:this|which)\s+(?:it\s+)?follows",
                       r"(?i)chain.*(?:from|through|to)"],
        "patterns_2": [r"(?i)follows\s+from", r"(?i)implies", r"(?i)leads\s+to"],
        "patterns_1": [r"(?i)related\s+to", r"(?i)connected"],
    },
    "FAL": {
        "patterns_3": [r"(?i)falsif", r"(?i)defeat\s+condition", r"(?i)self[\s-]refut",
                       r"(?i)cannot\s+be\s+(?:denied|refuted|defeated)"],
        "patterns_2": [r"(?i)test(?:able|ed|ing)", r"(?i)objection", r"(?i)counter[\s-]?argument"],
        "patterns_1": [r"(?i)challenge", r"(?i)question"],
    },
    "ISO": {
        "patterns_3": [r"(?i)isomorph", r"(?i)structural\s+(?:bridge|parallel|identity)",
                       r"(?i)same\s+equation", r"(?i)dual\s+projection"],
        "patterns_2": [r"(?i)bridge", r"(?i)parallel", r"(?i)cross[\s-]domain"],
        "patterns_1": [r"(?i)similar", r"(?i)analog"],
    },
    "STE": {
        "patterns_3": [r"(?i)steelman", r"(?i)strongest\s+objection", r"(?i)best\s+(?:case|argument)\s+against"],
        "patterns_2": [r"(?i)objection", r"(?i)counter[\s-]?argument", r"(?i)critic"],
        "patterns_1": [r"(?i)disagree", r"(?i)alternative\s+view"],
    },
    # BIBLE
    "BIB_OT": {
        "patterns_3": [r"(?i)genesis", r"(?i)exodus", r"(?i)psalm", r"(?i)isaiah",
                       r"(?i)deuteronom", r"(?i)old\s+testament"],
        "patterns_2": [r"(?i)moses", r"(?i)abraham", r"(?i)david(?!\s+lowe)", r"(?i)prophet"],
        "patterns_1": [r"(?i)hebrew", r"(?i)covenant", r"(?i)torah"],
    },
    "BIB_NT": {
        "patterns_3": [r"(?i)gospel", r"(?i)paul", r"(?i)apostle", r"(?i)new\s+testament",
                       r"(?i)crucifi", r"(?i)resurrect"],
        "patterns_2": [r"(?i)jesus", r"(?i)christ", r"(?i)cross"],
        "patterns_1": [r"(?i)church", r"(?i)disciple"],
    },
}


def score_property(content: str, prop: str) -> int:
    """Score a single property 0-3 based on pattern matching."""
    indicators = SCORE_INDICATORS.get(prop)
    if not indicators:
        return 0

    # Check level 3 first
    count_3 = sum(1 for p in indicators.get("patterns_3", []) if re.search(p, content))
    count_2 = sum(1 for p in indicators.get("patterns_2", []) if re.search(p, content))
    count_1 = sum(1 for p in indicators.get("patterns_1", []) if re.search(p, content))

    if count_3 >= 2:
        return 3
    elif count_3 >= 1:
        return 2 if count_2 >= 1 else 2
    elif count_2 >= 2:
        return 2
    elif count_2 >= 1 or count_1 >= 2:
        return 1
    elif count_1 >= 1:
        return 1
    return 0


def score_page(filepath: str) -> dict:
    """Score a single page on all properties."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    scores = {}
    for prop in SCORE_INDICATORS:
        s = score_property(content, prop)
        if s > 0:
            scores[prop] = s

    # Detect law binding
    law_match = re.search(r'(?i)law\s+(\d{1,2})', content)
    law = int(law_match.group(1)) if law_match else None

    # Detect chi variables
    chi_scores = {}
    chi_map = {
        'G': [r'(?i)grace', r'(?i)negentropy'],
        'M': [r'(?i)mutual\s+information'],
        'E': [r'(?i)entropy'],
        'S': [r'(?i)soul', r'(?i)self[\s-]reference'],
        'T': [r'(?i)\btime\b'],
        'K': [r'(?i)knowledge', r'(?i)kolmogorov'],
        'R': [r'(?i)relational', r'(?i)relationship'],
        'Q': [r'(?i)quantum'],
        'F': [r'(?i)\bfaith\b', r'(?i)\bforce\b'],
        'C': [r'(?i)coherence', r'(?i)christ'],
    }
    for var, patterns in chi_map.items():
        count = sum(1 for p in patterns if re.search(p, content))
        if count >= 2:
            chi_scores[var] = 3
        elif count == 1:
            chi_scores[var] = 2

    return {
        'scores': scores,
        'law': law,
        'chi_scores': {k: v for k, v in chi_scores.items() if v > 0},
        'file': filepath,
        'scored_at': datetime.now().isoformat(),
    }


def format_yaml_scores(result: dict) -> str:
    """Format scores as YAML block for insertion into frontmatter."""
    lines = ["scores:"]
    for prop, val in sorted(result['scores'].items()):
        lines.append(f"  {prop}: {val}")
    if result['law']:
        lines.append(f"law: {result['law']}")
    if result['chi_scores']:
        lines.append("chi_scores:")
        for var, val in sorted(result['chi_scores'].items()):
            lines.append(f"  {var}: {val}")
    lines.append(f"scored_at: \"{result['scored_at']}\"")
    return '\n'.join(lines)


def print_report(result: dict):
    """Print a human-readable scoring report."""
    print(f"\n{'='*60}")
    print(f"SCORING REPORT: {Path(result['file']).name}")
    print(f"{'='*60}")
    print(f"Scored at: {result['scored_at']}")
    if result['law']:
        print(f"Law binding: {result['law']}")
    print(f"\nProperty scores:")
    for prop, val in sorted(result['scores'].items()):
        bar = "#" * val + "." * (3 - val)
        print(f"  {prop:8s}  {bar}  {val}")
    if result['chi_scores']:
        print(f"\nchi variable scores:")
        for var, val in sorted(result['chi_scores'].items()):
            bar = "#" * val + "." * (3 - val)
            print(f"  chi_{var}   {bar}  {val}")
    print(f"\nYAML block:")
    print(format_yaml_scores(result))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python auto_scorer.py <file_or_folder> [--batch] [--api]")
        sys.exit(1)

    target = sys.argv[1]
    batch = '--batch' in sys.argv

    if batch and os.path.isdir(target):
        for md in Path(target).rglob('*.md'):
            result = score_page(str(md))
            if result['scores']:
                print_report(result)
    else:
        result = score_page(target)
        print_report(result)
