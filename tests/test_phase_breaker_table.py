from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.cad.oda_dwg_adapter import (
    _apply_phase_breaker_replacements_raw,
    _cleanup_raw_dxf_text,
    _format_body_note_text,
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


if __name__ == "__main__":
  unittest.main()
