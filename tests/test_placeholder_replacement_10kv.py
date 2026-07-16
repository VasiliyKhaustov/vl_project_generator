from __future__ import annotations

import unittest
from pathlib import Path

from backend.cad.oda_dwg_adapter import (
    _assign_mtext_dxf_chunks,
    _canonical_placeholder,
    _find_placeholders_in_dxf,
    _placeholder_name,
    _replace_placeholder_name,
    _replace_text,
    canonical_placeholder_key,
)
from backend.core.placeholders_10kv import template_placeholder_warning_10kv


class PlaceholderReplacement10kVTests(unittest.TestCase):
    def test_placeholder_names_with_hyphen_and_mixed_case(self) -> None:
        self.assertEqual(_placeholder_name("{{6-10}}"), "6-10")
        self.assertEqual(_placeholder_name("{{SECH_KABEL_10kV}}"), "SECH_KABEL_10kV")
        self.assertEqual(_placeholder_name("{{OTKUDA_STROIT_10kV}}"), "OTKUDA_STROIT_10kV")
        self.assertEqual(_placeholder_name("{{А20}}"), "А20")

    def test_canonical_placeholder_accepts_10kv_fields(self) -> None:
        self.assertEqual(_canonical_placeholder("{{6-10}}"), "{{6-10}}")
        self.assertEqual(_canonical_placeholder("{{SECH_KABEL_10kV}}"), "{{SECH_KABEL_10kV}}")

    def test_replace_10kv_placeholders_in_text(self) -> None:
        text = "ТП {{6-10}} кВ, 3x({{SECH_KABEL_10kV}}) мм²"
        replacement_map = {
            "{{6-10}}": "10/0,4",
            "{{SECH_KABEL_10kV}}": "1х50",
        }
        replaced, count = _replace_text(text, replacement_map)
        self.assertEqual(count, 2)
        self.assertEqual(replaced, "ТП 10/0,4 кВ, 3x(1х50) мм²")

    def test_mtext_formatting_is_not_placeholder(self) -> None:
        self.assertEqual(_canonical_placeholder("{вертикальный}"), "")
        self.assertEqual(_canonical_placeholder(r"{\H0.9x;вертикальный}"), "")

    def test_cyrillic_a231_maps_to_latin(self) -> None:
        self.assertEqual(canonical_placeholder_key("А231"), "{{A231}}")
        text = r"шт/ м³\P1/\{\{А231\}\}"
        replaced, count = _replace_placeholder_name(text, "A231", "2,88")
        self.assertEqual(count, 1)
        self.assertIn("2,88", replaced)
        self.assertNotIn("А231", replaced)

    def test_template_warning_accepts_cyrillic_a231(self) -> None:
        warning = template_placeholder_warning_10kv(
            Path("template.dwg"),
            {"supports": {"P23": 0, "A23": 4, "YA23": 0, "K21": 0}},
            ["{{A23}}", "{{А231}}", "{{Y4}}"],
        )
        self.assertIsNone(warning)

    def test_long_mtext_is_not_truncated_or_restructured(self) -> None:
        pairs = [["  3", "old-a"], ["  3", "old-b"], ["  1", "old-c"]]
        original_codes = [pair[0] for pair in pairs]
        replacement = "Текст " * 160

        _assign_mtext_dxf_chunks(pairs, replacement)

        self.assertEqual([pair[0] for pair in pairs], original_codes)
        self.assertEqual("".join(pair[1] for pair in pairs), replacement)


if __name__ == "__main__":
    unittest.main()
