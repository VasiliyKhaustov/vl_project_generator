from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.cad.oda_dwg_adapter import _fix_project_indicator_table_values


class ProjectIndicatorTableTests(unittest.TestCase):
    def test_does_not_corrupt_dxf_group_code_102(self) -> None:
        sample = "\n".join(
            [
                "  0",
                "SECTION",
                "280",
                "     1",
                "102",
                "ACAD_ROUNDTRIP_2008_TABLE_ENTITY",
                "  1",
                "{\\H1.0x;Строительная длина ВЛИ-0,4 кВ}",
                "  1",
                "км",
                "  1",
                "102",
            ]
        )
        replacement_map = {
            "{{LINE_LENGTH_M}}": "102",
            "{{LINE_LENGTH_KM}}": "0.102",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.dxf"
            path.write_text(sample + "\n", encoding="utf-8")
            _fix_project_indicator_table_values(path, replacement_map)
            updated = path.read_text(encoding="utf-8")

        self.assertIn("\n102\nACAD_ROUNDTRIP_2008_TABLE_ENTITY", updated)
        self.assertNotIn("\n0.102\nACAD_ROUNDTRIP_2008_TABLE_ENTITY", updated)
        self.assertIn("0.102", updated)

    def test_replaces_indicator_length_in_text_cell_only(self) -> None:
        sample = "\n".join(
            [
                "  1",
                "{\\H1.0x;Строительная длина ВЛИ-0,4 кВ}",
                "  1",
                "км",
                "  1",
                "102",
            ]
        )
        replacement_map = {
            "{{LINE_LENGTH_M}}": "102",
            "{{LINE_LENGTH_KM}}": "0.102",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.dxf"
            path.write_text(sample + "\n", encoding="utf-8")
            _fix_project_indicator_table_values(path, replacement_map)
            updated = path.read_text(encoding="utf-8")

        self.assertIn("  1\n0.102", updated)


if __name__ == "__main__":
    unittest.main()
