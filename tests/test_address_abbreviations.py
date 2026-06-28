from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.cad.oda_dwg_adapter import _fix_supports_install_note_raw
from backend.core.tu_parser import abbreviate_address_display_terms, _normalize_address_terms


class AddressAbbreviationTests(unittest.TestCase):
    def test_garage_cooperative_autolubiteley_to_gpka(self) -> None:
        value = (
            "Липецкая область, г.Липецк, гаражный потребительский кооператив автолюбителей "
            "«Северный-2», участок № 4"
        )
        normalized = abbreviate_address_display_terms(value)
        self.assertIn("ГПКА", normalized)
        self.assertIn("уч.", normalized)
        self.assertNotIn("автолюбителей", normalized.lower())

    def test_garage_cooperative_to_gpk(self) -> None:
        value = "гаражный потребительский кооператив «Южный»"
        self.assertIn("ГПК", abbreviate_address_display_terms(value))

    def test_garage_cooperative_short_to_gk(self) -> None:
        value = "гаражный кооператив «Восток»"
        self.assertIn("ГК", abbreviate_address_display_terms(value))

    def test_drops_redundant_urban_district_before_city(self) -> None:
        value = "Липецкая область, городской округ г.Липецк, г.Липецк, ГПК «Северный-2»"
        normalized = abbreviate_address_display_terms(value)
        self.assertNotIn("городской округ", normalized.lower())
        self.assertIn("Липецкая область, г.Липецк", normalized)

    def test_full_tu_address_normalization(self) -> None:
        value = (
            "Липецкая область, городской округ г. Липецк, г.Липецк, "
            "гаражный потребительский кооператив автолюбителей «Северный-2», участок № 4"
        )
        normalized = _normalize_address_terms(value)
        self.assertIn("ГПКА", normalized)
        self.assertIn("уч.", normalized)
        self.assertNotIn("городской округ", normalized.lower())


class SupportsInstallNoteTableTests(unittest.TestCase):
    def test_fixes_supports_note_in_acad_table(self) -> None:
        sample = "\n".join(
            [
                "  0",
                "ACAD_TABLE",
                "  1",
                "по 9 опорам",
                "302",
                "по 9 опорам",
            ]
        )
        replacement_map = {"{{SUPPORTS_INSTALL_NOTE}}": "по 10 опорам"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.dxf"
            path.write_text(sample + "\n", encoding="utf-8")
            _fix_supports_install_note_raw(path, replacement_map)
            updated = path.read_text(encoding="utf-8")

        self.assertIn("по 10 опорам", updated)
        self.assertNotIn("по 9 опорам", updated)


if __name__ == "__main__":
    unittest.main()
