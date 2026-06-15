from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.cad.oda_dwg_adapter import _cleanup_raw_dxf_text


class DxfCleanupIntegrityTests(unittest.TestCase):
    def test_cleanup_does_not_destroy_dxf_line_structure(self) -> None:
        sample = "\n".join(
            [
                "  0",
                "SECTION",
                "  2",
                "HEADER",
                "  0",
                "MTEXT",
                "  1",
                "садоводческое потребительское общество",
            ]
        )
        replacement_map = {
            "{{ADRESS}}": "Липецкая область, г.Липецк, СНП «Мечта»",
            "{{ADDRESS}}": "Липецкая область, г.Липецк, СНП «Мечта»",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.dxf"
            path.write_text(sample + "\n", encoding="utf-8")
            _cleanup_raw_dxf_text(path, replacement_map)
            updated = path.read_text(encoding="utf-8")

        self.assertIn("  0\nSECTION\n", updated)
        self.assertNotIn("0 SECTION 2 HEADER", updated)


if __name__ == "__main__":
    unittest.main()
