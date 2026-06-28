from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.core.validation import (
    ValidationIssue,
    _issues_from_note_placeholders,
    _issues_from_plan_data,
    validate_project_files,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = PROJECT_ROOT / "examples" / "templates"


class ValidationModuleTests(unittest.TestCase):
    def test_tu_wrong_format_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            tu_path = work_dir / "tu.txt"
            plan_path = PROJECT_ROOT / "examples" / "projects" / "project_01" / "plan.dxf"
            tu_path.write_text("test", encoding="utf-8")
            if not plan_path.exists():
                self.skipTest("example plan is missing")

            result = validate_project_files(
                tu_path=tu_path,
                plan_path=plan_path,
                note_path=None,
                templates_dir=TEMPLATES_DIR,
                work_dir=work_dir,
                project_number="ПСД/48/2026/001",
            )
            codes = {issue["code"] for issue in result["issues"]}
            self.assertIn("TU_FORMAT", codes)
            self.assertFalse(result["ready"])

    def test_plan_without_supports_is_error(self) -> None:
        issues = _issues_from_plan_data(
            {
                "line_length_m": 120.0,
                "supports": {"P23": 0, "A23": 0, "YA23": 0, "K21": 0},
                "grounding_count": 0,
            }
        )
        codes = {issue.code for issue in issues}
        self.assertIn("PLAN_NO_SUPPORTS", codes)
        self.assertIn("PLAN_NO_GROUNDING", codes)

    def test_note_missing_core_placeholders(self) -> None:
        issues = _issues_from_note_placeholders(
            ["{{PROJNUMB}}"],
            {"supports": {"P23": 1, "A23": 0, "YA23": 0, "K21": 0}},
        )
        codes = {issue.code for issue in issues}
        self.assertIn("NOTE_MISSING_CORE_PLACEHOLDERS", codes)

    def test_note_validation_mode_filled_when_no_placeholders(self) -> None:
        from backend.core.validation import _note_validation_mode

        self.assertEqual(_note_validation_mode([]), "filled")
        self.assertEqual(_note_validation_mode(["{{PROJNUMB}}"]), "filled")
        self.assertEqual(_note_validation_mode(["{{PROJNUMB}}", "{{APPLICANT}}", "{{ADRESS}}", "{{P23}}"]), "template")

    def test_armature_f207_formula(self) -> None:
        from backend.core.validation import _build_armature_report

        report = _build_armature_report(
            {"supports": {"P23": 4, "A23": 3, "YA23": 2, "K21": 1}, "grounding_count": 4},
            {"F207": 30, "NC20": 30, "ES15": 4, "CS10": 12},
            {"FAZE": "трехфазный"},
        )
        f207 = next(item for item in report["items"] if item["field"] == "F207")
        self.assertEqual(f207["value"], 30)
        self.assertIn("П23×2=8", f207["formula"])

    def test_validation_issue_to_dict(self) -> None:
        issue = ValidationIssue(
            category="note",
            severity="error",
            code="NOTE_VALUE_MISSING_DATE",
            message="test",
            field="DATE",
            location="титульный лист, дата",
        )
        payload = issue.to_dict()
        self.assertEqual(payload["location"], "титульный лист, дата")


if __name__ == "__main__":
    unittest.main()
