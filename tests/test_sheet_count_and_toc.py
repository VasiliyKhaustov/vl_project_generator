from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import ezdxf

from backend.cad.oda_dwg_adapter import (
    TOC_ELECTRO_ITEM_PLAIN,
    _fix_toc_electro_item_alignment_raw,
)
from backend.core.calculator import _sheet_labels_from_a3_count
from backend.core.dxf_reader import count_a3_route_sheets
from backend.core.tu_parser import _normalize_address_terms, abbreviate_garden_partnership_terms


class SheetCountTests(unittest.TestCase):
    def test_project_467_plan_counts_single_a3_sheet(self) -> None:
        plan_path = Path("output/VsePro/ПСД_48_2026_467/ПСД-48-2026-142 План.dxf")
        if not plan_path.exists():
            self.skipTest("project 467 plan fixture is unavailable")
        self.assertEqual(count_a3_route_sheets(plan_path), 1)

    def test_sheet_labels_for_single_route_sheet(self) -> None:
        labels = _sheet_labels_from_a3_count(1)
        self.assertEqual(labels["route_plan_sheet"], "5")
        self.assertEqual(labels["total_sheets"], 5)


class AddressAbbreviationTests(unittest.TestCase):
    def test_garden_consumer_society_is_abbreviated_to_snp(self) -> None:
        value = (
            "Липецкая область, г.Липецк, Липецкое садоводческое потребительское общество "
            "«Металлург-1», участок № 602"
        )
        normalized = _normalize_address_terms(value)
        self.assertIn("СНП", normalized)
        self.assertNotIn("потребительское общество", normalized.lower())

    def test_garden_nonprofit_partnership_is_abbreviated_to_snp(self) -> None:
        value = (
            "Липецкая область, г.Липецк, садоводческое некоммерческое партнерство "
            "«Мечта», участок № 169"
        )
        normalized = _normalize_address_terms(value)
        self.assertIn("СНП", normalized)
        self.assertNotIn("садоводческое некоммерческое партнерство", normalized.lower())


class TocElectroAlignmentTests(unittest.TestCase):
    def test_body_section_two_heading_is_centered(self) -> None:
        from backend.cad.oda_dwg_adapter import _format_body_note_text, _is_centered_heading_paragraph

        paragraph = r"\pxql,t0;{\A1;2.   Электротехнические  решения}"
        self.assertTrue(_is_centered_heading_paragraph(paragraph))
        formatted = _format_body_note_text(paragraph)
        self.assertIn(r"\pxqc", formatted)

    def test_aligns_only_second_toc_item(self) -> None:
        sample = "\n".join(
            [
                "  0",
                "BLOCK",
                "  2",
                "*T16",
                "  0",
                "MTEXT",
                " 71",
                "4",
                " 10",
                "61.5",
                " 20",
                "-47.5",
                "  1",
                "{1. Исходные данные}",
                "  0",
                "MTEXT",
                " 71",
                "1",
                " 10",
                "15.5",
                " 20",
                "-55.8",
                "  1",
                r"{2. Электротехнические решения}",
                "  0",
                "MTEXT",
                " 71",
                "4",
                " 10",
                "61.5",
                " 20",
                "-64.2",
                "  1",
                "{3. Строительные решения}",
                "  0",
                "ENDBLK",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.dxf"
            path.write_text(sample + "\n", encoding="utf-8")
            _fix_toc_electro_item_alignment_raw(path)
            updated = path.read_text(encoding="utf-8")

        self.assertIn(" 71\n4", updated)
        self.assertIn(" 10\n61.5", updated)
        self.assertIn(TOC_ELECTRO_ITEM_PLAIN, updated)


if __name__ == "__main__":
    unittest.main()
