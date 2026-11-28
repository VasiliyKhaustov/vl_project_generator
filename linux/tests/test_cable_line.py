import unittest
from pathlib import Path

from backend.core.ai_engineer_handbook import local_chat_reply
from backend.core.cable_line import is_cable_line_project, sech_kl_from_tu, tu_requires_vl_04
from backend.core.calculator_kl import calculate_materials_kl
from backend.core.template_selector_kl import select_template_note_path_kl


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "examples" / "templates"


class CableLineDetectionTests(unittest.TestCase):
    def test_overhead_cable_section_is_not_a_cable_line(self):
        text = "Смонтировать ВЛИ 0,4 кВ проводом СИП сечением кабеля до 50 мм2."
        self.assertFalse(is_cable_line_project(text))

    def test_standard_clause_does_not_make_overhead_line_a_cable_project(self):
        text = (
            "От опоры № 19 ВЛ 0,4 кВ фидера № 1 построить одноцепную ВЛИ 0,4 кВ "
            "на железобетонных опорах изолированным проводом. "
            "13.2.1. строительство воздушной и (или) кабельной линии электропередачи "
            "взамен ликвидируемой, подвеска дополнительных проводов, "
            "замена воздушной линии кабельной, замена проводов на участках линии."
        )
        self.assertFalse(is_cable_line_project(text))

    def test_explicit_cable_line_with_overhead(self):
        text = (
            "Смонтировать кабельную линию 0,4 кВ и построить ВЛ 0,4 кВ "
            "от РУ-0,4 кВ ТП №103/180 кВА до опоры №1. "
            "Кабелем сечением до 50 мм2."
        )
        self.assertTrue(is_cable_line_project(text))
        self.assertTrue(tu_requires_vl_04(text))
        self.assertEqual(sech_kl_from_tu(text), "4х50")

    def test_cable_line_without_overhead(self):
        text = "Смонтировать кабельную линию в траншее кабелем сечением от 50 до 70 мм2."
        self.assertTrue(is_cable_line_project(text))
        self.assertFalse(tu_requires_vl_04(text))
        self.assertEqual(sech_kl_from_tu(text), "4х70")

    def test_range_50_to_100_is_4x70_even_in_a_long_sentence(self):
        text = (
            "Построить КЛ 0,4 кВ в траншее в многожильном исполнении с резиновой или "
            "пластмассовой изоляцией сечением кабеля от 50 до 100 мм2 с одним кабелем в траншее."
        )
        self.assertTrue(is_cable_line_project(text))
        self.assertFalse(tu_requires_vl_04(text))
        self.assertEqual(sech_kl_from_tu(text), "4х70")
        ocr = (
            "ТП № 083/400 кВА построить КЛ 0,4 кВ в траншее в многожильном исполнении "
            "с резиновой или пластмас- совой изоляцией сечением кабеля от 50 до 100 мм? "
            "с одним кабелем в траншее. "
            "Строительство воздушной и (или) кабельной линии электропередачи взамен ликвидируемой."
        )
        self.assertFalse(tu_requires_vl_04(ocr))
        self.assertEqual(sech_kl_from_tu(ocr), "4х70")

    def test_pure_kl_hides_overhead_plan_warnings(self):
        from backend.core.cable_line import is_vl04_plan_noise

        self.assertTrue(is_vl04_plan_noise("Полилиния 0,4 кВ не найдена: в слое или в имени нет Электрика_04."))
        self.assertTrue(is_vl04_plan_noise("Заземления найдены в служебных ESMT-данных DXF: 1."))
        self.assertFalse(
            is_vl04_plan_noise("Полилиния кабельной линии не найдена: в слое или в имени нет Электрика_КЛ.")
        )


class CableLineFormulaTests(unittest.TestCase):
    def test_trench_46_meters_and_mass_for_4x50(self):
        materials = calculate_materials_kl(
            {"SECH_KL": "4х50", "POWER_KW": 15, "OTK_STR_KL": ""},
            {"line_length_kl_m": 46, "supports": {}},
            requires_vl_04=False,
        )
        self.assertEqual(materials["DL_KL"], 46)
        self.assertEqual(materials["DL_OB"], 66)
        self.assertAlmostEqual(materials["DL_KL_KM"], 0.066)
        self.assertAlmostEqual(materials["RYT_TR"], 8.28)
        self.assertAlmostEqual(materials["ZAS_OG"], 5.52)
        self.assertAlmostEqual(materials["ZAS_P"], 2.76)
        self.assertEqual(materials["PZK"], 96)
        self.assertEqual(materials["TR"], 3)
        self.assertEqual(materials["MFT"], 17)
        self.assertEqual(materials["YPKL"], 34)
        self.assertAlmostEqual(materials["MASSA"], 0.066 * 1.045 * 1408)

    def test_support_total_does_not_include_a23(self):
        materials = calculate_materials_kl(
            {"SECH_KL": "4х70", "POWER_KW": 15},
            {"line_length_kl_m": 10, "supports": {"P23": 2, "A23": 1, "YA23": 1, "K21": 1}},
            requires_vl_04=True,
        )
        self.assertEqual(materials["S"], 4)
        self.assertEqual(materials["P72"], 4)
        self.assertEqual(materials["E778"], 8)
        self.assertEqual(materials["MASSA"], materials["KM_KG"] * 1776)


class CableLineTemplateTests(unittest.TestCase):
    def test_switch_and_p23_k21(self):
        path, _ = select_template_note_path_kl(
            TEMPLATES,
            {"requires_komapparat_template": True},
            {"supports": {"P23": 2, "K21": 1}, "plan_has_pzk": False},
            requires_vl_04=True,
        )
        self.assertIn("коммутацион", path.name.casefold())
        self.assertIn("П23 и К21", path.name)
        self.assertNotIn("ПЗК", path.name)

    def test_all_supports_without_switch(self):
        path, _ = select_template_note_path_kl(
            TEMPLATES,
            {"requires_komapparat_template": False},
            {"supports": {"P23": 1, "A23": 1, "YA23": 1, "K21": 1}, "plan_has_pzk": False},
            requires_vl_04=True,
        )
        self.assertTrue(path.name.startswith("КЛ и ВЛ опоры П23 и А23 и УА23 и К21"))
        self.assertNotIn("коммутацион", path.name.casefold())

    def test_pzk_uses_pzk_and_joint_family(self):
        path, _ = select_template_note_path_kl(
            TEMPLATES,
            {"requires_komapparat_template": False},
            {"supports": {"P23": 1}, "plan_has_pzk": True},
            requires_vl_04=True,
        )
        self.assertTrue(path.name.startswith("КЛ (ПЗК и СМ)"))
        self.assertIn("опора П23", path.name)

    def test_no_overhead_uses_cable_only_example(self):
        path, _ = select_template_note_path_kl(
            TEMPLATES,
            {},
            {"supports": {"P23": 4}, "plan_has_pzk": True},
            requires_vl_04=False,
        )
        self.assertEqual(path.name, "Кабельная линия пример с ПЗК и соединительными муфтами.dwg")


class CableLineChatTests(unittest.TestCase):
    def test_chat_explains_trench_and_mass(self):
        reply = local_chat_reply("какая масса кабеля на КЛ если 4х50")
        self.assertIn("1408", reply)
        self.assertIn("Электрика_КЛ", local_chat_reply("на каком слое полилиния кабельной линии"))

    def test_chat_keeps_ordinary_vl_answer(self):
        reply = local_chat_reply("сколько F207 на А23")
        self.assertIn("F207", reply)
        self.assertNotIn("Электрика_КЛ", reply)

    def test_chat_uses_this_project_numbers(self):
        reply = local_chat_reply(
            "какая длина траншеи КЛ",
            {"план_кл": {"длина_траншеи_м": 46, "на_плане_есть_пзк": True}},
            has_project=True,
        )
        self.assertIn("46", reply)
        self.assertIn("ПЗК", reply)


if __name__ == "__main__":
    unittest.main()
