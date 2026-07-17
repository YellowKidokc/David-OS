#!/usr/bin/env python3
"""Paragraph-first spiritual tagger for David OS.

Phase 1 indexes documents and paragraphs, then optionally copies each source
file into every matching tag folder. It deliberately does not split into
sentence-level artifacts; paragraph slicing is a separate explicit mode after
the folder map has been reviewed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REGISTRY = SCRIPT_DIR / "spiritual_tag_registry.csv"
DEFAULT_OUTPUT = SCRIPT_DIR / "spiritual_index"
DEFAULT_TAGGED = SCRIPT_DIR / "spiritual_tagged"
DEFAULT_SLICES = SCRIPT_DIR / "spiritual_paragraph_slices"


@dataclass(frozen=True)
class TagRule:
    tag: str
    slug: str
    category: str
    parent_path: str
    variable: str
    pattern: re.Pattern[str]


def slugify(value: str) -> str:
    value = re.sub(r"(?<!^)(?=[A-Z])", "-", value).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "item"


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_registry(path: Path) -> list[TagRule]:
    rules: list[TagRule] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("route_enabled", "yes").strip().lower() not in {"yes", "true", "1"}:
                continue
            terms = [row["tag"]]
            terms.extend(alias.strip() for alias in row.get("aliases", "").split(";") if alias.strip())
            escaped = [re.escape(term) for term in terms if term]
            if not escaped:
                continue
            pattern = re.compile(
                r"(?<![A-Za-z0-9_])(?:" + "|".join(escaped) + r")(?![A-Za-z0-9_])",
                re.IGNORECASE,
            )
            rules.append(
                TagRule(
                    tag=row["tag"],
                    slug=row.get("slug") or slugify(row["tag"]),
                    category=row.get("category") or "Uncategorized",
                    parent_path=row.get("parent_path") or row["tag"],
                    variable=row.get("master_equation_variable", ""),
                    pattern=pattern,
                )
            )
    return rules


def iter_files(sources: list[Path], extensions: set[str], limit: int | None):
    seen = set()
    count = 0
    for source in sources:
        if source.is_file():
            candidates = [source]
        elif source.is_dir():
            candidates = source.rglob("*")
        else:
            continue

        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            yield path
            count += 1
            if limit and count >= limit:
                return


def split_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]


def find_hits(text: str, rules: list[TagRule]) -> list[TagRule]:
    return [rule for rule in rules if rule.pattern.search(text)]


def doc_id(path: Path) -> str:
    return hashlib.sha1(str(path).encode("utf-8", errors="ignore")).hexdigest()[:12]


def relative_target(base: Path, source: Path, rule: TagRule) -> Path:
    return base / slugify(rule.category) / rule.slug / source.name


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_paragraph_slice(slice_dir: Path, source: Path, paragraph_index: int, text: str, hits: list[TagRule]) -> None:
    primary = hits[0]
    target_dir = slice_dir / slugify(primary.category) / primary.slug
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{source.stem}__p{paragraph_index:04d}.md"
    tag_line = " ".join(f"#{hit.tag}" for hit in hits)
    target.write_text(
        f"---\nsource: \"{source}\"\nparagraph: {paragraph_index}\ntags: \"{';'.join(hit.tag for hit in hits)}\"\n---\n\n{tag_line}\n\n{text}\n",
        encoding="utf-8-sig",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Document + paragraph spiritual tagger.")
    parser.add_argument("--source", action="append", required=True, help="File or folder to scan. Repeat for many roots.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--tagged", default=str(DEFAULT_TAGGED))
    parser.add_argument("--slices", default=str(DEFAULT_SLICES))
    parser.add_argument("--extensions", default=".md,.txt,.html")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--copy-mode", choices=["none", "primary", "all-tags"], default="none")
    parser.add_argument("--slice-paragraphs", action="store_true", help="Write paragraph artifacts after folder map review.")
    args = parser.parse_args()

    rules = load_registry(Path(args.registry))
    output_dir = Path(args.output)
    tagged_dir = Path(args.tagged)
    slice_dir = Path(args.slices)
    extensions = {item.strip().lower() for item in args.extensions.split(",") if item.strip()}
    sources = [Path(item) for item in args.source]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    document_rows: list[dict] = []
    paragraph_rows: list[dict] = []
    folder_rows: list[dict] = []
    copy_rows: list[dict] = []

    for source in iter_files(sources, extensions, args.limit):
        try:
            text = read_text(source)
        except OSError as error:
            folder_rows.append({"path": str(source), "status": f"read_error: {error}", "primary_tag": "", "target_folder": ""})
            continue

        doc_hits = find_hits(text, rules)
        if not doc_hits:
            continue

        identifier = doc_id(source)
        variables = sorted({hit.variable for hit in doc_hits if hit.variable})
        document_rows.append(
            {
                "doc_id": identifier,
                "path": str(source),
                "primary_tag": doc_hits[0].tag,
                "primary_category": doc_hits[0].category,
                "tags": ";".join(hit.tag for hit in doc_hits),
                "variables": ";".join(variables),
                "hit_count": len(doc_hits),
            }
        )

        for index, paragraph in enumerate(split_paragraphs(text), start=1):
            hits = find_hits(paragraph, doc_hits)
            if not hits:
                continue
            paragraph_rows.append(
                {
                    "doc_id": identifier,
                    "path": str(source),
                    "paragraph": index,
                    "primary_tag": hits[0].tag,
                    "tags": ";".join(hit.tag for hit in hits),
                    "text": paragraph[:2000],
                }
            )
            if args.slice_paragraphs:
                write_paragraph_slice(slice_dir, source, index, paragraph, hits)

        route_hits = doc_hits if args.copy_mode == "all-tags" else doc_hits[:1]
        for hit in route_hits:
            target = relative_target(tagged_dir, source, hit)
            folder_rows.append(
                {
                    "path": str(source),
                    "status": "suggested" if args.copy_mode == "none" else "copied",
                    "primary_tag": hit.tag,
                    "target_folder": str(target.parent),
                }
            )
            if args.copy_mode != "none":
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    target = target.parent / f"{source.stem}__{identifier}{source.suffix}"
                shutil.copy2(source, target)
                copy_rows.append({"source": str(source), "target": str(target), "tag": hit.tag})

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / f"{stamp}_document_tags.csv", document_rows)
    write_csv(output_dir / f"{stamp}_paragraph_tags.csv", paragraph_rows)
    write_csv(output_dir / f"{stamp}_folder_routes.csv", folder_rows)
    write_csv(output_dir / f"{stamp}_copies.csv", copy_rows)

    summary = {
        "sources": [str(source) for source in sources],
        "documents_tagged": len(document_rows),
        "paragraphs_tagged": len(paragraph_rows),
        "folder_routes": len(folder_rows),
        "copies": len(copy_rows),
        "copy_mode": args.copy_mode,
        "paragraph_slices_written": bool(args.slice_paragraphs),
        "output_dir": str(output_dir),
    }
    (output_dir / f"{stamp}_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8-sig")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
