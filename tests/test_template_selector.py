from __future__ import annotations

import unittest
from pathlib import Path

from backend.core.template_selector import select_template_note_path


class TemplateSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.templates_dir = Path("examples/templates")

    def _select(self, supports: dict[str, int], komapparat: bool = False) -> Path:
        path, _ = select_template_note_path(
            self.templates_dir,
            {"requires_komapparat_template": komapparat},
            {"supports": supports},
        )
        return path

    def test_p23_only(self) -> None:
        self.assertEqual(
            self._select({"P23": 3, "A23": 0, "YA23": 0, "K21": 0}).name,
            "template_note_P23.dwg",
        )

    def test_komapparat_p23_only(self) -> None:
        self.assertEqual(
            self._select({"P23": 2, "A23": 0, "YA23": 0, "K21": 0}, komapparat=True).name,
            "template_note_komapparat_P23.dwg",
        )

    def test_p23_and_a23(self) -> None:
        self.assertEqual(
            self._select({"P23": 1, "A23": 2, "YA23": 0, "K21": 0}).name,
            "template_note_P23_A23.dwg",
        )

    def test_komapparat_p23_and_a23(self) -> None:
        self.assertEqual(
            self._select({"P23": 1, "A23": 1, "YA23": 0, "K21": 0}, komapparat=True).name,
            "template_note_komapparat_P23_A23.dwg",
        )

    def test_a23_and_ya23_without_p23(self) -> None:
        self.assertEqual(
            self._select({"P23": 0, "A23": 1, "YA23": 1, "K21": 0}).name,
            "template_note_A23_YA23_bezP.dwg",
        )

    def test_komapparat_a23_and_ya23_without_p23(self) -> None:
        self.assertEqual(
            self._select({"P23": 0, "A23": 2, "YA23": 1, "K21": 0}, komapparat=True).name,
            "template_note_komapparat_A23_YA23_bezP.dwg",
        )

    def test_a23_and_ya23_with_k21_uses_bezp_template(self) -> None:
        self.assertEqual(
            self._select({"P23": 0, "A23": 1, "YA23": 1, "K21": 1}).name,
            "template_note_A23_YA23_bezP.dwg",
        )

    def test_p23_a23_and_ya23_without_k21(self) -> None:
        self.assertEqual(
            self._select({"P23": 2, "A23": 1, "YA23": 1, "K21": 0}).name,
            "template_note_A23_YA23_bezK21.dwg",
        )

    def test_komapparat_p23_a23_and_ya23_without_k21(self) -> None:
        self.assertEqual(
            self._select({"P23": 1, "A23": 2, "YA23": 1, "K21": 0}, komapparat=True).name,
            "template_note_komapparat_A23_YA23_bezK21.dwg",
        )

    def test_p23_a23_ya23_and_k21_uses_full_template(self) -> None:
        self.assertEqual(
            self._select({"P23": 1, "A23": 1, "YA23": 1, "K21": 1}).name,
            "template_note_A23_YA23.dwg",
        )

    def test_p23_ya23_k21_without_a23_uses_ya23_template(self) -> None:
        self.assertEqual(
            self._select({"P23": 3, "A23": 0, "YA23": 2, "K21": 1}).name,
            "template_note_YA23.dwg",
        )

    def test_p23_and_k21_without_a23_uses_default_template(self) -> None:
        self.assertEqual(
            self._select({"P23": 4, "A23": 0, "YA23": 0, "K21": 1}).name,
            "template_note.dwg",
        )

    def test_komapparat_p23_and_k21_without_a23_uses_komapparat_default(self) -> None:
        self.assertEqual(
            self._select({"P23": 4, "A23": 0, "YA23": 0, "K21": 1}, komapparat=True).name,
            "template_note_komapparat.dwg",
        )

    def test_p23_a23_and_k21_without_ya23_uses_a23_template(self) -> None:
        self.assertEqual(
            self._select({"P23": 4, "A23": 1, "YA23": 0, "K21": 1}).name,
            "template_note_A23.dwg",
        )

    def test_komapparat_p23_a23_and_k21_without_ya23_uses_a23_template(self) -> None:
        self.assertEqual(
            self._select({"P23": 4, "A23": 1, "YA23": 0, "K21": 1}, komapparat=True).name,
            "template_note_komapparat_A23.dwg",
        )

    def test_project_194_plan_support_mix(self) -> None:
        plan_path = Path("output/VsePro/ПСД_48_2026_194/ПСД-48-2026-194 План.dxf")
        if not plan_path.exists():
            self.skipTest("plan 194 is unavailable")
        from backend.core.dxf_reader import analyze_dxf
        from backend.core.tu_parser import parse_tu

        plan_data, _ = analyze_dxf(plan_path)
        self.assertEqual(plan_data["supports"], {"P23": 4, "A23": 1, "YA23": 0, "K21": 1})
        tu_files = list(Path("output/VsePro/ПСД_48_2026_194").glob("*ТУ*"))
        if not tu_files:
            self.skipTest("plan 194 TU is unavailable")
        tu_data, _ = parse_tu(tu_files[0])
        self.assertTrue(tu_data.get("requires_komapparat_template"))
        path, _ = select_template_note_path(self.templates_dir, tu_data, plan_data)
        self.assertEqual(path.name, "template_note_komapparat_A23.dwg")

    def test_komapparat_p23_ya23_k21_without_a23_uses_ya23_template(self) -> None:
        self.assertEqual(
            self._select({"P23": 3, "A23": 0, "YA23": 2, "K21": 1}, komapparat=True).name,
            "template_note_komapparat_YA23.dwg",
        )

    def test_project_190_plan_support_mix(self) -> None:
        plan_path = Path("output/VsePro/ПСД_48_2026_190/ПСД-48-2026-190 План.dxf")
        if not plan_path.exists():
            self.skipTest("plan 190 is unavailable")
        from backend.core.dxf_reader import analyze_dxf

        plan_data, _ = analyze_dxf(plan_path)
        self.assertEqual(plan_data["supports"], {"P23": 4, "A23": 0, "YA23": 0, "K21": 1})
        path, _ = select_template_note_path(
            self.templates_dir,
            {"requires_komapparat_template": False},
            plan_data,
        )
        self.assertEqual(path.name, "template_note.dwg")

    def test_project_186_plan_support_mix(self) -> None:
        plan_path = Path("output/VsePro/ПСД_48_2026_286/ПСД-48-2026-186 План.dxf")
        if not plan_path.exists():
            self.skipTest("plan 186 is unavailable")
        from backend.core.dxf_reader import analyze_dxf

        plan_data, _ = analyze_dxf(plan_path)
        self.assertEqual(plan_data["supports"], {"P23": 3, "A23": 0, "YA23": 2, "K21": 1})
        path, _ = select_template_note_path(
            self.templates_dir,
            {"requires_komapparat_template": False},
            plan_data,
        )
        self.assertEqual(path.name, "template_note_YA23.dwg")

    def test_p23_a23_ya23_without_k21(self) -> None:
        self.assertEqual(
            self._select({"P23": 2, "A23": 1, "YA23": 1, "K21": 0}).name,
            "template_note_A23_YA23_bezK21.dwg",
        )

    def test_komapparat_p23_a23_ya23_without_k21(self) -> None:
        self.assertEqual(
            self._select({"P23": 3, "A23": 2, "YA23": 1, "K21": 0}, komapparat=True).name,
            "template_note_komapparat_A23_YA23_bezK21.dwg",
        )


if __name__ == "__main__":
    unittest.main()
