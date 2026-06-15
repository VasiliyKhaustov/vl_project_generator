from __future__ import annotations

import unittest

from backend.core.cable_format import (
    calculate_sip4_kg,
    calculate_sip4_spec_table_kg,
    format_cable_section_display,
    format_sip4_spec_table_kg,
    sip4_weight_per_km,
)
from backend.core.calculator import calculate_materials
from backend.core.replacement_builder import build_replacement_map


class CableFormatTests(unittest.TestCase):
    def test_format_cable_section_uses_cyrillic_x(self) -> None:
        self.assertEqual(format_cable_section_display("3*70+1*70"), "3х70+1х70")
        self.assertEqual(format_cable_section_display("4x16"), "4х16")

    def test_sip4_weight_per_km(self) -> None:
        self.assertEqual(sip4_weight_per_km("4х16"), 269.0)
        self.assertEqual(sip4_weight_per_km("2х16"), 134.0)

    def test_sip4_kg_for_three_phase_example(self) -> None:
        self.assertAlmostEqual(calculate_sip4_kg("4х16", 0.002), 0.538)

    def test_sip4_kg_for_single_phase_example(self) -> None:
        self.assertAlmostEqual(calculate_sip4_kg("2х16", 0.002), 0.268)


    def test_sip4_spec_table_kg_rounds_to_tenths(self) -> None:
        self.assertEqual(calculate_sip4_spec_table_kg("2х16"), 0.3)
        self.assertEqual(calculate_sip4_spec_table_kg("4х16"), 0.5)
        self.assertEqual(format_sip4_spec_table_kg("2х16"), "0.3")
        self.assertEqual(format_sip4_spec_table_kg("4х16"), "0.5")


class Sip4MaterialsTests(unittest.TestCase):
    def test_materials_include_sip4_fields(self) -> None:
        materials = calculate_materials(
            {"FAZE": "трехфазный", "SECH_KABEL": "3х70+1х70"},
            {"line_length_km": 0.002, "supports": {}, "grounding_count": 0},
        )
        self.assertEqual(materials["SECH_SIP4"], "4х16")
        self.assertAlmostEqual(materials["SIP4_KG"], 0.538)

    def test_replacement_map_formats_sip4_kg(self) -> None:
        materials = calculate_materials(
            {"FAZE": "однофазный", "SECH_KABEL": "3х50+1х50"},
            {"line_length_km": 0.002, "supports": {}, "grounding_count": 0},
        )
        replacement_map = build_replacement_map("ПСД/48/2026/052", {}, materials)
        self.assertEqual(replacement_map["{{SECH_SIP4}}"], "2х16")
        self.assertEqual(replacement_map["{{SIP4_KG}}"], "0.268")


if __name__ == "__main__":
    unittest.main()
