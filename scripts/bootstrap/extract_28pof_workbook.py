#!/usr/bin/env python3
"""Extract workbook registry sheets into scanner-readable JSON.

This intentionally uses only the Python standard library so it can run before
spreadsheet dependencies are installed.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def _load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for si in root.findall("a:si", NS):
        values.append("".join(t.text or "" for t in si.findall(".//a:t", NS)))
    return values


def _cell_text(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find("a:v", NS)
    if cell_type == "s" and value is not None and (value.text or "").isdigit():
        return shared[int(value.text or "0")]
    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(".//a:t", NS))
    if value is not None:
        return value.text or ""
    return "".join(t.text or "" for t in cell.findall(".//a:t", NS))


def _sheet_paths(zf: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    result: dict[str, str] = {}
    for sheet in workbook.findall("a:sheets/a:sheet", NS):
        rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        target = rid_to_target[rid]
        result[sheet.attrib["name"]] = "xl/" + target if not target.startswith("/") else target[1:]
    return result


def _rows(zf: zipfile.ZipFile, path: str, shared: list[str]) -> list[list[str]]:
    root = ET.fromstring(zf.read(path))
    out: list[list[str]] = []
    for row in root.findall("a:sheetData/a:row", NS):
        values = [_cell_text(cell, shared).strip() for cell in row.findall("a:c", NS)]
        if any(values):
            out.append(values)
    return out


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "value"


def _table_records(rows: list[list[str]]) -> list[dict[str, str]]:
    if not rows:
        return []
    header_idx = 0
    for idx, row in enumerate(rows):
        lowered = [cell.lower() for cell in row]
        if any(cell in {"id", "function_name", "severity", "profile", "gate", "order"} for cell in lowered):
            header_idx = idx
            break
    headers = [_slug(cell) for cell in rows[header_idx]]
    records: list[dict[str, str]] = []
    for row in rows[header_idx + 1 :]:
        if not any(row):
            continue
        if len(row) == 1 and row[0].isupper():
            continue
        record = {}
        for idx, header in enumerate(headers):
            record[header] = row[idx] if idx < len(row) else ""
        if any(record.values()):
            records.append(record)
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workbook",
        default=r"\\192.168.2.50\h_hp\Desktop\28pof_hub_architecture_with_templates.xlsx",
    )
    parser.add_argument("--out", default=r"D:\GitHub\TOP AI FIS\config\rules")
    args = parser.parse_args()

    workbook = Path(args.workbook)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(workbook) as zf:
        shared = _load_shared_strings(zf)
        paths = _sheet_paths(zf)
        wanted = {
            "Symptom Registry": "symptom_registry.28pof.v1.json",
            "Detection Functions": "detection_functions.28pof.v1.json",
            "Severity Scale": "severity_scale.28pof.v1.json",
            "Folder Profiles": "folder_profiles.28pof.v1.json",
            "Review Gates": "review_gates.28pof.v1.json",
            "Build Order": "build_order.28pof.v1.json",
        }
        summary = {
            "schema": "top-ai-fis.28pof_workbook_import.v1",
            "source_workbook": str(workbook),
            "sheets": {},
        }
        for sheet_name, filename in wanted.items():
            rows = _rows(zf, paths[sheet_name], shared)
            records = _table_records(rows)
            payload = {
                "schema": f"top-ai-fis.{_slug(sheet_name)}.28pof.v1",
                "source_workbook": str(workbook),
                "source_sheet": sheet_name,
                "record_count": len(records),
                "records": records,
            }
            target = out_dir / filename
            target.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
            summary["sheets"][sheet_name] = {
                "output": str(target),
                "records": len(records),
            }

    summary_path = out_dir / "28pof_workbook_import_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
