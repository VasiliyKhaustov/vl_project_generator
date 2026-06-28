from __future__ import annotations

import unittest
from pathlib import Path

from backend.core.tu_parser import abbreviate_applicant_display_terms, parse_tu


class TuApplicantTests(unittest.TestCase):
    def test_abbreviates_ooo_rel(self) -> None:
        value = abbreviate_applicant_display_terms(
            'Общество с ограниченной ответственностью «РЕЛ»'
        )
        self.assertEqual(value, 'ООО «РЕЛ»')

    def test_corporate_tu_extracts_rel_applicant(self) -> None:
        tu_path = Path("output/VsePro/ПСД_48_2026_286/_006 ТУ.pdf")
        if not tu_path.exists():
            self.skipTest("corporate TU sample is unavailable")

        data, warnings = parse_tu(tu_path)
        self.assertEqual(data["APPLICANT"], 'ООО «РЕЛ»')
        self.assertFalse(any("APPLICANT" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
