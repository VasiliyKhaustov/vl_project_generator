"""Ответы AI Engineer по типовым альбомам, без подмены расчёта записки."""

import unittest

from backend.core.ai_engineer_handbook import local_chat_reply


class TypicalAlbumChatTests(unittest.TestCase):
    def test_cable_comes_from_a5_92_not_from_guess(self):
        reply = local_chat_reply("какой кабель проложить в траншее")
        self.assertIn("А5-92", reply)
        self.assertIn("0,7", reply)
        self.assertIn("ТУ", reply)
        self.assertIn("не назначает", reply)

    def test_covered_10kv_wire_is_sip3(self):
        reply = local_chat_reply("какой провод по шифру 27.0002")
        self.assertIn("27.0002", reply)
        self.assertIn("СИП-3", reply)
        self.assertIn("50, 70, 95 или 120", reply)

    def test_span_250017_uses_table(self):
        reply = local_chat_reply("какой пролёт по 25.0017 для СИП-2 3х50")
        self.assertIn("25.0017", reply)
        self.assertIn("42/40/35/31", reply)

    def test_bare_span_uses_250038(self):
        reply = local_chat_reply("пролёт П10-1 по 25.0038 для АС50")
        self.assertIn("87/75/66/58", reply)
        self.assertIn("СВ105-5", reply)

    def test_project_section_is_quoted(self):
        reply = local_chat_reply(
            "какой кабель проложить",
            {"материалы_кл_по_этому_проекту": {"сечение кабеля КЛ": "4х50"}},
            has_project=True,
        )
        self.assertIn("4х50", reply)
        self.assertIn("А5-92", reply)

    def test_armature_question_stays_on_vl(self):
        reply = local_chat_reply("сколько F207 на А23")
        self.assertIn("F207", reply)
        self.assertNotIn("А5-92", reply)
        self.assertNotIn("27.0002", reply)

    def test_p23_burial_does_not_invent_a_depth(self):
        reply = local_chat_reply("какое заглубление у опоры П23 и нужен ли подкос")
        self.assertIn("25.0017", reply)
        self.assertIn("без подкоса", reply)
        self.assertIn("СВ95", reply)
        self.assertIn("не называю", reply)
        self.assertNotIn("2,0 м", reply)
        self.assertNotIn("2.0 м", reply)

    def test_sag_is_tension_not_one_number(self):
        reply = local_chat_reply("какой провис провода по типовым")
        self.assertIn("не задаёт одной стрелой", reply)
        self.assertIn("6,5 кН", reply)


if __name__ == "__main__":
    unittest.main()
