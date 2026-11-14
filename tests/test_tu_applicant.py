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

    def test_41b_tu_detects_10kv_gabarit(self) -> None:
        from backend.core.tu_parser import _has_10kv_gabarit, parse_tu

        hyphenated = "ориентировочной протяженностью 490 м (из них 420 м в габари-\nтах 10 кВ)"
        self.assertTrue(_has_10kv_gabarit(hyphenated))
        tu_path = Path("/Users/vasilijhaustov/Downloads/_41b ТУ.pdf")
        if not tu_path.exists():
            return
        data, _warnings = parse_tu(tu_path)
        self.assertTrue(data["vl_in_10kv_gabarit"])

    def test_extracts_build_from_existing_pole_without_item_number(self) -> None:
        from backend.core.replacement_builder import build_replacement_map
        from backend.core.tu_parser import _extract_build_from, _extract_tp_name

        text = (
            "Проектом технологического присоединения предусматривается: "
            "Построить ВЛИ 0,4 кВ от существующей опоры №2 ВЛИ 0,4 кВ фидера №1 "
            "ТП № 1816/63 кВА до границы участка Заявителя ориентировочной протяженностью 120 м; "
            "установить трехфазный прибор учёта."
        )
        tp_name = _extract_tp_name(text)
        self.assertEqual(tp_name, "ТП № 1816/63 кВА")
        build_from = _extract_build_from(text, tp_name)
        self.assertIn("от существующей опоры №2", build_from)
        self.assertNotIn("ТП №", build_from)
        replacement = build_replacement_map("ПСД/48/2026/001", {"OTKUDASTROIT": build_from, "TP_NAME": tp_name}, {})
        self.assertEqual(
            replacement["{{OTKUDASTROIT}}"],
            "от существующей опоры №2 ВЛИ 0,4 кВ фидера №1",
        )

    def test_build_from_uses_commutator_in_10_1_1(self) -> None:
        from backend.core.tu_parser import _extract_build_from, _extract_tp_name

        text = (
            "10.1.1. Строительство новых линий электропередачи: "
            "от коммутационного аппарата по п. 10.1.3. построить одноцепную ВЛИ 0,4 кВ "
            "на железобетонных опорах изолированным алюминиевым проводом сечением от 50 до 100 мм² "
            "включительно ориентировочной протяжённостью 280 м к границе земельного участка Заявителя.\n"
            "10.1.2. Следующий пункт.\n"
            "Проектом технологического присоединения предусматривается: "
            "Построить ВЛИ 0,4 кВ от существующей опоры №2 ВЛИ 0,4 кВ фидера №1 "
            "ТП № 1816/63 кВА до границы участка Заявителя."
        )
        build_from = _extract_build_from(text, _extract_tp_name(text))
        self.assertTrue(build_from.lower().startswith("от коммутационного аппарата"))
        self.assertNotIn("существующей опоры", build_from)

    def test_build_from_uses_existing_pole_in_10_1_1(self) -> None:
        from backend.core.tu_parser import _extract_build_from, _extract_tp_name

        text = (
            "10.1.1. Строительство новых линий электропередачи: "
            "от существующей опоры №2 ВЛИ 0,4 кВ фидера №1 ТП № 1816/63 кВА "
            "построить одноцепную ВЛИ 0,4 кВ ориентировочной протяжённостью 120 м "
            "к границе земельного участка Заявителя.\n"
            "10.1.2. Следующий пункт."
        )
        tp_name = _extract_tp_name(text)
        build_from = _extract_build_from(text, tp_name)
        self.assertIn("от существующей опоры №2", build_from)
        self.assertNotIn("коммутационного аппарата", build_from)
        self.assertNotIn("ТП №", build_from)

    def test_cadastral_quarter_fills_kadnumber_and_missing_stays_blank(self) -> None:
        from backend.cad.oda_dwg_adapter import _apply_cadastral_mention
        from backend.core.replacement_builder import build_replacement_map
        from backend.core.tu_parser import _extract_address, _extract_kad_kind, _extract_kadnumber

        quarter_text = (
            "антенно-мачтовое сооружение; Липецкая область, Воловский муниципальный округ, "
            "д. Сапрон, ул. Речная, кадастровый квартал 48:01:1190206."
        )
        self.assertEqual(_extract_kadnumber(quarter_text), "48:01:1190206")
        self.assertEqual(_extract_kad_kind(quarter_text), "quarter")
        self.assertNotIn("48:01", _extract_address(quarter_text))
        replacement = build_replacement_map(
            "ПСД/48/2026/001",
            {"KADNUMBER": "48:01:1190206", "KAD_KIND": "quarter", "ADRESS": "д. Сапрон"},
            {},
        )
        self.assertEqual(replacement["{{KADNUMBER}}"], "48:01:1190206")
        titled = "по адресу: д. Сапрон, к/н 48:01:1190206 (2026/76644)"
        self.assertEqual(
            _apply_cadastral_mention(titled, replacement),
            "по адресу: д. Сапрон, к/к 48:01:1190206 (2026/76644)",
        )

        short_label = "участок к/к 48:01:1190206"
        self.assertEqual(_extract_kadnumber(short_label), "48:01:1190206")

        parcel = "кадастровый номер 48:20:0011002:28"
        self.assertEqual(_extract_kadnumber(parcel), "48:20:0011002:28")
        self.assertEqual(_extract_kad_kind(parcel), "number")

        blank = build_replacement_map("ПСД/48/2026/001", {"ADRESS": "д. Сапрон"}, {})
        self.assertEqual(blank["{{KADNUMBER}}"], "")
        self.assertNotIn("не указан", blank["{{KADNUMBER}}"])
        note = "по адресу: д. Сапрон, к/н (2026/76644). кадастровый номер не указан"
        cleaned = _apply_cadastral_mention(note, blank)
        self.assertNotIn("к/н", cleaned)
        self.assertNotIn("не указан", cleaned)
        self.assertNotIn("кадастровый", cleaned)
        self.assertIn("(2026/76644)", cleaned)


if __name__ == "__main__":
    unittest.main()
