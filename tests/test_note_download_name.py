from __future__ import annotations

import unittest

from backend.core.output_manager import note_download_filename


class NoteDownloadNameTests(unittest.TestCase):
    def test_project_number_becomes_note_filename(self) -> None:
        name = note_download_filename("ПСД/48/2026/001", ".dwg")
        self.assertEqual(name, "ПСД／48／2026／001-Записка.dwg")
        self.assertNotIn("/", name)
        self.assertNotIn("note_result", name)

    def test_extension_and_empty_number(self) -> None:
        self.assertTrue(note_download_filename("ПСД/48/2026/001", "dxf").endswith(".dxf"))
        self.assertEqual(note_download_filename("", ".dwg"), "note_result-Записка.dwg")
