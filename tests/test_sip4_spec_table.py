from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.cad.oda_dwg_adapter import (
    _fix_sip4_numeric_width_raw,
    _fix_sip4_spec_table_values_raw,
    _fix_spec_certificate_text_heights_raw,
)


SIP4_TABLE_SNIPPET = """  0
MTEXT
  5
153B2A
330
153AA8
100
AcDbEntity
  8
0
100
AcDbMText
 10
180.0
 20
-152.2142857142857
 30
0.0
 40
3.0
 41
57.0
 46
0.0
 71
5
 72
5
  1
ГОСТ 31946-2012\\PСИП4
  7
стиль1
  0
MTEXT
  5
153B2D
330
153AA8
100
AcDbEntity
  8
0
100
AcDbMText
 10
300.0
 20
-152.2142857142857
 30
0.0
 40
3.0
 41
17.0
 46
0.0
 71
5
 72
5
  1
км
  7
стиль1
  0
MTEXT
  5
153B2E
330
153AA8
100
AcDbEntity
  8
0
100
AcDbMText
 10
314.98
 20
-152.2142857142857
 30
0.0
 40
3.0
 41
6.96
 46
0.0
 71
5
 72
5
  1
{0,186
  7
стиль1
  0
MTEXT
  5
153B2F
330
153AA8
100
AcDbEntity
  8
0
100
AcDbMText
 10
324.94
 20
-152.2142857142857
 30
0.0
 40
3.0
 41
6.96
 46
0.0
 71
5
 72
5
  1
{24.924}
  7
стиль1
  0
LINE
"""

SIP4_ACAD_TABLE_SNIPPET = """  0
ACAD_TABLE
  5
TABLE1
100
AcDbEntity
  1
ГОСТ 31946-2012\\PСИП4
  1
км
  1
{0,186
  1
{24.924}
  0
LINE
"""

CERTIFICATE_SNIPPET = """  0
MTEXT
  5
CERT1
330
153AA8
100
AcDbEntity
  8
0
100
AcDbMText
 10
227.5
 20
-94.0
 30
0.0
 40
3.0
 41
32.0
 46
0.0
 71
5
 72
5
  1
IЗ-93/23 {\\Pс 02.06.2023 по 02.06.2028}
  7
стиль1
  0
LINE
"""


class Sip4SpecTableFixTests(unittest.TestCase):
    def _replacement_map(self, sech_sip4: str) -> dict[str, str]:
        return {
            "{{SECH_SIP4}}": sech_sip4,
            "{{LINE_LENGTH_KM}}": "0.186",
            "{{SIP4_KG}}": "24.924",
        }

    def test_updates_sip4_km_and_mass_cells_for_single_phase(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "table.dxf"
            path.write_text(SIP4_TABLE_SNIPPET, encoding="utf-8")
            _fix_sip4_spec_table_values_raw(path, self._replacement_map("2х16"))
            text = path.read_text(encoding="utf-8")

        self.assertIn("{0,002", text)
        self.assertIn("{0.3}", text)
        self.assertNotIn("{0,186", text)
        self.assertNotIn("{24.924}", text)

    def test_updates_sip4_mass_for_three_phase_example(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "table.dxf"
            path.write_text(SIP4_TABLE_SNIPPET, encoding="utf-8")
            _fix_sip4_spec_table_values_raw(path, self._replacement_map("4х16"))
            text = path.read_text(encoding="utf-8")

        self.assertIn("{0,002", text)
        self.assertIn("{0.5}", text)

    def test_updates_embedded_acad_table_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "table.dxf"
            path.write_text(SIP4_ACAD_TABLE_SNIPPET, encoding="utf-8")
            _fix_sip4_spec_table_values_raw(path, self._replacement_map("2х16"))
            text = path.read_text(encoding="utf-8")

        self.assertIn("{0,002", text)
        self.assertIn("{0.3}", text)
        self.assertNotIn("{24.924}", text)

    def test_applies_width_factor_only_to_sip4_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "table.dxf"
            path.write_text(SIP4_TABLE_SNIPPET, encoding="utf-8")
            replacement_map = self._replacement_map("2х16")
            _fix_sip4_spec_table_values_raw(path, replacement_map)
            _fix_sip4_numeric_width_raw(path, replacement_map)
            text = path.read_text(encoding="utf-8")

        self.assertIn(r"\W0.90000;", text)
        self.assertIn("ГОСТ 31946-2012", text)

    def test_certificate_text_height_is_two(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "table.dxf"
            path.write_text(CERTIFICATE_SNIPPET, encoding="utf-8")
            _fix_spec_certificate_text_heights_raw(path)
            text = path.read_text(encoding="utf-8")

        self.assertIn("\n 40\n2.0\n", text)
        self.assertNotIn(r"\T0.85;", text)


if __name__ == "__main__":
    unittest.main()
