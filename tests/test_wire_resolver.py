from __future__ import annotations

import copy
import unittest

from backend.core.calculator import calculate_materials
from backend.core.replacement_builder import build_replacement_map
from backend.core.wire_resolver import (
    WireSelectionError,
    apply_wire_selection,
    get_wire_weight,
    resolve_final_wire,
)


SAMPLE_CATALOG = {
    "wires": {
        "3*70+1*70": {
            "label": "3х70+1х70",
            "sech_kabel": "3х70+1х70",
            "weight_kg_per_km": 1112,
            "weight_source": "test",
        },
        "3*50+1*54,6": {
            "label": "3х50+1х54,6",
            "sech_kabel": "3х50+1х54,6",
            "weight_kg_per_km": 775,
            "weight_source": "test",
        },
        "3*35+1*35": {
            "label": "3х35+1х35",
            "sech_kabel": "3х35+1х35",
            "weight_kg_per_km": 566,
            "weight_source": "test",
        },
    }
}


class WireResolverTests(unittest.TestCase):
    def test_auto_mode_uses_auto_wire(self) -> None:
        result = resolve_final_wire("3x70+1x70", "3*50+1*54,6", "auto")
        self.assertEqual(result, "3x70+1x70")

    def test_manual_mode_uses_manual_wire(self) -> None:
        result = resolve_final_wire("3x70+1x70", "3*50+1*54,6", "manual")
        self.assertEqual(result, "3*50+1*54,6")

    def test_manual_mode_does_not_use_auto_as_final(self) -> None:
        tu_data = {"SECH_KABEL": "3x50+1x50"}
        wire_data = apply_wire_selection(
            tu_data,
            wire_selection_mode="manual",
            wire_manual_value="3*70+1*70",
            catalog=SAMPLE_CATALOG,
        )
        self.assertEqual(tu_data["SECH_KABEL"], "3х70+1х70")
        self.assertNotEqual(wire_data["wire_final_value"], "3x50+1x50")
        self.assertEqual(wire_data["wire_auto_detected"], "3x50+1x50")

    def test_manual_mode_requires_wire_value(self) -> None:
        with self.assertRaises(WireSelectionError):
            resolve_final_wire("3x70+1x70", None, "manual")

    def test_unknown_wire_raises_error(self) -> None:
        with self.assertRaises(WireSelectionError):
            get_wire_weight("9*99+1*99", catalog=SAMPLE_CATALOG)

    def test_weight_for_3x70_manual(self) -> None:
        weight = get_wire_weight("3*70+1*70", catalog=SAMPLE_CATALOG)
        self.assertEqual(weight["weight_kg_per_km"], 1112)

    def test_weight_for_3x50_manual(self) -> None:
        weight = get_wire_weight("3*50+1*54,6", catalog=SAMPLE_CATALOG)
        self.assertEqual(weight["weight_kg_per_km"], 775)

    def test_weight_for_3x35_manual(self) -> None:
        weight = get_wire_weight("3*35+1*35", catalog=SAMPLE_CATALOG)
        self.assertEqual(weight["weight_kg_per_km"], 566)

    def test_weight_missing_for_unknown_wire_raises(self) -> None:
        catalog = copy.deepcopy(SAMPLE_CATALOG)
        catalog["wires"]["NO_WEIGHT"] = {
            "label": "NO_WEIGHT",
            "sech_kabel": "9x9+1x9",
            "weight_kg_per_km": None,
            "weight_source": None,
        }
        tu_data = {"SECH_KABEL": "3x50+1x50"}
        with self.assertRaises(WireSelectionError):
            apply_wire_selection(
                tu_data,
                wire_selection_mode="manual",
                wire_manual_value="NO_WEIGHT",
                catalog=catalog,
            )

    def test_manual_3x50_wire_is_used_in_calculations(self) -> None:
        tu_data = {"SECH_KABEL": "3x50+1x50", "FAZE": "трехфазный"}
        apply_wire_selection(
            tu_data,
            wire_selection_mode="manual",
            wire_manual_value="3*50+1*54,6",
            catalog=SAMPLE_CATALOG,
        )
        materials = calculate_materials(tu_data, {"line_length_km": 1.0, "supports": {}, "grounding_count": 0})
        self.assertEqual(tu_data["SECH_KABEL"], "3х50+1х54,6")
        self.assertEqual(materials["SECH_KG"], 1.045 * 775)

    def test_manual_3x35_wire_is_used_in_calculations(self) -> None:
        tu_data = {"SECH_KABEL": "3x50+1x50", "FAZE": "трехфазный"}
        apply_wire_selection(
            tu_data,
            wire_selection_mode="manual",
            wire_manual_value="3*35+1*35",
            catalog=SAMPLE_CATALOG,
        )
        materials = calculate_materials(tu_data, {"line_length_km": 1.0, "supports": {}, "grounding_count": 0})
        self.assertEqual(tu_data["SECH_KABEL"], "3х35+1х35")
        self.assertEqual(materials["SECH_KG"], 1.045 * 566)

    def test_manual_wire_with_catalog_weight_is_used_in_calculations(self) -> None:
        catalog = copy.deepcopy(SAMPLE_CATALOG)
        catalog["wires"]["3*50+1*54,6"]["weight_kg_per_km"] = 820
        tu_data = {"SECH_KABEL": "3x50+1x50", "FAZE": "трехфазный"}
        apply_wire_selection(
            tu_data,
            wire_selection_mode="manual",
            wire_manual_value="3*50+1*54,6",
            catalog=catalog,
        )
        materials = calculate_materials(tu_data, {"line_length_km": 1.0, "supports": {}, "grounding_count": 0})
        self.assertEqual(materials["SECH_KG"], 1.045 * 820)

    def test_replacement_map_uses_final_wire(self) -> None:
        tu_data = {"SECH_KABEL": "3x70+1x70", "FAZE": "трехфазный"}
        apply_wire_selection(
            tu_data,
            wire_selection_mode="manual",
            wire_manual_value="3*70+1*70",
            catalog=SAMPLE_CATALOG,
        )
        materials = calculate_materials(
            tu_data,
            {"line_length_m": 100.0, "line_length_km": 0.1, "supports": {}, "grounding_count": 0},
        )
        replacement_map = build_replacement_map("ПСД/48/2026/111", tu_data, materials)
        self.assertEqual(replacement_map["{{SECH_KABEL}}"], "3х70+1х70")
        self.assertEqual(tu_data["wire_weight_final"], 1112)

    def test_manual_3x50_placeholder_matches_site_label(self) -> None:
        tu_data = {"SECH_KABEL": "3x50+1x50", "FAZE": "трехфазный"}
        apply_wire_selection(
            tu_data,
            wire_selection_mode="manual",
            wire_manual_value="3*50+1*54,6",
            catalog=SAMPLE_CATALOG,
        )
        replacement_map = build_replacement_map("ПСД/48/2026/111", tu_data, {"SECH_KG": 100.0})
        self.assertEqual(replacement_map["{{SECH_KABEL}}"], "3х50+1х54,6")
        self.assertNotEqual(replacement_map["{{SECH_KABEL}}"], "3х50+1х50")

    def test_auto_mode_preserves_legacy_weight_for_3x50(self) -> None:
        tu_data = {"SECH_KABEL": "3x50+1x50", "FAZE": "трехфазный"}
        apply_wire_selection(
            tu_data,
            wire_selection_mode="auto",
            wire_manual_value=None,
            catalog=SAMPLE_CATALOG,
        )
        materials = calculate_materials(tu_data, {"line_length_km": 1.0, "supports": {}, "grounding_count": 0})
        self.assertEqual(tu_data["SECH_KABEL"], "3х50+1х50")
        self.assertEqual(tu_data["wire_weight_final"], 775)
        self.assertEqual(materials["SECH_KG"], 1.045 * 775)


if __name__ == "__main__":
    unittest.main()
