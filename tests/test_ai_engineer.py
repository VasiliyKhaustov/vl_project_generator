from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.core.ai_engineer import (
    load_ai_engineer_report,
    run_ai_engineer_review,
    save_ai_engineer_report,
)
from backend.core.plan_geometry_audit import expected_groundings_04kv, turn_angle_at_point


class AiEngineerTests(unittest.TestCase):
    def test_expected_groundings_every_100m(self) -> None:
        self.assertEqual(expected_groundings_04kv(100), 1)
        self.assertEqual(expected_groundings_04kv(101), 2)
        self.assertEqual(expected_groundings_04kv(300), 3)
        self.assertEqual(expected_groundings_04kv(250), 3)

    def test_grounding_spacing_recommendation_with_detail(self) -> None:
        report = run_ai_engineer_review(
            project_data={
                "project_number": "ПСД/48/2026/300",
                "project_type": "0.4kv",
                "tu_data": {"FAZE": "трехфазный"},
                "plan_data": {
                    "supports": {"P23": 3, "A23": 0, "YA23": 0, "K21": 1},
                    "line_length_m": 300,
                    "grounding_count": 2,
                },
                "materials_data": {"F207": 14},
            },
            replacement_map={
                "{{PROJNUMB}}": "ПСД/48/2026/300",
                "{{FAZE}}": "трехфазный",
                "{{SECH_KABEL}}": "3х70+1х70",
            },
            cad_result={"unresolved_placeholders": []},
            enable_llm=False,
            plan_path=None,
        )
        # Количество берётся из plan_data расчёта: 300 м → нужно 3, на плане 2.
        grounding = next(
            item for item in report["findings"] if item["id"] == "grounding_spacing_04"
        )
        self.assertIn("300", grounding["reason"])
        self.assertIn("2", grounding["title"])
        self.assertIn("3", grounding["title"])
        self.assertIn("в расчёте 2", grounding["title"])
        self.assertIn("100", grounding["detail"])
        self.assertEqual(grounding["action"], "Почему?")
        self.assertIn("шаге 100", grounding["why"])

    def test_missing_plan_is_not_false_ok(self) -> None:
        """Без DXF нельзя показывать «замечаний нет» / 99.9%."""
        report = run_ai_engineer_review(
            project_data={
                "project_number": "ПСД/48/2026/001",
                "project_type": "10kv",
                "tu_data": {},
                "plan_data": {
                    "supports": {"P23": 1, "A23": 1, "YA23": 0, "K21": 0},
                    "line_length_04kv_m": 52.5,
                    "grounding_count": 3,
                },
                "materials_data": {"F207": 10},
                "materials_10kv_data": {},
            },
            replacement_map={"{{PROJNUMB}}": "ПСД/48/2026/001", "{{SECH_KABEL}}": "3х70+1х70"},
            enable_llm=False,
            plan_path=None,
            cad_result={"unresolved_placeholders": []},
        )
        self.assertNotEqual(report["status"], "ok")
        self.assertTrue(
            any(item["id"] == "geometry_plan_unavailable" for item in report["findings"])
        )
        self.assertLess(report["score"], 99.0)

    def test_short_04_branch_does_not_undercount_groundings(self) -> None:
        """52 м 0,4 кВ и 3 заземления из расчёта — нормы хватает, ложного 'нужно 1' нет."""
        report = run_ai_engineer_review(
            project_data={
                "project_number": "ПСД/48/2026/777",
                "project_type": "10kv",
                "tu_data": {},
                "plan_data": {
                    "supports": {"P23": 1, "A23": 1, "YA23": 0, "K21": 0},
                    "supports_10kv": {"P20": 0, "A20": 0, "UA": 1, "UP": 0, "ARLK": 2},
                    "line_length_04kv_m": 52.5,
                    "line_length_10kv_m": 365.0,
                    "grounding_count": 3,
                },
                "materials_data": {"F207": 10},
                "materials_10kv_data": {},
            },
            replacement_map={"{{PROJNUMB}}": "ПСД/48/2026/777", "{{SECH_KABEL}}": "3х70+1х70"},
            enable_llm=False,
            plan_path=None,
        )
        self.assertFalse(any(item["id"] == "grounding_spacing_04" for item in report["findings"]))

    def test_off_route_support_uses_geometry_audit(self) -> None:
        report = run_ai_engineer_review(
            project_data={
                "project_number": "ПСД/48/2026/010",
                "project_type": "0.4kv",
                "tu_data": {},
                "plan_data": {
                    "supports": {"P23": 1, "A23": 0, "YA23": 0, "K21": 0},
                    "line_length_m": 120,
                    "grounding_count": 2,
                },
                "materials_data": {"F207": 8},
            },
            replacement_map={"{{PROJNUMB}}": "ПСД/48/2026/010", "{{SECH_KABEL}}": "3х70+1х70"},
            enable_llm=False,
            plan_path=None,
        )
        # Inject geometry via monkeypatch-style direct call path:
        from backend.core import ai_engineer as module

        findings = module._geometry_findings(
            {
                "line_length_m": 120,
                "grounding_count": 2,
            },
            {
                "available": True,
                "line_length_04_m": 120,
                "grounding_count": 2,
                "expected_groundings_04": 2,
                "supports_off_route": [
                    {
                        "support_type": "P23",
                        "number": "14",
                        "distance_m": 28.5,
                        "display_name": "опора П23 №14",
                    }
                ],
                "groundings_off_route": [
                    {"index": 1, "distance_m": 35.0, "label": "Заземление #1"}
                ],
                "route_available": True,
            },
            is_10kv=False,
        )
        titles = " ".join(item["title"] for item in findings)
        self.assertIn("не на полилинии 0,4 кВ", titles)
        self.assertIn("Заземление", titles)
        self.assertTrue(any("0,4" in item["detail"] for item in findings))
        self.assertTrue(any(item.get("action") == "Почему?" for item in findings))
        off_support = next(item for item in findings if item["id"].startswith("support_off_route"))
        self.assertIn("1 м", off_support["why"])
        self.assertIn("28.5 м", off_support["why"])

    def test_geometry_gaps_duplicates_and_missing(self) -> None:
        from backend.core import ai_engineer as module

        findings = module._geometry_findings(
            {
                "line_length_m": 140,
                "line_length_10kv_m": 200,
                "grounding_count": 2,
                "supports": {"P23": 2, "A23": 0, "YA23": 0, "K21": 0},
                "supports_10kv": {"P20": 2, "A20": 0, "UA": 0, "UP": 0, "ARLK": 0},
            },
            {
                "available": True,
                "line_length_04_m": 140,
                "line_length_10_m": 200,
                "grounding_count": 2,
                "expected_groundings_04": 2,
                "supports_off_route": [],
                "groundings_off_route": [],
                "supports_on_route": 4,
                "groundings_on_route": 2,
                "supports_04_count": 2,
                "supports_10_count": 2,
                "touch_tolerance_m": 1.0,
                "max_support_gap_04_m": 42,
                "max_support_gap_10_m": 70,
                "max_grounding_gap_m": 100,
                "support_gaps_04": [
                    {
                        "from_name": "опора П23 №1",
                        "to_name": "опора П23 №2",
                        "distance_m": 50.0,
                        "limit_m": 42,
                    }
                ],
                "support_gaps_10": [
                    {
                        "from_name": "опора П20 №3",
                        "to_name": "опора П20 №4",
                        "distance_m": 85.0,
                        "limit_m": 70,
                    }
                ],
                "grounding_gaps": [
                    {
                        "from_name": "Заземление #1",
                        "to_name": "Заземление #2",
                        "distance_m": 120.0,
                        "limit_m": 100,
                    }
                ],
                "duplicate_supports": [
                    {
                        "number": "17",
                        "count": 2,
                        "names": ["опора П23 №17", "опора П23 №17"],
                    }
                ],
                "route_available": True,
            },
            is_10kv=True,
        )
        titles = " ".join(item["title"] for item in findings)
        self.assertIn("Подозрительное расстояние между опорами 0,4 кВ", titles)
        self.assertIn("Подозрительное расстояние между опорами 10 кВ", titles)
        self.assertIn("Подозрительное расстояние между заземлениями", titles)
        self.assertIn("Дублирование объектов: опора №17", titles)
        gap_04 = next(item for item in findings if item["id"].startswith("gap_support_04"))
        self.assertIn("Допустимое расстояние для данной проверки — 42 м", gap_04["why"])
        self.assertEqual(gap_04["action"], "Почему?")
        self.assertEqual(gap_04["fix_action"], "Как решить?")
        self.assertIn("Уменьшите расстояние между опорами 0,4 кВ до 42 м", gap_04["how"])

    def test_support_gap_04_limit_is_42_m(self) -> None:
        from backend.core.plan_geometry_audit import MAX_SUPPORT_GAP_04_M, _consecutive_gaps

        self.assertEqual(MAX_SUPPORT_GAP_04_M, 42.0)
        self.assertEqual(
            _consecutive_gaps(
                [
                    {"display_name": "опора ПП23 №1", "station_m": 0},
                    {"display_name": "опора ПП23 №2", "station_m": 41.5},
                ],
                name_key="display_name",
                limit_m=MAX_SUPPORT_GAP_04_M,
            ),
            [],
        )
        over = _consecutive_gaps(
            [
                {"display_name": "опора ПП23 №1", "station_m": 0},
                {"display_name": "опора ПП23 №2", "station_m": 43.0},
            ],
            name_key="display_name",
            limit_m=MAX_SUPPORT_GAP_04_M,
        )
        self.assertEqual(len(over), 1)
        self.assertEqual(over[0]["limit_m"], 42.0)

    def test_support_number_sequence_along_route(self) -> None:
        from backend.core.plan_geometry_audit import _support_number_sequence
        from backend.core import ai_engineer as module

        ok_up = _support_number_sequence(
            [
                {"number": "№1", "station_m": 0, "display_name": "опора П23 №1"},
                {"number": "2", "station_m": 20, "display_name": "опора П23 №2"},
                {"number": "№3", "station_m": 40, "display_name": "опора А23 №3"},
            ],
            voltage="04",
        )
        self.assertIsNone(ok_up)
        ok_down = _support_number_sequence(
            [
                {"number": "5", "station_m": 0, "display_name": "опора П23 №5"},
                {"number": "4", "station_m": 25, "display_name": "опора П23 №4"},
                {"number": "3", "station_m": 50, "display_name": "опора П23 №3"},
            ],
            voltage="04",
        )
        self.assertIsNone(ok_down)
        broken = _support_number_sequence(
            [
                {"number": "№1", "station_m": 0, "display_name": "опора П23 №1"},
                {"number": "№4", "station_m": 25, "display_name": "опора П23 №4"},
                {"number": "№3", "station_m": 50, "display_name": "опора П23 №3"},
            ],
            voltage="04",
        )
        self.assertIsNotNone(broken)
        assert broken is not None
        self.assertEqual(broken["along"], "№1 → №4 → №3")
        self.assertEqual(broken["expected"], "№1 → №2 → №3")

        findings = module._geometry_findings(
            {"line_length_m": 80, "grounding_count": 2, "supports": {"P23": 3}},
            {
                "available": True,
                "line_length_04_m": 80,
                "supports_04_count": 3,
                "grounding_count": 2,
                "supports_off_route": [],
                "groundings_off_route": [],
                "number_sequence_issues": [broken],
                "duplicate_supports": [],
                "wrong_angle_supports": [],
                "support_gaps_04": [],
                "support_gaps_10": [],
                "grounding_gaps": [],
            },
            is_10kv=False,
        )
        seq = next(item for item in findings if str(item["id"]).startswith("support_number_sequence"))
        self.assertIn("не по порядку", seq["title"])
        self.assertIn("№1 → №4 → №3", seq["reason"])
        self.assertIn("№2", seq["how"])

        missing = module._geometry_findings(
            {"line_length_m": 80, "grounding_count": 0, "supports": {}},
            {
                "available": True,
                "line_length_04_m": 80,
                "supports_04_count": 0,
                "grounding_count": 0,
                "supports_off_route": [],
                "groundings_off_route": [],
                "max_grounding_gap_m": 100,
            },
            is_10kv=False,
        )
        missing_ids = {item["id"] for item in missing}
        self.assertIn("missing_supports_04", missing_ids)
        self.assertIn("missing_grounding", missing_ids)

    def test_no_generic_rlk_recommendation(self) -> None:
        report = run_ai_engineer_review(
            project_data={
                "project_number": "ПСД/48/2026/660",
                "project_type": "10kv",
                "branch_pole_type": "anchor",
                "tu_data": {"FAZE": "трехфазный", "SECH_KABEL": "3х70+1х70"},
                "plan_data": {
                    "supports": {"P23": 1, "A23": 1, "YA23": 0, "K21": 0},
                    "supports_10kv": {"P20": 0, "A20": 0, "UA": 1, "UP": 0, "ARLK": 2},
                    "line_length_10kv_m": 360.0,
                    "line_length_04kv_m": 52.0,
                    "grounding_count": 3,
                },
                "materials_data": {"F207": 10},
                "materials_10kv_data": {"SHF": 12},
            },
            replacement_map={
                "{{PROJNUMB}}": "ПСД/48/2026/660",
                "{{FAZE}}": "трехфазный",
                "{{SECH_KABEL}}": "3х70+1х70",
            },
            enable_llm=False,
        )
        titles = " ".join(item["title"] for item in report["findings"])
        self.assertNotIn("РЛК", titles)
        self.assertNotIn("УОП/УОК", titles)

    def test_turn_angle_on_polyline(self) -> None:
        straight = [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (20.0, 0.0, 0.0)]
        corner = [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 10.0, 0.0)]
        self.assertLess(turn_angle_at_point(straight, (10.0, 0.0)), 1.0)
        self.assertLess(turn_angle_at_point(corner, (5.0, 0.0)), 1.0)
        self.assertAlmostEqual(turn_angle_at_point(corner, (10.0, 0.0)), 90.0, delta=0.5)

    def test_wrong_support_type_for_polyline_angle(self) -> None:
        from backend.core import ai_engineer as module

        findings = module._geometry_findings(
            {
                "line_length_m": 40,
                "grounding_count": 1,
                "supports": {"P23": 1, "A23": 0, "YA23": 1, "K21": 0},
            },
            {
                "available": True,
                "line_length_04_m": 40,
                "grounding_count": 1,
                "supports_off_route": [],
                "groundings_off_route": [],
                "supports_04_count": 2,
                "wrong_angle_supports": [
                    {
                        "support_type": "P23",
                        "number": "5",
                        "display_name": "опора П23 №5",
                        "angle_deg": 42.0,
                        "allowed_max_deg": 8.0,
                        "suggested": "УА23* (поворот до 90°)",
                    },
                    {
                        "support_type": "YA23",
                        "number": "6",
                        "display_name": "опора УА23* №6",
                        "angle_deg": 120.0,
                        "allowed_max_deg": 90.0,
                        "suggested": "проверить геометрию трассы: угол больше 90°, УА23* не подходит",
                    },
                ],
                "route_available": True,
            },
            is_10kv=False,
        )
        titles = " ".join(item["title"] for item in findings)
        self.assertIn("Неверный тип опоры на угле трассы", titles)
        p23 = next(item for item in findings if item["id"].startswith("support_wrong_angle_P23"))
        self.assertIn("42", p23["why"])
        self.assertIn("УА23*", p23["how"])
        self.assertEqual(p23["fix_action"], "Как решить?")
        ya = next(item for item in findings if item["id"].startswith("support_wrong_angle_YA23"))
        self.assertIn("90", ya["why"])

    def test_save_and_load_report(self) -> None:
        report = run_ai_engineer_review(
            project_data={
                "project_number": "ПСД/48/2026/002",
                "project_type": "0.4kv",
                "tu_data": {},
                "plan_data": {
                    "supports": {"P23": 1, "A23": 0, "YA23": 0, "K21": 0},
                    "line_length_m": 50,
                    "grounding_count": 1,
                },
                "materials_data": {"F207": 8},
            },
            replacement_map={"{{PROJNUMB}}": "ПСД/48/2026/002", "{{SECH_KABEL}}": "3х70+1х70"},
            enable_llm=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            path = save_ai_engineer_report(data_dir, report)
            self.assertTrue(path.exists())
            loaded = load_ai_engineer_report(data_dir)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded["score"], report["score"])

    def test_chat_without_key_returns_error(self) -> None:
        import os
        from unittest.mock import patch

        from backend.core.ai_engineer import chat_with_project

        with patch.dict(os.environ, {"AI_ENGINEER_API_KEY": "", "OPENAI_API_KEY": ""}, clear=False):
            result = chat_with_project(
                message="сколько F207 на А23?",
                project_data={"project_number": "ПСД/48/2026/001", "project_type": "0.4kv"},
                replacement_map={"{{PROJNUMB}}": "ПСД/48/2026/001"},
                report={"summary": "нужно проверить", "findings": []},
            )
        self.assertTrue(result["ok"])
        self.assertIn("F207", result["reply"])
        self.assertEqual(result["model"], "rules")

    def test_chat_saves_history(self) -> None:
        from backend.core.ai_engineer import load_ai_engineer_chat, save_ai_engineer_chat

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            save_ai_engineer_chat(
                data_dir,
                [
                    {"role": "user", "content": "Как исправить?"},
                    {"role": "assistant", "content": "Поставьте опору на полилинию."},
                ],
            )
            loaded = load_ai_engineer_chat(data_dir)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[1]["content"], "Поставьте опору на полилинию.")

    def test_chat_handbook_uses_human_words(self) -> None:
        from backend.core.ai_engineer_handbook import (
            CHAT_KNOWLEDGE,
            chat_system_prompt,
            human_project_facts,
            sanitize_chat_reply,
        )

        self.assertIn("А23 — 2 шт", CHAT_KNOWLEDGE)
        self.assertIn("ТМ-63", CHAT_KNOWLEDGE)
        self.assertNotIn("{{F207}}", CHAT_KNOWLEDGE)
        cleaned = sanitize_chat_reply(
            r"На опору \(N_{A23}\) нужно \[ F207 = N_{\text{узлов}} \times q \] и {{F207}}."
        )
        self.assertNotIn("{{", cleaned)
        self.assertNotIn("\\text", cleaned)
        self.assertIn("монтажная лента F207", cleaned)
        facts = human_project_facts(
            project_data={
                "project_number": "ПСД/1",
                "project_type": "0.4kv",
                "plan_data": {"supports": {"A23": 3}, "line_length_m": 80},
                "materials_data": {"F207": 12, "A23": 3},
            },
            replacement_map={"{{A23}}": "3", "{{F207}}": "12"},
            report={"summary": "ок", "findings": []},
            cad_result={},
        )
        self.assertEqual(facts["тип_этого_проекта"], "0,4 кВ")
        self.assertEqual(facts["план_0_4"]["опор_А23"], 3)
        prompt = chat_system_prompt(facts)
        self.assertIn("коротко", prompt)
        self.assertIn("П20-3Н", prompt)
        self.assertNotIn("Запрещено:", prompt)
        general = chat_system_prompt({"статус": "проект ещё не сформирован"}, has_project=False)
        self.assertIn("ещё не сформирован", general)
        self.assertIn("Старт", general)

    def test_local_chat_answers_the_question(self) -> None:
        from backend.core.ai_engineer_handbook import local_chat_reply

        f207 = local_chat_reply("сколько F207 на А23?")
        self.assertIn("2 шт", f207)
        self.assertIn("А23", f207)
        self.assertNotIn("Запрещено", f207)
        self.assertNotIn("LaTeX", f207)

        pp23 = local_chat_reply("чем ПП23 отличается от П23?")
        self.assertIn("габарит", pp23.lower())
        self.assertIn("СВ110-5", pp23)

        findings = local_chat_reply(
            "что не так и как исправить?",
            {
                "замечания": [
                    {
                        "замечание": "Опора П23 №4 стоит на угле",
                        "почему": "промежуточная не работает на повороте",
                        "как_исправить": "замените блок на УА23*",
                    }
                ]
            },
            has_project=True,
        )
        self.assertIn("П23 №4", findings)
        self.assertIn("УА23*", findings)
        self.assertIn("Как исправить", findings)

        angle = local_chat_reply("какую мне опору поставить на угол 50 градусов")
        self.assertIn("УА23*", angle)
        self.assertIn("50", angle)
        self.assertNotIn("ОПОРЫ 0,4", angle)
        self.assertNotIn("слой PP23", angle)

        mixed = local_chat_reply("Привет я не знаю какую мне опору поставить на угол")
        self.assertIn("УА23*", mixed)
        self.assertNotIn("На связи", mixed)

        start = local_chat_reply("как начать делать план я первый день")
        self.assertIn("полилини", start)
        self.assertIn("П23", start)
        self.assertNotIn("Не совсем понял", start)

        dup_facts = {
            "дубли_опор": [
                {
                    "number": "17",
                    "count": 2,
                    "names": ["опора П23 №17", "опора П23 №17"],
                }
            ],
            "замечания": [
                {
                    "id": "duplicate_support_17_2",
                    "замечание": "Дублирование объектов: опора №17 встречается 2 раза",
                    "почему": "номер должен быть уникальным",
                    "как_исправить": "удалите или перенумеруйте дубликат",
                }
            ],
        }
        dup = local_chat_reply("Какая опора у меня продублирована?", dup_facts, has_project=True)
        self.assertIn("№17", dup)
        self.assertNotIn("Не совсем понял", dup)
        none = local_chat_reply(
            "У меня есть дублирование объектов каких?",
            {"дубли_опор": [], "замечания": []},
            has_project=True,
        )
        self.assertIn("дублей нет", none.lower())

    def test_llm_span_guess_dropped_when_gaps_ok(self) -> None:
        from backend.core.ai_engineer import _drop_llm_geometry_guesses

        kept = _drop_llm_geometry_guesses(
            [
                {
                    "source": "llm",
                    "title": "Две опоры на трассе 100 м образуют пролёт около 100 м",
                    "reason": "В плане указаны 2 опоры П23 при длине линии 100 м.",
                },
                {
                    "source": "llm",
                    "title": "Линия не отражена в line_length_04kv_m",
                    "reason": "поле пустое",
                },
                {"source": "rules", "title": "Оставить", "reason": "ok"},
            ],
            {"support_gaps_04": [], "support_gaps_10": []},
        )
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["title"], "Оставить")

    def test_llm_grounding_location_guess_dropped(self) -> None:
        from backend.core.ai_engineer import _drop_llm_geometry_guesses, _placement_notes

        kept = _drop_llm_geometry_guesses(
            [
                {
                    "source": "llm",
                    "title": "Два заземления не подтверждают нормативный шаг на трассе 112 м",
                    "reason": "Для линии 0,4 кВ длиной 112 м указано только 2 заземления, но их расположение не приведено.",
                }
            ],
            {
                "grounding_gaps": [],
                "groundings_on_route": 2,
                "grounding_positions": [
                    {"label": "Заземление 1", "station_m": 12, "on_route": True},
                    {"label": "Заземление 2", "station_m": 90, "on_route": True},
                ],
            },
        )
        self.assertEqual(kept, [])
        notes = _placement_notes(
            {
                "max_grounding_gap_m": 100,
                "grounding_positions": [
                    {"label": "Заземление 1", "station_m": 12, "on_route": True},
                    {"label": "Заземление 2", "station_m": 90, "on_route": True},
                ],
            }
        )
        self.assertTrue(notes)
        self.assertIn("12", notes[0])
        self.assertIn("90", notes[0])

    def test_grounding_end_gap_along_route(self) -> None:
        from backend.core.plan_geometry_audit import _gaps_along_route

        gaps = _gaps_along_route(
            [
                {"label": "Заземление 1", "station_m": 10},
                {"label": "Заземление 2", "station_m": 20},
            ],
            name_key="label",
            limit_m=100,
            route_length_m=130,
        )
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["from_name"], "Заземление 2")
        self.assertEqual(gaps[0]["to_name"], "конец трассы")
        self.assertGreater(gaps[0]["distance_m"], 100)

    def test_latest_plan_p23_on_polyline(self) -> None:
        from backend.core.plan_geometry_audit import audit_plan_geometry

        path = Path("output/sessions/79186cc16e9d40d881a96a5adcdd02af/temp/uploaded_plan_converted.dxf")
        if not path.exists():
            self.skipTest("latest uploaded plan is unavailable")
        audit = audit_plan_geometry(path)
        self.assertEqual(audit["supports_04_count"], 2)
        self.assertEqual(audit["supports_off_route"], [])
        self.assertEqual(audit["support_gaps_04"], [])
        distances = [item["distance_m"] for item in audit.get("supports_off_route") or []]
        self.assertEqual(distances, [])


if __name__ == "__main__":
    unittest.main()
