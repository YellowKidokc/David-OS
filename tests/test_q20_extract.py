from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook

from pipeline.q20_extract import write_outputs


def test_q20_extract_preserves_questions_and_misc(tmp_path: Path) -> None:
    workbook = tmp_path / "20q.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Questions"
    ws.append(["id", "question", "category", "answer_type", "choices", "notes"])
    ws.append(["Q01", "Who owns this folder?", "WHO", "text", "", "ask David if unclear"])
    ws.append(["loose", "review this note", "", "", "", "not a question"])
    ws.append([None, "blank first column note", "", "", "", "must not crash read_only EmptyCell handling"])
    ws2 = wb.create_sheet("Notes")
    ws2["A1"] = "Accumulated notes"
    ws2["B2"] = "Keep this verbatim"
    wb.save(workbook)

    outputs = write_outputs(workbook, tmp_path / "out")
    data = json.loads(outputs["bank_json"].read_text(encoding="utf-8"))

    assert data["stats"]["sheets"] == 2
    assert data["stats"]["questions"] == 1
    assert data["questions"][0]["auto_answerable"] is None
    assert data["questions"][0]["scan_source"] is None
    assert data["questions"][0]["id"] == "Q01"
    misc_text = outputs["misc_md"].read_text(encoding="utf-8")
    assert "Keep this verbatim" in misc_text
    assert "review this note" in misc_text
    assert "blank first column note" in misc_text
    assert "Who owns this folder?" in outputs["bank_md"].read_text(encoding="utf-8")
