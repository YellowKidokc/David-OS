#!/usr/bin/env python3
"""Read-only Theophysics math inventory extractor.

This scans a chosen canonical vault before any historical comparison. It
extracts math-looking blocks, equations, and formal-keyword paragraphs, then
writes source-backed reports for symbol and equation cleanup.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_OUTPUT = Path(r"C:\Theophysics_Tagger\05_MATH_AUDIT")
DEFAULT_EXTENSIONS = ".md,.txt,.tex"
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".obsidian",
    ".stversions",
    "__pycache__",
    "node_modules",
    "00_MEDIA",
    "99_TAG_NOTES",
    "ZZZ_DUPLICATES",
    "_archive",
    "_ARCHIVE",
}
MATH_KEYWORDS = [
    "χ =",
    "dχ/dt",
    "L =",
    "G·M·E·S·T·K·R·Q·F·C",
    "Noether",
    "Lagrangian",
    "Hamiltonian",
    "entropy",
    "operator",
    "tensor",
    "field",
    "phase transition",
    "boundary theorem",
]
SYMBOL_RE = re.compile(
    r"(?:[A-Za-zΑ-Ωα-ωχτ][A-Za-z0-9_Α-Ωα-ωχτ]*|[A-Za-zΑ-Ωα-ωχτ]_[A-Za-z0-9]+|[A-Za-zΑ-Ωα-ωχτ]\^\{?[A-Za-z0-9+-]+\}?)"
)
DEFINITION_RE = re.compile(
    r"(?P<symbol>[A-Za-zΑ-Ωα-ωχτ][A-Za-z0-9_Α-Ωα-ωχτ]*|[χτ])\s*(?:=|:=|≡|means|is defined as|represents|denotes)\s*(?P<definition>.{1,240})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MathItem:
    item_id: str
    kind: str
    path: Path
    paragraph: int
    heading: str
    text: str
    normalized: str


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def split_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]


def iter_files(sources: list[Path], extensions: set[str], limit: int | None, max_file_mb: float):
    seen: set[str] = set()
    count = 0
    for source in sources:
        candidates = [source] if source.is_file() else source.rglob("*")
        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            if any(part in DEFAULT_EXCLUDE_DIRS for part in path.parts):
                continue
            try:
                if path.stat().st_size > max_file_mb * 1024 * 1024:
                    continue
            except OSError:
                continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            yield path
            count += 1
            if limit and count >= limit:
                return


def normalize_math(text: str) -> str:
    value = text.strip()
    value = re.sub(r"```(?:math|latex)?|```", "", value, flags=re.IGNORECASE).strip()
    value = re.sub(r"\s+", " ", value)
    value = value.replace("\\left", "").replace("\\right", "")
    return value


def item_hash(path: Path, paragraph: int, kind: str, text: str) -> str:
    raw = f"{path}|{paragraph}|{kind}|{text}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()[:12]


def extract_items(path: Path, text: str) -> list[MathItem]:
    items: list[MathItem] = []
    paragraphs = split_paragraphs(text)
    block_pattern = re.compile(r"```(?:math|latex)\s*(.*?)```", re.IGNORECASE | re.DOTALL)
    inline_pattern = re.compile(r"(?<!\$)\$\$(.+?)\$\$(?!\$)|(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL)
    headings: list[str] = []

    for index, paragraph in enumerate(paragraphs, start=1):
        first = paragraph.splitlines()[0].strip()
        if first.startswith("#"):
            headings.append(first.lstrip("#").strip())
        heading = " > ".join(headings[-3:])
        for match in block_pattern.finditer(paragraph):
            raw = match.group(1).strip()
            if raw:
                normalized = normalize_math(raw)
                items.append(MathItem(item_hash(path, index, "math_block", normalized), "math_block", path, index, heading, raw, normalized))

        for match in inline_pattern.finditer(paragraph):
            raw = (match.group(1) or match.group(2) or "").strip()
            if raw:
                normalized = normalize_math(raw)
                items.append(MathItem(item_hash(path, index, "dollar_math", normalized), "dollar_math", path, index, heading, raw, normalized))

        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        for line in lines:
            if looks_like_equation(line):
                normalized = normalize_math(line)
                items.append(MathItem(item_hash(path, index, "equation_line", normalized), "equation_line", path, index, heading, line, normalized))

        lowered = paragraph.lower()
        if any(keyword.lower() in lowered for keyword in MATH_KEYWORDS):
            normalized = normalize_math(paragraph[:1200])
            items.append(MathItem(item_hash(path, index, "keyword_paragraph", normalized), "keyword_paragraph", path, index, heading, paragraph, normalized))

    return dedupe_items(items)


def looks_like_equation(line: str) -> bool:
    if len(line) > 500:
        return False
    math_tokens = ("=", "≡", "∂", "Δ", "∇", "→", "≤", "≥", "\\frac", "\\sum", "\\int", "χ", "τ", "·")
    if not any(token in line for token in math_tokens):
        return False
    return bool(re.search(r"[A-Za-zΑ-Ωα-ωχτ]\s*(?:=|≡|:=|→|≤|≥)", line) or re.search(r"(?:\\frac|\\sum|\\int|dχ/dt|G·M·E·S·T·K·R·Q·F·C)", line))


def dedupe_items(items: list[MathItem]) -> list[MathItem]:
    seen: set[tuple[str, int, str, str]] = set()
    result: list[MathItem] = []
    for item in items:
        key = (str(item.path).lower(), item.paragraph, item.kind, item.normalized)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def extract_symbols(text: str) -> set[str]:
    stop = {
        "and", "the", "for", "from", "with", "where", "operator", "field", "phase", "transition",
        "entropy", "boundary", "theorem", "noether", "lagrangian", "hamiltonian",
    }
    symbols = set()
    for match in SYMBOL_RE.finditer(text):
        symbol = match.group(0).strip()
        if len(symbol) > 28 or symbol.lower() in stop:
            continue
        if len(symbol) == 1 or "_" in symbol or "^" in symbol or any(ch in symbol for ch in "χτΔ∂∇"):
            symbols.add(symbol)
    return symbols


def extract_definitions(item: MathItem) -> list[dict]:
    rows: list[dict] = []
    for match in DEFINITION_RE.finditer(item.text):
        rows.append(
            {
                "symbol": match.group("symbol").strip(),
                "definition": match.group("definition").strip().replace("\n", " "),
                "path": str(item.path),
                "paragraph": item.paragraph,
                "heading": item.heading,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_reports(output_dir: Path, stamp: str, items: list[MathItem], files_scanned: int, sources: list[Path]) -> None:
    run_dir = output_dir / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    inventory_rows = [
        {
            "item_id": item.item_id,
            "kind": item.kind,
            "path": str(item.path),
            "paragraph": item.paragraph,
            "heading": item.heading,
            "normalized": item.normalized,
            "symbols": ";".join(sorted(extract_symbols(item.text))),
        }
        for item in items
    ]
    write_csv(run_dir / "math_inventory.csv", inventory_rows)

    definitions: list[dict] = []
    symbol_sources: dict[str, list[MathItem]] = defaultdict(list)
    for item in items:
        for symbol in extract_symbols(item.text):
            symbol_sources[symbol].append(item)
        definitions.extend(extract_definitions(item))
    write_csv(run_dir / "symbol_definitions.csv", definitions)

    normalized_counts = Counter(item.normalized for item in items if item.kind != "keyword_paragraph")
    symbol_def_counts = Counter((row["symbol"], row["definition"].lower()) for row in definitions)

    conflicts: list[dict] = []
    definitions_by_symbol: dict[str, set[str]] = defaultdict(set)
    for row in definitions:
        definitions_by_symbol[row["symbol"]].add(row["definition"].strip())
    for symbol, defs in sorted(definitions_by_symbol.items()):
        if len(defs) > 1:
            conflicts.append({"type": "multiple_definitions", "symbol": symbol, "count": len(defs), "details": " || ".join(sorted(defs)[:8])})
    for equation, count in normalized_counts.items():
        if count > 1:
            conflicts.append({"type": "repeated_equation", "symbol": "", "count": count, "details": equation})
    write_csv(run_dir / "math_conflicts.csv", conflicts)

    write_math_inventory_md(run_dir / "math_inventory.md", items, files_scanned, sources)
    write_symbol_dictionary_md(run_dir / "symbol_dictionary.md", symbol_sources, definitions_by_symbol)
    write_math_conflicts_md(run_dir / "math_conflicts.md", conflicts)
    write_canonical_candidate_md(run_dir / "canonical_math_candidate.md", items, normalized_counts)

    summary = {
        "sources": [str(source) for source in sources],
        "files_scanned": files_scanned,
        "math_items": len(items),
        "symbols": len(symbol_sources),
        "definitions": len(definitions),
        "conflicts_or_repeats": len(conflicts),
        "output_dir": str(run_dir),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8-sig")
    print(json.dumps(summary, indent=2))


def write_math_inventory_md(path: Path, items: list[MathItem], files_scanned: int, sources: list[Path]) -> None:
    lines = [
        "# Math Inventory",
        "",
        f"- Sources: {', '.join(str(source) for source in sources)}",
        f"- Files scanned: {files_scanned}",
        f"- Math-looking items found: {len(items)}",
        "",
    ]
    for item in items:
        lines.extend(
            [
                f"## {item.item_id} - {item.kind}",
                "",
                f"- Source: `{item.path}`",
                f"- Paragraph: {item.paragraph}",
                f"- Heading: {item.heading or '(none)'}",
                f"- Symbols: {', '.join(sorted(extract_symbols(item.text))) or '(none detected)'}",
                "",
                "```text",
                item.text.strip()[:3000],
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def write_symbol_dictionary_md(path: Path, symbol_sources: dict[str, list[MathItem]], definitions_by_symbol: dict[str, set[str]]) -> None:
    lines = ["# Symbol Dictionary", ""]
    for symbol in sorted(symbol_sources):
        items = symbol_sources[symbol]
        definitions = sorted(definitions_by_symbol.get(symbol, set()))
        lines.extend([f"## `{symbol}`", "", f"- Occurrences: {len(items)}"])
        if definitions:
            lines.append("- Definitions found:")
            for definition in definitions[:10]:
                lines.append(f"  - {definition}")
        else:
            lines.append("- Definitions found: none")
        lines.append("- Example sources:")
        for item in items[:8]:
            lines.append(f"  - `{item.path}` paragraph {item.paragraph}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def write_math_conflicts_md(path: Path, conflicts: list[dict]) -> None:
    lines = ["# Math Conflicts", "", "This is a first-pass consistency report, not a truth judgment.", ""]
    if not conflicts:
        lines.append("No repeated equations or multiple symbol definitions were detected in this run.")
    for row in conflicts:
        lines.extend(
            [
                f"## {row['type']}",
                "",
                f"- Symbol: `{row.get('symbol') or '(equation)'}`",
                f"- Count: {row['count']}",
                "",
                "```text",
                row["details"],
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def write_canonical_candidate_md(path: Path, items: list[MathItem], normalized_counts: Counter[str]) -> None:
    priority_terms = re.compile(r"master equation|lagrangian|noether|hamiltonian|symplectic|boundary theorem|χ|dχ/dt|G·M·E·S·T·K·R·Q·F·C", re.IGNORECASE)
    candidates = [item for item in items if priority_terms.search(item.text)]
    candidates.sort(key=lambda item: (normalized_counts[item.normalized], len(item.text)), reverse=True)

    lines = [
        "# Canonical Math Candidate",
        "",
        "This is a candidate spine based on repeated/formal-looking items in the current scan. Human review still decides what is canonical.",
        "",
        "## Highest-Priority Items",
        "",
    ]
    for item in candidates[:50]:
        lines.extend(
            [
                f"### {item.item_id} - {item.kind}",
                "",
                f"- Source: `{item.path}`",
                f"- Paragraph: {item.paragraph}",
                f"- Repeat count: {normalized_counts[item.normalized]}",
                "",
                "```text",
                item.text.strip()[:2200],
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Theophysics math inventory reports.")
    parser.add_argument("--source", action="append", required=True, help="Canonical file or folder to scan. Repeat for multiple roots.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--extensions", default=DEFAULT_EXTENSIONS)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-file-mb", type=float, default=5.0)
    parser.add_argument("--progress-every", type=int, default=250)
    args = parser.parse_args()

    sources = [Path(item) for item in args.source]
    extensions = {item.strip().lower() for item in args.extensions.split(",") if item.strip()}
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    items: list[MathItem] = []
    files_scanned = 0
    for path in iter_files(sources, extensions, args.limit, args.max_file_mb):
        files_scanned += 1
        if args.progress_every and files_scanned % args.progress_every == 0:
            print(f"scanned {files_scanned} files; found {len(items)} math-looking items", flush=True)
        try:
            text = read_text(path)
        except OSError:
            continue
        items.extend(extract_items(path, text))

    write_reports(Path(args.output), stamp, items, files_scanned, sources)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
