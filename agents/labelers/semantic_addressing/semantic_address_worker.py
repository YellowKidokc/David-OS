#!/usr/bin/env python3
"""Run the legacy FIS semantic address scorer as a TOP AI FIS worker.

This is intentionally a thin wrapper around the already-built deterministic
10D scorer and hash codec. It does not start the old watcher and does not need
the old Postgres app.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hash_codec import encode_hash, human_score_string
from meta_mapper import MetaMapper
from semantic_scorer import SemanticScorer


TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".py", ".js", ".ts", ".jsx", ".tsx",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".html", ".htm",
    ".css", ".sql", ".ps1", ".bat", ".cmd", ".ahk", ".csv",
}


def read_text_sample(path: Path, max_chars: int = 120_000) -> str:
    """Best-effort local text read.

    The hub reader/parsers should eventually provide richer text extraction.
    This worker stays dependency-free so it can run early in the install.
    """
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return path.name
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError:
        return path.name


def score_path(path: Path, text: str | None = None) -> dict:
    sample = text if text is not None else read_text_sample(path)
    scorer = SemanticScorer()
    address = scorer.score_file(str(path), text=sample, keywords=[])
    encoded = encode_hash(
        address.vector,
        magnitude=address.magnitude,
        state=address.state,
        dominant=address.dominant,
    )
    meta = MetaMapper().classify(address, extension=path.suffix.lower())
    return {
        "schema": "top-ai-fis.semantic_address_result.v1",
        "source": "legacy-fis-semantic-scorer",
        "path": str(path),
        "filename": path.name,
        "extension": path.suffix.lower(),
        "variables": ["G", "M", "E", "S", "T", "K", "R", "Q", "F", "C"],
        "vector": address.vector,
        "vector_dict": address.vector_dict,
        "dominant": address.dominant,
        "magnitude": address.magnitude,
        "state": address.state,
        "legacy_coord_hash": address.coord_hash,
        "coord_hash_raw": encoded["coord_hash_raw"],
        "coord_hash_full": encoded["coord_hash_full"],
        "human_score": human_score_string(address.vector),
        "meta": {
            "context": meta.context,
            "domain": meta.domain,
            "function": meta.function,
            "state": meta.state,
            "path": meta.path,
            "confidence": {
                "context": meta.context_confidence,
                "domain": meta.domain_confidence,
                "function": meta.function_confidence,
                "state": meta.state_confidence,
            },
            "rules": {
                "context": meta.context_rule,
                "domain": meta.domain_rule,
                "function": meta.function_rule,
                "state": meta.state_rule,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, help="File path to score.")
    parser.add_argument("--text", help="Optional pre-extracted text.")
    parser.add_argument("--out", help="Optional JSON output path.")
    args = parser.parse_args()

    result = score_path(Path(args.path), text=args.text)
    payload = json.dumps(result, indent=2, ensure_ascii=True) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
