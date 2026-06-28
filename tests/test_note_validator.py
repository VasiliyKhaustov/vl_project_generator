from __future__ import annotations

import unittest
from pathlib import Path

from backend.core.calculator import calculate_materials
from backend.core.dxf_reader import analyze_dxf
from backend.core.note_validator import (
    _read_armature_table_quantities,
    _read_route_plan_sheet,
    load_note_document,
    validate_filled_note,
)
from backend.core.replacement_builder import build_replacement_map
from backend.core.tu_parser import parse_tu


PROJECT_ROOT = Path(__file__).resolve().parents[1]
USER_NOTE = Path("/Users/vasilijhaustov/Downloads/RESULT232323232323.dwg")


class NoteValidatorIntegrationTests(unittest.TestCase):
    def test_detects_wrong_route_plan_sheet_in_user_note(self) -> None:
        if not USER_NOTE.exists():
            self.skipTest("user note file is missing")
        work = PROJECT_ROOT / "output" / "result"
        tu_path = work / "uploads" / "validate_tu.pdf"
        plan_path = work / "uploads" / "validate_plan.dxf"
        if not tu_path.exists() or not plan_path.exists():
            self.skipTest("validation uploads are missing")

        tu_data, _ = parse_tu(tu_path)
        plan_data, _ = analyze_dxf(plan_path)
        replacement_map = build_replacement_map(
            "ПСД/48/2026/179",
            tu_data,
            calculate_materials(tu_data, plan_data),
        )
        issues = validate_filled_note(
            USER_NOTE,
            work,
            replacement_map,
            tu_data,
            "ПСД/48/2026/179",
        )
        codes = {issue.code for issue in issues}
        self.assertIn("NOTE_VALUE_WRONG_ROUTE_PLAN_SHEET", codes)

        document = load_note_document(USER_NOTE, work)
        self.assertEqual(_read_route_plan_sheet(document), "5")
        self.assertEqual(replacement_map["{{ROUTE_PLAN_SHEET}}"], "5-6")
        armature = _read_armature_table_quantities(document)
        self.assertEqual(armature.get("F207"), "30")


if __name__ == "__main__":
    unittest.main()
