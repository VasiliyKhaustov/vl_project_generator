from __future__ import annotations

import unittest

from backend.api.routes import _normalize_wire_form_params
from backend.core.replacement_builder import build_replacement_map
from backend.core.wire_resolver import WireSelectionError, apply_wire_selection


class WireFormParamsTests(unittest.TestCase):
    def test_normalize_auto_mode(self) -> None:
        mode, manual = _normalize_wire_form_params("auto", None)
        self.assertEqual(mode, "auto")
        self.assertIsNone(manual)

    def test_normalize_manual_mode(self) -> None:
        mode, manual = _normalize_wire_form_params("manual", "3*70+1*70")
        self.assertEqual(mode, "manual")
        self.assertEqual(manual, "3*70+1*70")

    def test_normalize_combined_select_value(self) -> None:
        mode, manual = _normalize_wire_form_params("manual:3*70+1*70", None)
        self.assertEqual(mode, "manual")
        self.assertEqual(manual, "3*70+1*70")

    def test_manual_without_value_raises(self) -> None:
        with self.assertRaises(WireSelectionError):
            _normalize_wire_form_params("manual", None)


class WireReplacementIntegrationTests(unittest.TestCase):
    def test_manual_wire_reaches_sech_kabel_placeholder(self) -> None:
        tu_data = {"SECH_KABEL": "3x50+1x50", "FAZE": "однофазный"}
        apply_wire_selection(
            tu_data,
            wire_selection_mode="manual",
            wire_manual_value="3*70+1*70",
        )
        replacement_map = build_replacement_map("ПСД/48/2026/111", tu_data, {"SECH_KG": 200.0})
        self.assertEqual(replacement_map["{{SECH_KABEL}}"], "3х70+1х70")
        self.assertEqual(tu_data["SECH_KABEL"], "3х70+1х70")


if __name__ == "__main__":
    unittest.main()
