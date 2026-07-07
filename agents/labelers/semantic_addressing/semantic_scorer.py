"""Semantic Address Scoring Engine — χ-field vector computation.

Maps file content to a 10-dimensional vector [G,M,E,S,T,K,R,Q,F,C]
using deterministic NLP signal detection. No LLM calls.

Architecture:
  1. Extract text (existing FIS extractor)
  2. Extract keywords (YAKE) + entities (spaCy) 
  3. Match against 250 signal words → variable weights
  4. Add structural heuristics (extension, size, links, sentences)
  5. Normalize to 0-3 per variable
  6. Encode 20-bit coordinate hash
  7. Determine magnitude + state
  8. Project into naming mode

CRITICAL RULE: All variables score the document AS AN ARTIFACT —
its own structure, completeness, and internal properties.
Do NOT score what the document describes or discusses as a topic.
A paper about chaos is not chaotic. A fragment about God is still a fragment.
"""

import re
import math
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ============================================================
# SIGNAL WORD TABLE — 250 terms mapped to variable weights
# Each entry: "signal_word": {"VAR": weight, ...}
# Weights 0.0-1.0. A word can activate multiple variables.
# ============================================================

SIGNAL_WORDS = {
    # --- G: Authority / Ground ---
    "axiom": {"G": 0.9, "K": 0.3},
    "axiomatic": {"G": 0.9, "K": 0.3},
    "foundational": {"G": 0.8, "K": 0.2},
    "fundamental": {"G": 0.7, "K": 0.3},
    "authoritative": {"G": 0.8},
    "governing": {"G": 0.8, "R": 0.2},
    "constitution": {"G": 0.9, "R": 0.3, "K": 0.2},
    "sovereign": {"G": 0.9},
    "absolute": {"G": 0.7},
    "transcendent": {"G": 0.8},
    "grounding": {"G": 0.7},
    "postulate": {"G": 0.8, "K": 0.3},
    "given": {"G": 0.4},
    "premise": {"G": 0.6, "K": 0.3},
    "irreducible": {"G": 0.7},
    "self-evident": {"G": 0.9, "K": 0.2},
    "first cause": {"G": 0.9},
    "origin": {"G": 0.6, "T": 0.3},
    "creation": {"G": 0.7, "M": 0.3},
    "decree": {"G": 0.8, "R": 0.2},
    "canon": {"G": 0.7, "K": 0.2},
    "canonical": {"G": 0.7, "K": 0.3},
    "law": {"G": 0.5, "K": 0.3, "R": 0.2},
    "statute": {"G": 0.7, "K": 0.3},
    "ruling": {"G": 0.7, "K": 0.2},
    "verdict": {"G": 0.6, "C": 0.4},
    "ordained": {"G": 0.8},
    "mandate": {"G": 0.7, "R": 0.2},

    # --- M: Mechanism / Action ---
    "execute": {"M": 0.9},
    "function": {"M": 0.7, "K": 0.2},
    "process": {"M": 0.7},
    "algorithm": {"M": 0.8, "K": 0.3},
    "pipeline": {"M": 0.8},
    "script": {"M": 0.9},
    "implementation": {"M": 0.8},
    "deploy": {"M": 0.7},
    "build": {"M": 0.7},
    "compile": {"M": 0.8},
    "install": {"M": 0.8},
    "automate": {"M": 0.8},
    "procedure": {"M": 0.7, "K": 0.2},
    "workflow": {"M": 0.7},
    "handler": {"M": 0.8},
    "watcher": {"M": 0.8},
    "server": {"M": 0.7},
    "client": {"M": 0.5, "R": 0.3},
    "endpoint": {"M": 0.7, "R": 0.3},
    "api": {"M": 0.7, "R": 0.3},
    "route": {"M": 0.7},
    "import": {"M": 0.6},
    "def ": {"M": 0.9},
    "class ": {"M": 0.7, "K": 0.2},
    "return": {"M": 0.8},
    "if ": {"M": 0.5},
    "for ": {"M": 0.5},
    "while ": {"M": 0.5},
    "run": {"M": 0.7},
    "start": {"M": 0.6},
    "stop": {"M": 0.5},
    "trigger": {"M": 0.6},
    "batch": {"M": 0.7},
    "convert": {"M": 0.7},
    "transform": {"M": 0.7},
    "parse": {"M": 0.7, "K": 0.2},

    # --- E: Entropy / Disorder (artifact entropy, not subject) ---
    "todo": {"E": 0.6},
    "fixme": {"E": 0.7},
    "hack": {"E": 0.7},
    "broken": {"E": 0.8},
    "untitled": {"E": 0.7},
    "temp": {"E": 0.6},
    "draft": {"E": 0.5},
    "wip": {"E": 0.6},
    "scratch": {"E": 0.7},
    "junk": {"E": 0.9},
    "misc": {"E": 0.6},
    "random": {"E": 0.5},
    "unnamed": {"E": 0.7},
    "copy of": {"E": 0.5},
    "new 1": {"E": 0.8},
    "new 2": {"E": 0.8},
    "test": {"E": 0.4, "M": 0.3},
    "old": {"E": 0.4, "T": 0.3},
    "backup": {"E": 0.4, "T": 0.2},
    "duplicate": {"E": 0.6},
    "(1)": {"E": 0.5},
    "(2)": {"E": 0.5},

    # --- S: Identity / Self ---
    "identity": {"S": 0.7, "Q": 0.2},
    "personhood": {"S": 0.9},
    "self": {"S": 0.6, "Q": 0.3},
    "soul": {"S": 0.8},
    "spirit": {"S": 0.7},
    "consciousness": {"S": 0.5, "Q": 0.5},
    "who am i": {"S": 0.9, "Q": 0.3},
    "autobiography": {"S": 0.8, "Q": 0.3, "T": 0.2},
    "memoir": {"S": 0.7, "Q": 0.4, "T": 0.3},
    "testimony": {"S": 0.7, "Q": 0.3, "F": 0.2},
    "confession": {"S": 0.7, "Q": 0.4},
    "journal": {"S": 0.5, "Q": 0.3, "T": 0.3},
    "diary": {"S": 0.6, "Q": 0.4, "T": 0.3},
    "portrait": {"S": 0.6, "Q": 0.3},
    "biography": {"S": 0.6, "T": 0.3, "K": 0.2},
    "personal": {"S": 0.5, "Q": 0.2},
    "inner": {"S": 0.5, "Q": 0.4},
    "existential": {"S": 0.7, "Q": 0.3},

    # --- T: Time / Sequence ---
    "history": {"T": 0.7, "K": 0.3},
    "historical": {"T": 0.7, "K": 0.2},
    "timeline": {"T": 0.9},
    "chronology": {"T": 0.9},
    "evolution": {"T": 0.6, "M": 0.3},
    "progression": {"T": 0.7},
    "phase": {"T": 0.6},
    "stage": {"T": 0.6},
    "era": {"T": 0.7},
    "epoch": {"T": 0.7},
    "version": {"T": 0.5, "M": 0.2},
    "v1": {"T": 0.4},
    "v2": {"T": 0.4},
    "v3": {"T": 0.4},
    "changelog": {"T": 0.7, "M": 0.2},
    "update": {"T": 0.5, "M": 0.3},
    "legacy": {"T": 0.6},
    "archive": {"T": 0.5, "E": 0.2},
    "before": {"T": 0.4},
    "after": {"T": 0.4},
    "sequence": {"T": 0.6, "M": 0.2},
    "lifecycle": {"T": 0.7},
    "deadline": {"T": 0.6, "M": 0.2},
    "schedule": {"T": 0.6, "M": 0.2},
    "1950": {"T": 0.5}, "1960": {"T": 0.5}, "1970": {"T": 0.5},
    "1980": {"T": 0.5}, "1990": {"T": 0.5}, "2000": {"T": 0.5},
    "2010": {"T": 0.5}, "2020": {"T": 0.5}, "2025": {"T": 0.5},
    "2026": {"T": 0.5},

    # --- K: Knowledge / Information ---
    "theorem": {"K": 0.8, "G": 0.3},
    "proof": {"K": 0.7, "G": 0.3, "C": 0.2},
    "definition": {"K": 0.8},
    "equation": {"K": 0.7, "M": 0.2},
    "formula": {"K": 0.7, "M": 0.2},
    "analysis": {"K": 0.7},
    "study": {"K": 0.6},
    "research": {"K": 0.6},
    "data": {"K": 0.7},
    "dataset": {"K": 0.8},
    "database": {"K": 0.7, "M": 0.2},
    "taxonomy": {"K": 0.8, "C": 0.2},
    "classification": {"K": 0.7, "C": 0.2},
    "reference": {"K": 0.6, "R": 0.2},
    "documentation": {"K": 0.7, "M": 0.2},
    "specification": {"K": 0.8, "M": 0.2},
    "report": {"K": 0.6},
    "summary": {"K": 0.6, "C": 0.2},
    "evidence": {"K": 0.6, "F": 0.2},
    "finding": {"K": 0.6},
    "conclusion": {"K": 0.5, "C": 0.3},
    "argument": {"K": 0.6, "C": 0.2, "F": 0.2},
    "claim": {"K": 0.5, "F": 0.3},
    "hypothesis": {"K": 0.5, "F": 0.4},
    "observation": {"K": 0.6, "Q": 0.2},
    "principle": {"K": 0.6, "G": 0.3},
    "model": {"K": 0.6, "M": 0.3},
    "framework": {"K": 0.6, "C": 0.3},
    "master": {"K": 0.4, "C": 0.3},

    # --- R: Relation / Bond ---
    "relationship": {"R": 0.8},
    "covenant": {"R": 0.8, "G": 0.2, "F": 0.2},
    "contract": {"R": 0.8, "G": 0.2},
    "agreement": {"R": 0.7},
    "obligation": {"R": 0.7, "G": 0.2},
    "dependency": {"R": 0.7, "M": 0.2},
    "connection": {"R": 0.6},
    "network": {"R": 0.7, "M": 0.2},
    "community": {"R": 0.6, "S": 0.2},
    "social": {"R": 0.5, "S": 0.2},
    "marriage": {"R": 0.9, "G": 0.2, "F": 0.2},
    "family": {"R": 0.7, "S": 0.2},
    "partner": {"R": 0.6},
    "collaboration": {"R": 0.7},
    "alliance": {"R": 0.7},
    "bond": {"R": 0.8},
    "between": {"R": 0.4},
    "mutual": {"R": 0.5},
    "interaction": {"R": 0.6, "M": 0.2},
    "correspondence": {"R": 0.6, "K": 0.2},
    "isomorphism": {"R": 0.5, "K": 0.3, "C": 0.3},

    # --- Q: Experience / Felt ---
    "feel": {"Q": 0.7},
    "feeling": {"Q": 0.8},
    "experience": {"Q": 0.7},
    "emotion": {"Q": 0.8},
    "beautiful": {"Q": 0.6},
    "terrible": {"Q": 0.6},
    "amazing": {"Q": 0.6},
    "wonder": {"Q": 0.6},
    "fear": {"Q": 0.6},
    "joy": {"Q": 0.7},
    "pain": {"Q": 0.7},
    "love": {"Q": 0.5, "R": 0.3},
    "hate": {"Q": 0.5},
    "dream": {"Q": 0.6, "F": 0.2},
    "nightmare": {"Q": 0.7},
    "perception": {"Q": 0.7, "K": 0.2},
    "intuition": {"Q": 0.6, "F": 0.3},
    "aesthetic": {"Q": 0.7},
    "subjective": {"Q": 0.7},
    "perspective": {"Q": 0.5, "K": 0.2},
    "narrative": {"Q": 0.5, "S": 0.2, "T": 0.2},
    "story": {"Q": 0.4, "S": 0.2, "T": 0.2},
    "voice": {"Q": 0.5, "S": 0.3},
    "taste": {"Q": 0.6},
    "impression": {"Q": 0.6},

    # --- F: Faith / Trust ---
    "faith": {"F": 0.9},
    "trust": {"F": 0.8},
    "believe": {"F": 0.7},
    "belief": {"F": 0.7},
    "assumption": {"F": 0.6, "K": 0.2},
    "presupposition": {"F": 0.7, "G": 0.2},
    "commitment": {"F": 0.7, "R": 0.2},
    "confidence": {"F": 0.6},
    "hope": {"F": 0.6, "Q": 0.2},
    "promise": {"F": 0.7, "R": 0.3},
    "vow": {"F": 0.8, "R": 0.3},
    "risk": {"F": 0.5},
    "uncertainty": {"F": 0.5, "E": 0.3},
    "rely": {"F": 0.6},
    "reliance": {"F": 0.6},
    "loyalty": {"F": 0.6, "R": 0.3},
    "devotion": {"F": 0.7, "Q": 0.2},
    "conviction": {"F": 0.7},
    "allegiance": {"F": 0.6, "R": 0.3},
    "prophecy": {"F": 0.6, "G": 0.3, "T": 0.2},
    "revelation": {"F": 0.5, "G": 0.4, "K": 0.2},

    # --- C: Coherence / Unity ---
    "coherence": {"C": 0.9},
    "unified": {"C": 0.8},
    "integration": {"C": 0.7},
    "consistent": {"C": 0.7},
    "harmony": {"C": 0.7},
    "systematic": {"C": 0.7, "K": 0.2},
    "comprehensive": {"C": 0.6, "K": 0.2},
    "complete": {"C": 0.6},
    "holistic": {"C": 0.7},
    "synthesis": {"C": 0.7, "K": 0.2},
    "convergence": {"C": 0.7},
    "alignment": {"C": 0.6, "R": 0.2},
    "integrity": {"C": 0.7},
    "closure": {"C": 0.6},
    "resolution": {"C": 0.6},
    "therefore": {"C": 0.5, "K": 0.3},
    "thus": {"C": 0.4, "K": 0.2},
    "hence": {"C": 0.4, "K": 0.2},
    "consequently": {"C": 0.5, "K": 0.2},
    "qed": {"C": 0.8, "K": 0.3, "G": 0.2},
    "logos": {"C": 0.7, "G": 0.3},
}

# ============================================================
# STRUCTURAL HEURISTICS — score the artifact, not the subject
# ============================================================

# Extension → variable priors (what the file IS functionally)
EXTENSION_PRIORS = {
    # Code = Mechanism
    ".py": {"M": 1.5}, ".js": {"M": 1.5}, ".ts": {"M": 1.5},
    ".jsx": {"M": 1.2}, ".tsx": {"M": 1.2}, ".rs": {"M": 1.5},
    ".go": {"M": 1.5}, ".java": {"M": 1.5}, ".cpp": {"M": 1.5},
    ".c": {"M": 1.5}, ".rb": {"M": 1.2}, ".php": {"M": 1.2},
    ".sql": {"M": 1.0, "K": 0.5},
    # Scripts/configs = Mechanism
    ".bat": {"M": 1.2}, ".sh": {"M": 1.2}, ".ps1": {"M": 1.2},
    ".cmd": {"M": 1.2}, ".ahk": {"M": 1.2},
    ".ini": {"M": 0.8}, ".cfg": {"M": 0.8}, ".toml": {"M": 0.8},
    ".yaml": {"M": 0.8}, ".yml": {"M": 0.8}, ".json": {"M": 0.5, "K": 0.5},
    # Documents = Knowledge
    ".md": {"K": 0.8}, ".txt": {"K": 0.5},
    ".docx": {"K": 0.8}, ".doc": {"K": 0.8},
    ".pdf": {"K": 0.8},
    ".html": {"K": 0.5},
    # Data = Knowledge + Relation
    ".xlsx": {"K": 0.8, "R": 0.3}, ".xls": {"K": 0.8, "R": 0.3},
    ".csv": {"K": 0.8, "R": 0.3},
    # Media
    ".mp3": {"Q": 0.5}, ".mp4": {"Q": 0.5, "M": 0.3},
    ".png": {"Q": 0.3}, ".jpg": {"Q": 0.3},
    # Archives
    ".zip": {"E": 0.3, "T": 0.2}, ".tar": {"E": 0.3, "T": 0.2},
}

# Variable names for ordering
VAR_NAMES = ["G", "M", "E", "S", "T", "K", "R", "Q", "F", "C"]
VAR_INDEX = {v: i for i, v in enumerate(VAR_NAMES)}


@dataclass
class SemanticAddress:
    """A file's position in 10-dimensional meaning space."""
    vector: list[float] = field(default_factory=lambda: [0.0] * 10)
    magnitude: int = 1        # 1=fragment, 2=substantial, 3=comprehensive
    state: str = "W"          # D=draft, W=working, F=final, X=fragment
    dominant: list[str] = field(default_factory=list)  # top 2-3 vars
    coord_hash: str = ""      # decodable 20-bit address
    scores_raw: dict = field(default_factory=dict)

    @property
    def vector_dict(self) -> dict:
        return {VAR_NAMES[i]: self.vector[i] for i in range(10)}


class SemanticScorer:
    """Deterministic scorer — no LLM, no API, no divergence."""

    def __init__(self):
        self._signal_table = SIGNAL_WORDS
        self._ext_priors = EXTENSION_PRIORS

    def score_file(self, file_path: str, text: str = None,
                   keywords: list[dict] = None) -> SemanticAddress:
        """Score a file and produce its semantic address.

        Args:
            file_path: path to the file
            text: pre-extracted text (optional, extracted if missing)
            keywords: pre-extracted YAKE keywords (optional)
        """
        path = Path(file_path)
        raw_scores = {v: 0.0 for v in VAR_NAMES}

        # --- Layer 1: Extension priors ---
        ext = path.suffix.lower()
        if ext in self._ext_priors:
            for var, weight in self._ext_priors[ext].items():
                raw_scores[var] += weight

        # --- Layer 2: Filename signal words ---
        name_lower = path.stem.lower()
        for signal, weights in self._signal_table.items():
            if signal in name_lower:
                for var, w in weights.items():
                    raw_scores[var] += w * 0.5  # filename = half weight vs content

        # --- Layer 3: Content signal words ---
        if text is None:
            from fis.nlp.extractor import extract_text
            text = extract_text(file_path)

        if text and text.strip():
            text_lower = text.lower()
            text_len = len(text)

            for signal, weights in self._signal_table.items():
                count = text_lower.count(signal)
                if count > 0:
                    # Diminishing returns: log scale for repeated signals
                    effective = min(math.log2(count + 1), 4.0)
                    for var, w in weights.items():
                        raw_scores[var] += w * effective

            # --- Layer 4: Structural heuristics (artifact properties) ---
            raw_scores = self._structural_heuristics(
                raw_scores, text, text_len, path
            )
        else:
            # No text = high entropy
            raw_scores["E"] += 3.0

        # --- Normalize to 0-3 scale ---
        vector = self._normalize(raw_scores)

        # --- Compute magnitude, state, dominant vars, hash ---
        magnitude = self._compute_magnitude(text, path)
        state = self._compute_state(name_lower, text)
        dominant = self._compute_dominant(vector)
        coord_hash = self._encode_hash(vector, magnitude, state)

        return SemanticAddress(
            vector=vector,
            magnitude=magnitude,
            state=state,
            dominant=dominant,
            coord_hash=coord_hash,
            scores_raw=raw_scores,
        )

    def _structural_heuristics(self, scores: dict, text: str,
                                text_len: int, path: Path) -> dict:
        """Score artifact structure — what the document IS, not ABOUT."""
        s = dict(scores)

        # Sentence structure → Coherence
        sentences = text.count('.') + text.count('!') + text.count('?')
        if sentences > 0:
            avg_sentence_len = text_len / sentences
            if 15 < avg_sentence_len < 40:
                s["C"] += 0.5  # well-structured prose
            if sentences > 50:
                s["K"] += 0.5  # substantial content

        # Paragraph structure → Coherence
        paragraphs = text.count('\n\n') + 1
        if paragraphs > 5:
            s["C"] += 0.3
            s["K"] += 0.3

        # Headers (markdown/html) → Knowledge + Coherence
        headers = len(re.findall(r'^#{1,4}\s', text, re.MULTILINE))
        headers += len(re.findall(r'<h[1-6]', text, re.IGNORECASE))
        if headers > 3:
            s["K"] += 0.5
            s["C"] += 0.5

        # Code blocks → Mechanism
        code_blocks = text.count('```') // 2
        code_blocks += len(re.findall(r'def \w+\(', text))
        code_blocks += len(re.findall(r'function \w+\(', text))
        if code_blocks > 0:
            s["M"] += 0.5 * min(code_blocks, 5)

        # Links/references → Relation
        links = len(re.findall(r'\[.*?\]\(.*?\)', text))  # markdown
        links += len(re.findall(r'href=', text, re.IGNORECASE))
        if links > 3:
            s["R"] += 0.3 * min(links / 5, 3.0)

        # Dates in text → Time
        dates = len(re.findall(r'\b\d{4}[-/]\d{2}', text))
        dates += len(re.findall(r'\b(19|20)\d{2}\b', text))
        if dates > 2:
            s["T"] += 0.3 * min(dates / 3, 2.0)

        # Question marks → may indicate Q or F
        questions = text.count('?')
        if questions > 5:
            s["Q"] += 0.2
            s["F"] += 0.2

        # First person → S + Q
        first_person = len(re.findall(r'\b(I|my|me|mine|myself)\b', text))
        if first_person > 10:
            s["S"] += 0.5
            s["Q"] += 0.3

        # Very short file → entropy boost
        if text_len < 200:
            s["E"] += 1.0
        elif text_len < 50:
            s["E"] += 2.0

        return s

    def _normalize(self, raw_scores: dict) -> list[float]:
        """Normalize raw scores to 0-3 scale."""
        values = [raw_scores[v] for v in VAR_NAMES]
        max_val = max(values) if max(values) > 0 else 1.0
        # Scale so the highest raw score maps to 3.0
        return [round(min((v / max_val) * 3.0, 3.0), 2) for v in values]

    def _compute_magnitude(self, text: str, path: Path) -> int:
        """Magnitude = completeness proxy based on size."""
        if text is None:
            size = path.stat().st_size if path.exists() else 0
        else:
            size = len(text)

        if size < 500:
            return 1  # fragment
        elif size < 10000:
            return 2  # substantial
        else:
            return 3  # comprehensive

    def _compute_state(self, name_lower: str, text: str) -> str:
        """Determine document state from name and content signals."""
        if not text or len(text.strip()) == 0:
            return "X"  # empty/fragment

        name = name_lower
        if any(w in name for w in ["draft", "wip", "scratch", "temp"]):
            return "D"
        if any(w in name for w in ["final", "canonical", "complete", "published", "v1"]):
            return "F"

        # Check content for state signals
        if text:
            tl = text.lower()
            if "todo" in tl or "fixme" in tl or "work in progress" in tl:
                return "D"
            if "abstract" in tl and "conclusion" in tl:
                return "F"  # has both = probably complete

        return "W"  # default = working

    def _compute_dominant(self, vector: list[float]) -> list[str]:
        """Pick the top 2-3 variables scoring >= 2.0."""
        scored = [(VAR_NAMES[i], vector[i]) for i in range(10)]
        scored.sort(key=lambda x: -x[1])

        dominant = []
        for name, val in scored:
            if val >= 2.0 and len(dominant) < 4:
                dominant.append(name)
            elif val >= 1.5 and len(dominant) < 2:
                # If nothing hits 2.0, relax threshold for top 2
                dominant.append(name)

        if not dominant:
            # Nothing dominant — entropy wins
            dominant = ["E"]

        return dominant

    def _encode_hash(self, vector: list[float], magnitude: int,
                     state: str) -> str:
        """Encode the vector into a decodable coordinate hash.

        Format: [dominant vars][magnitude][state]
        Examples: GKC3F, MK2W, E1X, RQFC3F
        """
        dominant = self._compute_dominant(vector)
        return "".join(dominant) + str(magnitude) + state

    @staticmethod
    def decode_hash(coord_hash: str) -> dict:
        """Decode a coordinate hash back into its components.

        'GKC3F' -> {vars: ['G','K','C'], magnitude: 3, state: 'F'}
        """
        if not coord_hash:
            return {"vars": [], "magnitude": 0, "state": "X"}

        # State is last char
        state = coord_hash[-1] if coord_hash[-1] in "DWFX" else "W"
        # Magnitude is second-to-last digit
        rest = coord_hash[:-1] if state != "W" or coord_hash[-1] in "DWFX" else coord_hash
        magnitude = 1
        if rest and rest[-1].isdigit():
            magnitude = int(rest[-1])
            rest = rest[:-1]

        # Everything else is variable names
        variables = [c for c in rest if c in VAR_NAMES]

        return {"vars": variables, "magnitude": magnitude, "state": state}


# ============================================================
# NAME PROJECTION — same vector, different surface
# ============================================================

def project_name(address: SemanticAddress, path: Path,
                 mode: str = "personal") -> str:
    """Project the semantic address into a human-readable filename.

    Modes:
      personal    — SLUG_DATE_ID.ext
      research    — PROJECT_SERIES_TOPIC_DATE_STATUS.ext
      professional— DEPT_DOCTYPE_SUBJECT_DATE_VERSION.ext
      system      — FUNCTION_TARGET.ext
    """
    ext = path.suffix
    stem = path.stem
    hash_str = address.coord_hash
    seq = "000000"  # placeholder — filled by DB on insert

    if mode == "system" and "M" in address.dominant:
        # System mode for mechanism-dominant files
        slug = _clean_slug(stem, max_len=30)
        return f"{slug}{ext}"

    elif mode == "research":
        slug = _clean_slug(stem, max_len=40)
        state_label = {"D": "draft", "W": "working", "F": "final", "X": "fragment"}
        return f"{hash_str}_{slug}_{state_label.get(address.state, 'working')}{ext}"

    elif mode == "professional":
        # Map dominant vars to department names
        dept_map = {"G": "GOV", "M": "OPS", "E": "QA", "S": "HR",
                    "T": "PMO", "K": "RES", "R": "BIZ", "Q": "CX",
                    "F": "RISK", "C": "ARCH"}
        dept = dept_map.get(address.dominant[0], "GEN") if address.dominant else "GEN"
        slug = _clean_slug(stem, max_len=30)
        return f"{dept}_{slug}_{seq}{ext}"

    else:  # personal (default)
        slug = _clean_slug(stem, max_len=40)
        return f"{hash_str}_{slug}_{seq}{ext}"


def _clean_slug(name: str, max_len: int = 30) -> str:
    """Clean a filename into a consistent slug."""
    # Remove existing hash patterns and sequence IDs
    name = re.sub(r'_\d{6}$', '', name)
    name = re.sub(r'^[A-Z]{1,4}\d[DWFX]_', '', name)
    # Normalize
    slug = re.sub(r'[^a-zA-Z0-9\s\-_]', '', name)
    slug = re.sub(r'[\s\-]+', '-', slug).strip('-')
    slug = slug[:max_len].rstrip('-')
    return slug.lower() if slug else "untitled"
