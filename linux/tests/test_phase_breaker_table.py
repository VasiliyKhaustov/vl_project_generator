from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import ezdxf

from backend.cad.oda_dwg_adapter import (
    _apply_phase_breaker_replacements_raw,
    _cleanup_raw_dxf_text,
    _format_body_note_text,
    _centered_table_top,
    _land_allocation_tops,
    _integer_cell_text_is_shared,
    _ktp_scheme_anchors,
    _move_climate_table_down_raw,
    _raise_10kv_ktp_schemes,
    _set_reference_docs_row_heights_raw,
    _sheet_register_drop,
    _sync_va88_nominal_current_raw,
    _work_table_support_field_for_row,
)


class PhaseBreakerTableTests(unittest.TestCase):
  def test_replaces_three_pole_text_in_acad_table(self) -> None:
    sample = "\n".join(
      [
        "  0",
        "ACAD_TABLE",
        "  1",
        "Монтаж выключателя автоматического {\\C256;трехполюсного} в щит навесной",
        "  1",
        "ВА47-29 3Р 32А",
        "  1",
        "Выключатель автоматический трехполюсный,  Iн=32А",
        "  1",
        "Кол.",
      ]
    )
    replacement_map = {
      "{{BREAKER}}": "ВА47-29 1Р 32А",
      "{{BREAKER_CURRENT}}": "32А",
      "{{BREAKER_POLES_TEXT}}": "однополюсный",
      "{{BREAKER_POLES_TEXT_GENITIVE}}": "однополюсного",
    }
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp) / "sample.dxf"
      path.write_text(sample + "\n", encoding="utf-8")
      _apply_phase_breaker_replacements_raw(path, replacement_map)
      updated = path.read_text(encoding="utf-8")

    self.assertIn("однополюсного", updated)
    self.assertIn("однополюсный", updated)
    self.assertIn("ВА47-29 1Р 32А", updated)
    self.assertNotIn("трехполюс", updated)
    self.assertNotIn("3Р 32", updated)

  def test_cleanup_preserves_linked_table_structure(self) -> None:
    sample = "\n".join(
      [
        "  0",
        "SECTION",
        "  1",
        "CELLCONTENT_BEGIN",
        " 90",
        "1",
        "300",
        "VALUE",
        " 93",
        "6",
        " 90",
        "4",
        "  1",
        "0.396",
        "304",
        "ACVALUE_END",
        " 91",
        "0",
        "309",
        "CELLCONTENT_END",
      ]
    )
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp) / "sample.dxf"
      path.write_text(sample + "\n", encoding="utf-8")
      _cleanup_raw_dxf_text(path, {})
      updated = path.read_text(encoding="utf-8")

    self.assertNotIn("\n  1\n  1\n", updated)
    self.assertIn("0.396", updated)

  def test_removes_empty_paragraph_before_delivery_and_route_choice(self) -> None:
    sample = (
        r"кв.м.}\P\pxi4,l0,b0.25,qj,t1,4;{\A1;}\P\pxi4,l0,b0.25,qj,t0;{\A1;Доставка материалов"
        r"\P\pxi6,l0,ql,sm1;{}\P\pxi6,l0,ql,sm1;{}\P\pxi3,l1,r2.8572,sm1,ql;{При выборе оптимального варианта"
    )
    updated = _format_body_note_text(sample)
    self.assertNotIn(r"{\A1;}\P\pxi4,l0,b0.25,qj,t0;{\A1;Доставка", updated)
    self.assertIn("Доставка материалов", updated)
    self.assertNotIn(r"{}\P\pxi6,l0,ql,sm1;{}\P", updated)
    self.assertIn("При выборе оптимального", updated)

  def test_cleanup_preserves_dxf_structure(self) -> None:
    sample = "\n".join(
      [
        "  0",
        "SECTION",
        "  0",
        "MTEXT",
        "  1",
        "трехполюсный",
      ]
    )
    replacement_map = {
      "{{BREAKER_POLES_TEXT}}": "однополюсный",
    }
    with tempfile.TemporaryDirectory() as tmp:
      path = Path(tmp) / "sample.dxf"
      path.write_text(sample + "\n", encoding="utf-8")
      _cleanup_raw_dxf_text(path, replacement_map)
      updated = path.read_text(encoding="utf-8")

    self.assertIn("  0\nSECTION\n", updated)
    self.assertIn("однополюсный", updated)


class AdditionalBreakerTests(unittest.TestCase):
    def test_fifteen_kw_three_phase_is_one_step_higher(self) -> None:
        from backend.core.calculator import calculate_materials
        from backend.core.replacement_builder import build_replacement_map

        materials = calculate_materials(
            {"POWER_KW": "15", "FAZE": "трехфазный"},
            {"supports": {}, "line_length_m": 0, "grounding_count": 0},
        )
        self.assertEqual(materials["BREAKER"], "ВА47-29 3Р 32А")
        self.assertEqual(materials["komauto"], "ВА47-29 3Р 40А")
        replacement = build_replacement_map("ПСД/48/2026/001", {}, materials)
        self.assertEqual(replacement["{{komauto}}"], "ВА47-29 3Р 40А")
        self.assertEqual(replacement["{{KOMAUTO}}"], "ВА47-29 3Р 40А")

    def test_single_phase_additional_breaker_is_still_three_pole(self) -> None:
        from backend.core.calculator import calculate_materials

        materials = calculate_materials(
            {"POWER_KW": "5", "FAZE": "однофазный"},
            {"supports": {}, "line_length_m": 0, "grounding_count": 0},
        )
        self.assertEqual(materials["BREAKER"], "ВА47-29 1Р 25А")
        self.assertEqual(materials["komauto"], "ВА47-29 3Р 32А")

    def test_volume_cell_breaker_updates_and_komauto_stays_higher(self) -> None:
        from backend.cad.oda_dwg_adapter import _apply_calculated_literal_replacements

        fragmented = (
            r"{\fTimes New Roman|b0|i0|c204|p18;ВА}47-29 3"
            r"{\fTimes New Roman|b0|i0|c204|p18;Р }32"
            r"{\fTimes New Roman|b0|i0|c204|p18;А}"
        )
        replacement_map = {
            "{{BREAKER}}": "ВА47-29 3Р 16А",
            "{{komauto}}": "ВА47-29 3Р 25А",
        }
        self.assertEqual(
            _apply_calculated_literal_replacements(fragmented, replacement_map),
            "ВА47-29 3Р 16А",
        )
        self.assertEqual(
            _apply_calculated_literal_replacements("ВА47-29 3Р 25А", replacement_map),
            "ВА47-29 3Р 25А",
        )

    def test_va88_description_takes_nominal_from_the_type_cell(self) -> None:
        sample = (
            "ВА88-35 3Р 250А\n"
            "Выключатель автоматический трехполюсный,  Iн=50А\n"
            + ("x" * 4000)
            + "\nВыключатель автоматический трехполюсный,  Iн=32А\n"
        )
        updated = _sync_va88_nominal_current_raw(sample)
        self.assertIn("Выключатель автоматический трехполюсный,  Iн=250А", updated)
        self.assertIn("Выключатель автоматический трехполюсный,  Iн=32А", updated)
        self.assertIn("ВА88-35 3Р 250А", updated)

    def test_vertical_ground_18_l5_uses_two_plus_one_count(self) -> None:
        row = [
            "7",
            r"Монтаж вертикального заземлителя {\fArial|b0|i0|c204|p34;%%C}18 мм",
            "L=5 м",
            "шт",
            "1",
        ]
        self.assertEqual(_work_table_support_field_for_row(row), "185")
        horizontal = [
            "8",
            r"Монтаж горизонтального заземлителя {\fArial|b0|i0|c204|p34;%%C}12 мм",
            "L=5 м",
            "шт",
            "1",
        ]
        self.assertIsNone(_work_table_support_field_for_row(horizontal))

    def test_shared_integer_quantity_is_not_copied_into_other_rows(self) -> None:
        class Tag:
            def __init__(self, code: int, value: str) -> None:
                self.code = code
                self.value = value

        shared = [Tag(1, "3"), Tag(302, "3"), Tag(1, "3"), Tag(302, "3")]
        self.assertTrue(_integer_cell_text_is_shared(shared, "3"))
        unique = [Tag(1, "3"), Tag(302, "3"), Tag(1, "1"), Tag(302, "1")]
        self.assertFalse(_integer_cell_text_is_shared(unique, "3"))
        self.assertFalse(_integer_cell_text_is_shared(shared, "0,393"))

    def test_10kv_climate_table_is_raised_and_reference_rows_are_8(self) -> None:
        sample = "\n".join(
            [
                "  0",
                "ACAD_TABLE",
                " 10",
                "3710.0",
                " 20",
                "3767.0",
                " 30",
                "0.0",
                "  1",
                "Район по гололеду",
                "  0",
                "ENDSEC",
                "  0",
                "ACAD_TABLE",
                " 10",
                "6077.0",
                " 20",
                "3830.0",
                " 30",
                "0.0",
                "141",
                "16.0",
                "141",
                "21.0",
                "  1",
                "Обозначение",
                "  1",
                "Ссылочные документы",
                "  1",
                "Прилагаемые документы",
                "  0",
                "ENDSEC",
                "",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.dxf"
            path.write_text(sample, encoding="utf-8")
            _move_climate_table_down_raw(path, outside_band_shift=12.0)
            _set_reference_docs_row_heights_raw(path)
            updated = path.read_text(encoding="utf-8")
        self.assertIn("\n 20\n3779.0\n", updated)
        self.assertNotIn("\n 20\n3767.0\n", updated)
        self.assertNotIn("\n141\n16.0\n", updated)
        self.assertNotIn("\n141\n21.0\n", updated)
        self.assertGreaterEqual(updated.count("141\n6.0"), 2, updated)
        self.assertEqual(_sheet_register_drop(3758.8, 3697.7), 8.0)
        self.assertEqual(_sheet_register_drop(3700.0, 3697.7), 0.0)

    def test_climate_table_sits_below_the_upper_paragraph(self) -> None:
        # Центр зазора ещё накрывает абзац, поэтому таблица опускается на высоту шапки.
        top = _centered_table_top(3785.31, 3720.30, 3.0, 59.95)
        centered = (3785.31 + 3720.30 + 3.0 + 59.95) / 2
        self.assertAlmostEqual(top, centered - 12.0, places=2)
        self.assertLess(top, 3785.31)

    def test_land_tables_stack_under_the_paragraph(self) -> None:
        # Таблица 8 стоит на линии штампа, таблица 7 остаётся выше с зазором.
        top, lower = _land_allocation_tops(3634.0, 7, 3, 3770.31, 3723.15)
        self.assertAlmostEqual(lower - 24.0, 3634.0 + 2.0, places=2)
        self.assertAlmostEqual(top - 56.0, lower + 8.0, places=2)
        kept, kept_lower = _land_allocation_tops(None, 7, 3, None, 3766.03)
        self.assertAlmostEqual(kept, 3766.03, places=2)
        self.assertAlmostEqual(kept_lower, 3766.03 - 56.0, places=2)

    def test_ktp_scheme_lifts_drawing_and_leaves_stamp(self) -> None:
        document = ezdxf.new()
        modelspace = document.modelspace()
        modelspace.add_text("10 кВ", dxfattribs={"insert": (6743.6, 3896.3), "height": 3})
        modelspace.add_line((6760, 3716), (6800, 3716))
        modelspace.add_text("ПСД/48/2026/001-ТКР", dxfattribs={"insert": (6833, 3671), "height": 2.5})
        anchors = _ktp_scheme_anchors(document)
        _raise_10kv_ktp_schemes(document, anchors)
        texts = {entity.dxf.text: entity.dxf.insert.y for entity in modelspace.query("TEXT")}
        line = next(iter(modelspace.query("LINE")))
        self.assertAlmostEqual(texts["10 кВ"], 3903.3, places=2)
        self.assertAlmostEqual(line.dxf.start.y, 3723.0, places=2)
        self.assertAlmostEqual(texts["ПСД/48/2026/001-ТКР"], 3671, places=2)


if __name__ == "__main__":
  unittest.main()
