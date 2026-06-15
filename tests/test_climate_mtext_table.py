from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.cad.oda_dwg_adapter import (
    SPEC_CERTIFICATE_TEXT_HEIGHT,
    _fix_climate_table_mtext_values_raw,
    _fix_spec_certificate_text_heights_raw,
    _is_spec_certificate_text,
)


class ClimateMtextTableTests(unittest.TestCase):
    def test_fixes_visible_climate_block_values(self) -> None:
        sample = "\n".join(
            [
                "  0",
                "BLOCK",
                "  2",
                "*T20",
                "  0",
                "MTEXT",
                "  1",
                "Район по гололеду",
                "  0",
                "MTEXT",
                "  1",
                "III",
                "  0",
                "MTEXT",
                "  1",
                "Нормативная толщина стенки гололеда",
                "  0",
                "MTEXT",
                "  1",
                "20",
                "  0",
                "MTEXT",
                "  1",
                "Район по ветру",
                "  0",
                "MTEXT",
                "  1",
                "III",
                "  0",
                "MTEXT",
                "  1",
                "Нормативная скорость ветра",
                "  0",
                "MTEXT",
                "  1",
                "32",
                "  0",
                "MTEXT",
                "  1",
                "Ветровое давление",
                "  0",
                "MTEXT",
                "  1",
                "650",
                "  0",
                "ENDBLK",
            ]
        )
        replacement_map = {
            "{{ICE_DISTRICT}}": "II",
            "{{WIND_DISTRICT}}": "II",
            "{{ICE_THICKNESS_MM}}": "15",
            "{{WIND_SPEED_MS}}": "29",
            "{{WIND_PRESSURE_PA}}": "500",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.dxf"
            path.write_text(sample + "\n", encoding="utf-8")
            _fix_climate_table_mtext_values_raw(path, replacement_map)
            updated = path.read_text(encoding="utf-8")

        self.assertIn("  1\nII", updated)
        self.assertIn("  1\n15", updated)
        self.assertIn("  1\n29", updated)
        self.assertIn("  1\n500", updated)
        self.assertNotIn("  1\nIII", updated)
        self.assertNotIn("  1\n650", updated)


class PpdCertificateHeightTests(unittest.TestCase):
    def test_detects_ppd_certificate_text(self) -> None:
        raw = r"{\\C256;IIПД-51/22\Pот05.09.2022 до 05.09.2027}"
        self.assertTrue(_is_spec_certificate_text(raw))

    def test_sets_ppd_certificate_height_to_two(self) -> None:
        sample = "\n".join(
            [
                "  0",
                "MTEXT",
                " 40",
                "3.0",
                "  1",
                r"{\\C256;IIПД-51/22\Pот05.09.2022 до 05.09.2027}",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.dxf"
            path.write_text(sample + "\n", encoding="utf-8")
            _fix_spec_certificate_text_heights_raw(path)
            updated = path.read_text(encoding="utf-8")

        self.assertIn(f" 40\n{SPEC_CERTIFICATE_TEXT_HEIGHT:.1f}", updated)


if __name__ == "__main__":
    unittest.main()
