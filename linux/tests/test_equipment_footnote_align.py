from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.cad.oda_dwg_adapter import (
    _format_equipment_footnote_text,
    _is_equipment_footnote_mtext,
    _left_align_equipment_footnote_raw,
    _repair_mtext_format_garbage,
)


class EquipmentFootnoteAlignTests(unittest.TestCase):
    def test_detect_equipment_footnote(self) -> None:
        self.assertTrue(
            _is_equipment_footnote_mtext(
                "Все применяемое оборудование, соответствует Реестру аттестованного"
            )
        )
        self.assertFalse(_is_equipment_footnote_mtext("Проектом технологического присоединения"))

    def test_repair_garbage_does_not_corrupt_whole_dxf_file(self) -> None:
        sample = "  0\nSECTION\n  2\nHEADER\n  1\n" + (
            r"\pxql;Все применяемое оборудование, соответствует Реестру"
        )
        repaired = _repair_mtext_format_garbage(sample)
        self.assertTrue(repaired.startswith("  0\nSECTION"))
        self.assertIn(r"\pxql;Все применяемое", repaired)

    def test_format_restores_left_paragraph_code(self) -> None:
        text = (
            "Все применяемое оборудование, соответствует Реестру "
            r"\P* - Допускается использование материалов"
        )
        formatted = _format_equipment_footnote_text(text)
        self.assertTrue(formatted.startswith(r"\pxql;"))
        self.assertNotIn(r"\P\pxql;", formatted)

    def test_format_preserves_template_paragraph_structure(self) -> None:
        text = (
            r"\pxql;Все применяемое оборудование, соответствует Реестру аттестованного"
            r"\P* - Допускается использование материалов"
        )
        self.assertEqual(_format_equipment_footnote_text(text), text)

    def test_repair_garbage_does_not_strip_left_align_for_footnote(self) -> None:
        text = (
            r"\pxql;Все применяемое оборудование, соответствует Реестру аттестованного"
            r"\P\pxql;* - Допускается использование материалов"
        )
        repaired = _repair_mtext_format_garbage(text)
        self.assertIn(r"\pxql;", repaired)
        self.assertNotIn("Все применяемое", repaired.split(r"\pxql;")[0])

    def test_raw_fix_restores_center_anchor_and_left_text(self) -> None:
        sample = (
            "  0\nMTEXT\n"
            "  5\nABC\n"
            " 10\n0.0\n"
            " 20\n200.0\n"
            " 40\n2.0\n"
            " 41\n200.0\n"
            " 71\n4\n"
            "  1\nВсе применяемое оборудование, соответствует Реестру\n"
            "  0\nLINE\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.dxf"
            path.write_text(sample, encoding="utf-8")
            _left_align_equipment_footnote_raw(path)
            updated = path.read_text(encoding="utf-8")
        self.assertIn(" 71\n5\n", updated)
        self.assertIn(" 10\n100.0\n", updated)
        self.assertIn(r"\pxql;", updated)

    def test_raw_join_preserves_chunk_boundary_without_false_paragraph(self) -> None:
        from backend.cad.oda_dwg_adapter import _raw_text_content_from_object

        sample = (
            "  0\nMTEXT\n"
            "  5\nABC\n"
            "  3\n"
            r"\pxql;Все применяемое оборудование, соответствует Реестру аттестованного первичного и вторичного оборудования, материалов и систем, допущенных к применению на объектах ПАО «Россети» \P* - Допускается использование материалов других производителей, до"
            "\n"
            "  1\n"
            'пущенных к применению на объектах ПАО "Россети"\n'
            "  0\nLINE\n"
        )
        joined = _raw_text_content_from_object(sample)
        self.assertIn("допущенных", joined)
        self.assertNotIn(r"до\Pпущенных", joined)
        self.assertEqual(joined.count(r"\P"), 1)

    def test_raw_join_preserves_font_code_split_across_chunks(self) -> None:
        from backend.cad.oda_dwg_adapter import (
            _apply_mtext_entity_fixes_raw,
            _format_equipment_footnote_text,
            _raw_text_content_from_object,
        )

        sample = (
            "  0\nMTEXT\n"
            "  3\n"
            r"\pxql;Все применяемое оборудование, соответствует Реестру аттестованного первичного и вторичного оборудования, \fTi"
            "\n"
            "  1\n"
            r"mes New Roman|b0|i0|c204|p18;материалов и систем, допущенных к применению на объектах ПАО «Россети» \P* - Допускается"
            "\n"
            "  0\nLINE\n"
        )
        joined = _raw_text_content_from_object(sample)
        self.assertIn(r"\fTimes New Roman|b0|i0|c204|p18;", joined)
        self.assertNotIn("mes New Roman", joined.replace(r"\fTimes New Roman", ""))
        formatted = _format_equipment_footnote_text(joined)
        self.assertIn(r"\fTimes New Roman|b0|i0|c204|p18;", formatted)
        self.assertNotIn(r"\P\pxql;mes", formatted)
        fixed = _apply_mtext_entity_fixes_raw(
            "  0\nMTEXT\n"
            "  3\n"
            r"\pxql;{\fTimes New Roman|b0|i0|c204|p18;\W0.8;Все применяемое оборудование"
            "\n"
            "  0\nLINE\n"
        )
        self.assertIn(r"\W0.8;", fixed)


if __name__ == "__main__":
    unittest.main()
