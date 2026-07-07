"""Naming Learner — River-based online learning for file naming preferences.

Architecture (from DOWNSTREAM_INTEGRATION_HANDOFF.md):

  INPUT: approve/reject events from David
    |
    v
  RIVER (Model 18) — real-time streaming learner
    Learns: which slugs, domains, subjects David accepts vs rejects
    Learns: naming patterns per file type, extension, path context
    Speed: microsecond per event, always online
    |
    v
  PPK (Model 17) — portable preference kernel
    Stores: compressed naming weights as tiny JSON
    Purpose: copy to any machine, any AI worker knows David's prefs
    Updated: periodically from River's learned state
    |
    v
  IMPLICIT (Model 13) — collaborative filter (FUTURE)
    Learns: co-occurrence patterns ("David always renames X then Y")
    Needs: PPK training data first — don't wire until PPK has real weights

Separate specialist:
  MARKOVIFY (Model 19) — text prediction for slug generation
    Learns: from approved slugs + content text
    Output: "David would name this..." predictions
    Independent of the River->PPK chain

Usage:
    from fis.naming_learner import NamingLearner
    learner = NamingLearner()

    # On classify — get naming prediction
    prediction = learner.predict_name(features)

    # On approve — learn from acceptance
    learner.learn_approve(features, approved_name)

    # On reject — learn from rejection
    learner.learn_reject(features, rejected_name)

    # Periodic — export to PPK
    learner.export_to_ppk()
"""

import json
import os
import pickle
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from river import compose, linear_model, preprocessing, feature_extraction

from fis.log import get_logger

log = get_logger("naming_learner")

# Model state locations — canonical in the NAS model zoo
# Models 13-19 are behavioral models that build weights from David's usage
MODEL_BASE = Path(r"X:\Models")
RIVER_DIR = MODEL_BASE / "P06_river"                    # River state
MARKOV_DIR = MODEL_BASE / "P07_markovify"               # Slug corpus
PPK_DIR = MODEL_BASE / "P05_ppk"                        # PPK export
IMPLICIT_DIR = MODEL_BASE / "P01_implicit"              # Future

# Fallback local paths if NAS is unreachable
LOCAL_FALLBACK = Path("D:/GitHub/file-intelligence-system/models/naming")

SLUG_CORPUS_PATH = MARKOV_DIR / "approved_slugs.jsonl"


class NamingLearner:
    """Online learner for file naming preferences.

    River model learns from every approve/reject.
    Markovify learns from approved slug corpus.
    PPK gets periodic exports of the compressed preference state.
    """

    def __init__(self):
        # Ensure directories exist (NAS primary, local fallback)
        for d in [RIVER_DIR, MARKOV_DIR, PPK_DIR, LOCAL_FALLBACK]:
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

        # Determine where to save state — NAS if reachable, local if not
        if RIVER_DIR.exists():
            self._state_dir = RIVER_DIR
            self._ppk_dir = PPK_DIR
            self._corpus_path = SLUG_CORPUS_PATH
        else:
            log.warning("NAS model folder unreachable, using local fallback")
            self._state_dir = LOCAL_FALLBACK
            self._ppk_dir = LOCAL_FALLBACK
            self._corpus_path = LOCAL_FALLBACK / "approved_slugs.jsonl"

        # River model for domain/subject acceptance prediction
        self.domain_model = compose.Pipeline(
            preprocessing.StandardScaler(),
            linear_model.LogisticRegression(l2=0.01),
        )

        # River model for slug quality prediction
        self.slug_model = compose.Pipeline(
            preprocessing.StandardScaler(),
            linear_model.LogisticRegression(l2=0.01),
        )

        self.event_count = 0
        self.approve_count = 0
        self.reject_count = 0

        # Slug corpus for Markovify training
        self._slug_corpus = []

        # Load saved state if exists
        self._load_state()

    def _load_state(self):
        """Load River model state from disk."""
        state_path = self._state_dir / "river_naming_state.pkl"
        if state_path.exists():
            try:
                with open(state_path, "rb") as f:
                    state = pickle.load(f)
                self.domain_model = state.get("domain_model", self.domain_model)
                self.slug_model = state.get("slug_model", self.slug_model)
                self.event_count = state.get("event_count", 0)
                self.approve_count = state.get("approve_count", 0)
                self.reject_count = state.get("reject_count", 0)
                log.info("Loaded naming learner: %d events (%d approve, %d reject)",
                         self.event_count, self.approve_count, self.reject_count)
            except Exception as e:
                log.warning("Could not load naming learner state: %s", e)

    def _save_state(self):
        """Save River model state to disk."""
        state_path = self._state_dir / "river_naming_state.pkl"
        try:
            with open(state_path, "wb") as f:
                pickle.dump({
                    "domain_model": self.domain_model,
                    "slug_model": self.slug_model,
                    "event_count": self.event_count,
                    "approve_count": self.approve_count,
                    "reject_count": self.reject_count,
                    "saved_at": datetime.now(timezone.utc).isoformat(),
                }, f)
        except Exception as e:
            log.warning("Could not save naming learner state: %s", e)

    def extract_features(
        self,
        *,
        domain: str = "",
        subjects: list[str] | None = None,
        slug: str = "",
        extension: str = "",
        confidence: float = 0.0,
        vector: list[float] | None = None,
        dominant: list[str] | None = None,
        original_name: str = "",
        file_path: str = "",
        keywords: list[str] | None = None,
    ) -> dict:
        """Extract features for the naming models.

        Returns a flat dict suitable for River's online learning.
        """
        subjects = subjects or []
        vector = vector or [0.0] * 10
        dominant = dominant or []
        keywords = keywords or []
        var_names = ["G", "M", "E", "S", "T", "K", "R", "Q", "F", "C"]

        features = {}

        # Domain as one-hot
        for d in ["TP", "SY", "DT", "EV", "MD", "DC", "OB", "CB", "--"]:
            features[f"domain_{d}"] = 1.0 if domain == d else 0.0

        # Subject count and primary subject
        features["n_subjects"] = len(subjects)
        for s in ["MQ", "LG", "JS", "IS", "SV", "RS", "GR", "CS", "EN", "AX",
                   "WV", "SC", "CF", "GT", "MR", "ST", "JR", "GN"]:
            features[f"subj_{s}"] = 1.0 if s in subjects else 0.0

        # Confidence
        features["confidence"] = confidence / 100.0

        # Vector values
        for i, v in enumerate(var_names):
            features[f"vec_{v}"] = vector[i]

        # Dominant vars
        for v in var_names:
            features[f"dom_{v}"] = 1.0 if v in dominant else 0.0

        # Extension
        ext = extension.lower()
        for e in [".md", ".py", ".pdf", ".html", ".xlsx", ".txt", ".json",
                  ".mp3", ".mp4", ".png", ".jpg", ".zip", ".docx"]:
            features[f"ext_{e}"] = 1.0 if ext == e else 0.0

        # Slug properties
        features["slug_len"] = len(slug)
        features["slug_words"] = slug.count("-") + 1 if slug else 0

        # Original filename properties
        stem = Path(original_name).stem if original_name else ""
        features["orig_len"] = len(stem)
        features["orig_words"] = len(re.findall(r'[a-zA-Z]+', stem))
        features["orig_has_numbers"] = 1.0 if re.search(r'\d', stem) else 0.0
        features["orig_has_spaces"] = 1.0 if " " in original_name else 0.0
        features["orig_is_uppercase"] = 1.0 if stem.isupper() else 0.0

        # Path context
        path_lower = file_path.lower()
        features["path_github"] = 1.0 if "github" in path_lower else 0.0
        features["path_theophysics"] = 1.0 if "theophysics" in path_lower else 0.0
        features["path_desktop"] = 1.0 if "desktop" in path_lower else 0.0
        features["path_downloads"] = 1.0 if "downloads" in path_lower else 0.0

        # Time
        features["hour"] = datetime.now().hour
        features["day_of_week"] = datetime.now().weekday()

        # Top keywords as binary features (up to 10)
        for i, kw in enumerate(keywords[:10]):
            features[f"kw_{i}_{kw.lower().replace(' ', '_')[:20]}"] = 1.0

        return features

    def learn_approve(self, features: dict, approved_name: str,
                      original_name: str = ""):
        """Learn from an approved rename.

        River updates immediately. Slug corpus gets appended for Markovify.
        """
        # River learn — domain model (was the domain right?)
        self.domain_model.learn_one(features, 1)

        # River learn — slug model (was the slug good?)
        slug_features = {k: v for k, v in features.items()
                         if k.startswith(("slug_", "orig_", "kw_", "vec_", "dom_"))}
        self.slug_model.learn_one(slug_features, 1)

        self.event_count += 1
        self.approve_count += 1

        # Append to slug corpus for Markovify training
        self._append_slug_corpus(approved_name, features, reward=1.0)

        # Save state every 10 events
        if self.event_count % 10 == 0:
            self._save_state()
            log.info("Naming learner: %d events, %d approved, %d rejected",
                     self.event_count, self.approve_count, self.reject_count)

        # Export to PPK every 50 events
        if self.event_count % 50 == 0:
            self.export_to_ppk()

    def learn_reject(self, features: dict, rejected_name: str,
                     correction: str = ""):
        """Learn from a rejected rename.

        River gets negative signal. If David provided a correction,
        that's even more valuable — we learn what he WANTED.
        """
        # River learn — negative signal
        self.domain_model.learn_one(features, 0)

        slug_features = {k: v for k, v in features.items()
                         if k.startswith(("slug_", "orig_", "kw_", "vec_", "dom_"))}
        self.slug_model.learn_one(slug_features, 0)

        self.event_count += 1
        self.reject_count += 1

        # If David provided a correction, learn from THAT as positive
        if correction:
            self._append_slug_corpus(correction, features, reward=1.0)
            # Re-extract features with the corrected name and learn positive
            corrected_features = dict(features)
            corrected_features["slug_len"] = len(correction)
            corrected_features["slug_words"] = correction.count("-") + 1
            self.domain_model.learn_one(corrected_features, 1)
            self.slug_model.learn_one(
                {k: v for k, v in corrected_features.items()
                 if k.startswith(("slug_", "orig_", "kw_", "vec_", "dom_"))},
                1
            )

        if self.event_count % 10 == 0:
            self._save_state()

    def predict_name_confidence(self, features: dict) -> float:
        """Predict how likely David is to approve a proposed name.

        Returns 0.0-1.0 confidence. Below 0.3 = probably bad name.
        """
        if self.event_count < 5:
            return 0.5  # Not enough data yet

        domain_conf = self.domain_model.predict_proba_one(features).get(True, 0.5)

        slug_features = {k: v for k, v in features.items()
                         if k.startswith(("slug_", "orig_", "kw_", "vec_", "dom_"))}
        slug_conf = self.slug_model.predict_proba_one(slug_features).get(True, 0.5)

        return (domain_conf + slug_conf) / 2.0

    def predict_slug_markov(self, keywords: list[str], domain: str = "") -> Optional[str]:
        """Use Markovify to predict a slug from keywords.

        Only works after enough approved slugs have been collected.
        Falls back to None if not enough training data.
        """
        if not self._corpus_path.exists():
            return None

        try:
            import markovify
        except ImportError:
            log.debug("markovify not installed — skipping slug prediction")
            return None

        # Load approved slug corpus
        slugs = []
        with open(self._corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("reward", 0) > 0:
                        # Use the approved name as training text
                        slug = entry.get("name", "")
                        if slug:
                            # Convert slug back to words for Markov chain
                            words = slug.replace("-", " ").replace("_", " ")
                            slugs.append(words)
                except json.JSONDecodeError:
                    continue

        if len(slugs) < 20:
            return None  # Need at least 20 approved names

        # Build Markov chain from approved slugs
        try:
            corpus = ". ".join(slugs)
            model = markovify.Text(corpus, state_size=1)
            sentence = model.make_short_sentence(40, tries=20)
            if sentence:
                # Convert back to slug format
                slug = re.sub(r'[^a-z0-9\s]', '', sentence.lower())
                slug = re.sub(r'\s+', '-', slug.strip())
                return slug[:30]
        except Exception as e:
            log.debug("Markovify slug generation failed: %s", e)

        return None

    def _append_slug_corpus(self, name: str, features: dict, reward: float):
        """Append to the slug corpus JSONL for Markovify training."""
        entry = {
            "name": name,
            "domain": next((k.split("_")[1] for k, v in features.items()
                          if k.startswith("domain_") and v == 1.0), ""),
            "reward": reward,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(self._corpus_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            log.warning("Could not append to slug corpus: %s", e)

    def export_to_ppk(self) -> dict:
        """Export River's learned state to PPK format.

        PPK is a portable JSON file that captures:
        - Domain preference weights
        - Slug pattern preferences
        - Feature importance rankings
        - Confidence calibration

        Any AI worker or machine can load this JSON and know
        David's naming preferences without needing River's full state.
        """
        ppk_path = self._ppk_dir / "naming_ppk.json"

        # Extract what River has learned
        ppk = {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "event_count": self.event_count,
            "approve_count": self.approve_count,
            "reject_count": self.reject_count,
            "approve_rate": (self.approve_count / self.event_count
                           if self.event_count > 0 else 0),
            "domain_weights": {},
            "slug_weights": {},
            "confidence_calibration": {
                "min_events_for_trust": 50,
                "current_trust": min(self.event_count / 50.0, 1.0),
            },
        }

        # Extract learned weights from River models
        try:
            if hasattr(self.domain_model, 'steps'):
                lr = self.domain_model.steps.get('LogisticRegression',
                     self.domain_model[-1] if hasattr(self.domain_model, '__getitem__') else None)
                if lr and hasattr(lr, 'weights'):
                    ppk["domain_weights"] = {k: round(float(v), 4)
                                             for k, v in lr.weights.items()
                                             if abs(v) > 0.01}
        except Exception:
            pass

        try:
            if hasattr(self.slug_model, 'steps'):
                lr = self.slug_model.steps.get('LogisticRegression',
                     self.slug_model[-1] if hasattr(self.slug_model, '__getitem__') else None)
                if lr and hasattr(lr, 'weights'):
                    ppk["slug_weights"] = {k: round(float(v), 4)
                                           for k, v in lr.weights.items()
                                           if abs(v) > 0.01}
        except Exception:
            pass

        ppk_path.write_text(json.dumps(ppk, indent=2), encoding="utf-8")
        log.info("Exported PPK to %s (%d events)", ppk_path, self.event_count)
        return ppk

    def get_summary(self) -> dict:
        """Quick summary for diagnostics."""
        return {
            "event_count": self.event_count,
            "approve_count": self.approve_count,
            "reject_count": self.reject_count,
            "approve_rate": round(self.approve_count / max(self.event_count, 1), 2),
            "trust_level": min(self.event_count / 50.0, 1.0),
            "slug_corpus_size": (sum(1 for _ in open(self._corpus_path))
                                if self._corpus_path.exists() else 0),
        }
