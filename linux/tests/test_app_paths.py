from __future__ import annotations

import platform
import unittest
from pathlib import Path

from backend.core.app_paths import app_data_dir


class AppPathsTests(unittest.TestCase):
    def test_data_dir_matches_current_os(self) -> None:
        path = app_data_dir()
        system = platform.system()
        if system == "Darwin":
            self.assertEqual(path, Path.home() / "Library" / "Application Support" / "PRO-VL")
        elif system == "Windows":
            self.assertEqual(path.name, "PRO-VL")
            self.assertIn("AppData", str(path))
        else:
            self.assertEqual(path, Path.home() / ".local" / "share" / "PRO-VL")
        self.assertTrue(path.is_dir())
