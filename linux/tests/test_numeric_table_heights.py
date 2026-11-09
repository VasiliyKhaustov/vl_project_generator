from __future__ import annotations

import unittest

from backend.cad.oda_dwg_adapter import (
    BODY_TEXT_HEIGHT,
    _cell_contains_numeric_quantity,
    _fix_acad_table_numeric_cell_pairs,
    _is_numeric_quantity_cell_text,
    _split_object_pairs,
)


class NumericQuantityCellTests(unittest.TestCase):
    def test_detects_slash_separated_values(self) -> None:
        self.assertTrue(_is_numeric_quantity_cell_text("5/2.7"))
        self.assertTrue(_is_numeric_quantity_cell_text("0.23/255.5"))
        self.assertTrue(_is_numeric_quantity_cell_text("0,002/0.538"))
        self.assertTrue(_is_numeric_quantity_cell_text("2.8"))

    def test_normalizes_split_cell_fragments(self) -> None:
        sample_pairs = [
            ["301", "CELL_VALUE"],
            ["170", "4"],
            ["140", "2.5"],
            ["1", r"{\H2.5;5}"],
            ["1", r"{\H1.4;/2.7}"],
            ["304", "ACVALUE_END"],
        ]
        self.assertTrue(_cell_contains_numeric_quantity(sample_pairs, 0))
        _fix_acad_table_numeric_cell_pairs(sample_pairs)
        height_pair = next(pair for pair in sample_pairs if pair[0].strip() == "140")
        self.assertEqual(height_pair[1], f"{BODY_TEXT_HEIGHT:.1f}")
        text_values = [pair[1] for pair in sample_pairs if pair[0].strip() == "1"]
        self.assertTrue(any(value == "5" for value in text_values))
        self.assertTrue(any("2.7" in value and "\\H" not in value for value in text_values))
        self.assertFalse(any("\\H" in value for value in text_values))


if __name__ == "__main__":
    unittest.main()
