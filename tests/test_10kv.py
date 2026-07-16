from __future__ import annotations

import unittest
from pathlib import Path

from backend.core.calculator_10kv import calculate_materials_10kv, yopk_value
from backend.core.project_type import is_10kv_project, resolve_project_is_10kv, has_10kv_plan_features
from backend.core.plan_reader_10kv import classify_10kv_support_label, read_plan_10kv_data
from backend.core.replacement_builder_10kv import build_replacement_map_10kv
from backend.core.template_selector_10kv import select_template_note_path_10kv
from backend.core.tu_parser_10kv import enrich_tu_data_10kv


class ProjectTypeTests(unittest.TestCase):
    def test_detects_10kv_tu(self) -> None:
        text = (
            "10.1.1.1. От опоры ВЛ 10 кВ Романово до РУ 10 кВ проектируемой ТП 10/0,4 кВ "
            "смонтировать одноцепную ВЛЗ 10 кВ.\n"
            "10.1.2. Строительство новых подстанций: смонтировать ТП 10/0,4 кВ "
            "с силовым трансформатором мощностью 160 кВА киоскового типа."
        )
        self.assertTrue(is_10kv_project(text))

    def test_detects_ot_opory_vl_10kv_marker(self) -> None:
        text = (
            "10.1.1. Строительство новых линий электропередачи:\n"
            "10.1.1.1. От опоры ВЛ 10 кВ Романово по п. 10.2.1. до РУ 10 кВ "
            "проектируемой ТП 10/0,4 кВ смонтировать одноцепную ВЛЗ 10 кВ "
            "сечением до 50 мм² ориентировочной протяженностью 260 м."
        )
        self.assertTrue(is_10kv_project(text))
        plan_data = {
            "supports_10kv": {"P20": 2, "A20": 0, "UP": 0, "UA": 0, "ARLK": 1},
            "line_length_10kv_m": 260.0,
        }
        self.assertTrue(resolve_project_is_10kv(text, plan_data))

    def test_plan_layer_10_triggers_10kv(self) -> None:
        """Полилиния на слое 10 → проект 10 кВ, даже без опор в supports_10kv-счётчике."""
        self.assertTrue(
            has_10kv_plan_features(
                {
                    "supports_10kv": {"P20": 0, "A20": 0, "UP": 0, "UA": 0, "ARLK": 0},
                    "line_length_10kv_m": 190.0,
                }
            )
        )
        self.assertFalse(
            has_10kv_plan_features(
                {
                    "supports_10kv": {"P20": 0, "A20": 0, "UP": 0, "UA": 0, "ARLK": 0},
                    "line_length_10kv_m": 0.0,
                    "line_length_04kv_m": 15.0,
                }
            )
        )

    def test_04kv_tu_not_detected_as_10kv(self) -> None:
        text = (
            "13.1.1. От опоры №12 ВЛИ 0,4 кВ фидера №2 ТП №10/0,4 кВА построить "
            "одноцепную ВЛИ 0,4 кВ сечением кабеля до 50.\n"
            "13.1.2. Строительство новых подстанций: не требуется.\n"
            "8. Основной источник питания: ВЛ 10 кВ яч. № 13."
        )
        self.assertFalse(is_10kv_project(text))

    def test_04kv_plan_overrides_10kv_tu_markers(self) -> None:
        tu_text = (
            "10.1.1.1. От опоры ВЛ 10 кВ построить одноцепную ВЛЗ 10 кВ.\n"
            "Технологическое присоединение: 0,4 кВ."
        )
        plan_data = {
            "supports_10kv": {"P20": 0, "A20": 0, "UP": 0, "UA": 0, "ARLK": 0},
            "line_length_10kv_m": 0.0,
        }
        self.assertTrue(is_10kv_project(tu_text))
        self.assertFalse(resolve_project_is_10kv(tu_text, plan_data))
        self.assertFalse(has_10kv_plan_features(plan_data))


class TemplateSelector10kVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.templates_dir = Path("examples/templates")

    def test_p23_a23_with_p20_a20_arlk(self) -> None:
        path, _ = select_template_note_path_10kv(
            self.templates_dir,
            {
                "supports": {"P23": 2, "A23": 1, "YA23": 0, "K21": 0},
                "supports_10kv": {"P20": 3, "A20": 1, "UP": 0, "UA": 0, "ARLK": 1},
            },
        )
        self.assertEqual(
            path.name,
            "Опоры (П23 и А23) и опоры П20 и А20 и А20 РЛК.dwg",
        )

    def test_p23_a23_with_ua20(self) -> None:
        path, _ = select_template_note_path_10kv(
            self.templates_dir,
            {
                "supports": {"P23": 2, "A23": 1, "YA23": 0, "K21": 0},
                "supports_10kv": {"P20": 2, "A20": 0, "UP": 0, "UA": 1, "ARLK": 1},
            },
        )
        self.assertEqual(
            path.name,
            "Опоры (П23 и А23) и опоры П20 и УА20 и А20 РЛК.dwg",
        )

    def test_a23_with_ua_and_arlk_uses_ua_template(self) -> None:
        path, _ = select_template_note_path_10kv(
            self.templates_dir,
            {
                "supports": {"P23": 0, "A23": 4, "YA23": 0, "K21": 0},
                "supports_10kv": {"P20": 7, "A20": 0, "UP": 0, "UA": 1, "ARLK": 1},
            },
        )
        self.assertEqual(
            path.name,
            "Опора А23 и опоры П20 и УА20 и А20 РЛК.dwg",
        )

    def test_p23_only_with_p20_arlk(self) -> None:
        path, _ = select_template_note_path_10kv(
            self.templates_dir,
            {
                "supports": {"P23": 3, "A23": 0, "YA23": 0, "K21": 0},
                "supports_10kv": {"P20": 2, "A20": 0, "UP": 0, "UA": 0, "ARLK": 1},
            },
        )
        self.assertEqual(
            path.name,
            "Опора П23 и опорыП20 и А20 РЛК.dwg",
        )


class Calculator10kVTests(unittest.TestCase):
    def test_yopk_values(self) -> None:
        self.assertEqual(yopk_value("intermediate"), "УОП")
        self.assertEqual(yopk_value("anchor"), "УОК")

    def test_basic_materials(self) -> None:
        result = calculate_materials_10kv(
            {
                "MOSH": "160",
                "6-10": "10/0,4",
                "SECH_KABEL_10kV": "1х50",
                "SECH_KABEL": "3х70+1х70",
                "POWER_KW": "150",
            },
            {
                "supports_10kv": {"P20": 3, "A20": 1, "UP": 0, "UA": 1, "ARLK": 1},
                "line_length_10kv_m": 350.0,
                "line_length_10kv_km": 0.35,
                "line_length_04kv_m": 388.0,
                "POWER_10": "0,35",
                "POWER_LENGT_M": "388",
                "KM_10": "0,35",
                "KM_04": "0,388",
            },
            branch_pole_type="intermediate",
        )
        self.assertEqual(result["YOPK"], "УОП")
        self.assertEqual(result["POWER_KW"], "150")
        self.assertEqual(result["KM_10_ROUTE"], "0,35")
        self.assertEqual(result["KTP_ENTRY_10_KM"], "0,005")
        self.assertEqual(result["POWER_10"], "0,355")
        self.assertEqual(result["KM_10"], "0,355")
        self.assertEqual(result["KM10"], 1.113)
        self.assertEqual(result["KM_04_ROUTE"], "0,388")
        self.assertEqual(result["KTP_ENTRY_KM"], "0,005")
        self.assertEqual(result["KM_04"], "0,393")
        self.assertEqual(result["KM_04_RESERVE"], 0.411)
        self.assertEqual(result["KG_04"], 456.7)
        self.assertEqual(result["POWER_LENGT_M"], "393")
        self.assertEqual(result["P20"], 3)
        self.assertEqual(result["P"], 3)
        self.assertEqual(result["A"], 1)
        self.assertEqual(result["ARLK"], 1)
        self.assertEqual(result["RAZ"], 1)
        self.assertEqual(result["AS"], 0.204)
        self.assertEqual(result["65"], 2)
        self.assertEqual(result["66"], 2)
        # PN: 6*A20 + 3*ARLK + 6*UA = 6*1 + 3*1 + 6*1 = 15
        # ARLK не входит в множитель 6*A20.
        self.assertEqual(result["PN"], 15)
        self.assertEqual(result["PI"], 30)
        self.assertEqual(result["OSH_KG"], 2.0)
        self.assertEqual(result["TM73_KG"], 9.85)
        self.assertEqual(result["TM74_KG"], 13.0)
        self.assertEqual(result["BRANCH_04_KM"], "0.004")
        self.assertEqual(result["BRANCH_04_KG"], 3.239)
        self.assertEqual(result["SQUARE_10kV"], 3850)
        self.assertEqual(result["IZM"], 6)
        self.assertEqual(result["SV10"], 10)
        self.assertEqual(result["1210"], result["185"])
        self.assertEqual(result["681"], 33)
        self.assertEqual(result["NOM"], "232")
        self.assertEqual(result["PRED"], "101-20")
        self.assertEqual(result["PLAV"], "20")
        self.assertEqual(
            (result["QF1"], result["QF2"], result["QF3"], result["QF4"]),
            ("100", "100", "100", "-"),
        )

    def test_pn_without_plain_a20_uses_only_arlk(self) -> None:
        result = calculate_materials_10kv(
            {"MOSH": "160", "6-10": "10/0,4"},
            {"supports_10kv": {"P20": 6, "A20": 0, "UP": 0, "UA": 1, "ARLK": 1}},
        )
        self.assertEqual(result["P20"], 6)
        self.assertEqual(result["A20"], 0)
        self.assertEqual(result["ARLK"], 1)
        # Только РЛК и УА: 6*0 + 3*1 + 6*1 = 9
        self.assertEqual(result["PN"], 9)
        self.assertEqual(result["SERG"], 9)
        self.assertEqual(result["PI"], 18)
        # SHF: 3*P20 + 3*UA + A20_base + 3 = 18 + 3 + 1 + 3 = 25
        self.assertEqual(result["SHF"], 25)
        self.assertEqual(result["K9"], 25)
        # В остальных формулах ARLK по-прежнему входит в базовую А20.
        self.assertEqual(result["65"], 1)
        self.assertEqual(result["AS"], 0.102)

    def test_transformer_protection_depends_on_voltage(self) -> None:
        plan_data = {"supports_10kv": {}}
        ten_kv = calculate_materials_10kv(
            {"MOSH": "100", "6-10": "10/0,4"},
            plan_data,
        )
        six_kv = calculate_materials_10kv(
            {"MOSH": "100", "6-10": "6/0,4"},
            plan_data,
        )
        self.assertEqual(ten_kv["PRED"], "101-16")
        self.assertEqual(ten_kv["PLAV"], "16")
        self.assertEqual(six_kv["PRED"], "101-20")
        self.assertEqual(six_kv["PLAV"], "20")
        self.assertEqual(ten_kv["NOM"], "144")
        self.assertEqual(
            (ten_kv["QF1"], ten_kv["QF2"], ten_kv["QF3"], ten_kv["QF4"]),
            ("100", "80", "40", "-"),
        )

    def test_10kv_display_abbreviations(self) -> None:
        result = build_replacement_map_10kv(
            "ПСД/48/2026/001",
            {
                "APPLICANT": "Крестьянское фермерское хозяйство «Милованово»",
                "ADRESS": "Липецкая область, Липецкий муниципальный район",
            },
            {},
            {},
        )
        self.assertEqual(result["{{APPLICANT}}"], "КФХ «Милованово»")
        self.assertEqual(result["{{ADRESS}}"], "Липецкая область, Липецкий район")


class PlanReader10kVTests(unittest.TestCase):
    def test_classify_support_labels(self) -> None:
        self.assertEqual(classify_10kv_support_label("П20-3Н"), "P20")
        self.assertEqual(classify_10kv_support_label("УА20-3Н"), "UA")
        self.assertEqual(classify_10kv_support_label("А20-3Н+КР2"), "ARLK")
        self.assertEqual(
            classify_10kv_support_label("А20-3Н", block_name="Пл_ОпораНВ_А23"),
            None,
        )
        self.assertEqual(classify_10kv_support_label("А23"), None)

    def test_read_milovanovo_plan_supports_and_04kv_length(self) -> None:
        plan_dxf = Path("output/result/temp/plan_debug.dxf")
        if not plan_dxf.exists():
            self.skipTest("plan_debug.dxf отсутствует — сначала конвертируйте plan.dwg")
        data, warnings = read_plan_10kv_data(plan_dxf)
        supports = data["supports_10kv"]
        self.assertEqual(supports["P20"], 7)
        self.assertEqual(supports["A20"], 0)
        self.assertEqual(supports["UA"], 1)
        self.assertEqual(supports["ARLK"], 1)
        self.assertGreater(data["line_length_04kv_m"], 6.0)
        self.assertLess(data["line_length_04kv_m"], 8.0)
        self.assertEqual(data["KM_04"], "0,007")
        self.assertEqual(data["POWER_LENGT_M"], "7")
        self.assertFalse(any("0,4 кВ не найдена" in warning for warning in warnings))


class TuParser10kVTests(unittest.TestCase):
    def test_enrich_tu_fields(self) -> None:
        text = (
            "8. Основной источник питания:\n"
            "- базовая подстанция 110-35 кВ: ПС 35/10 кВ Романово,\n"
            "10.1.1.1. От опоры ВЛ 10 кВ Романово по п. 10.2.2 до РУ 10 кВ проектируемой ТП 10/0,4 кВ "
            "смонтировать одноцепную ВЛЗ 10 кВ сечением до 50 мм².\n"
            "10.1.2. Строительство новых подстанций: смонтировать ТП 10/0,4 кВ "
            "с силовым трансформатором мощностью 160 кВА киоскового типа."
        )
        tu_path = Path("output/test_tu_10kv_sample.txt")
        tu_path.parent.mkdir(parents=True, exist_ok=True)
        tu_path.write_text(text, encoding="utf-8")

        from unittest.mock import patch

        with patch("backend.core.tu_parser_10kv.read_tu_text", return_value=text):
            data, warnings = enrich_tu_data_10kv(tu_path, {})
        self.assertEqual(data["PS_NAME"], "ПС Романово")
        self.assertEqual(data["6-10"], "10/0,4")
        self.assertEqual(data["SECH_KABEL_10kV"], "1х50")
        self.assertEqual(data["MOSH"], "160")
        self.assertEqual(data["OTKUDA_STROIT_10kV"], "от опоры ВЛ 10 кВ до РУ 10 кВ")
        self.assertEqual(data["OTKUDASTROIT_10kV"], "от опоры ВЛ 10 кВ до РУ 10 кВ")
        self.assertEqual(
            f"{data['OTKUDASTROIT_10kV']} {data['PS_NAME']}",
            "от опоры ВЛ 10 кВ до РУ 10 кВ ПС Романово",
        )
        self.assertEqual(warnings, [])

    def test_sech_70_from_50_to_100(self) -> None:
        text = (
            "10.1.1.1. От опоры ВЛ 10 кВ Романово по п. 10.2.2 до РУ 10 кВ проектируемой ТП 10/0,4 кВ "
            "смонтировать одноцепную ВЛЗ 10 кВ сечением от 50 мм² до 100 мм².\n"
            "10.1.2. Строительство новых подстанций: смонтировать ТП 10/0,4 кВ "
            "с силовым трансформатором мощностью 250 кВА киоскового типа.\n"
            "базовая подстанция 110-35 кВ: ПС 35/10 кВ Романово,"
        )
        tu_path = Path("output/test_tu_10kv_sech70.txt")
        tu_path.parent.mkdir(parents=True, exist_ok=True)
        tu_path.write_text(text, encoding="utf-8")

        from unittest.mock import patch

        with patch("backend.core.tu_parser_10kv.read_tu_text", return_value=text):
            data, warnings = enrich_tu_data_10kv(tu_path, {})
        self.assertEqual(data["SECH_KABEL_10kV"], "1х70")
        self.assertEqual(data["6-10"], "10/0,4")
        self.assertEqual(data["MOSH"], "250")
        self.assertEqual(data["OTKUDASTROIT_10kV"], "от опоры ВЛ 10 кВ до РУ 10 кВ")
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
