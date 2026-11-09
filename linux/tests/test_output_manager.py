import tempfile
import unittest
from pathlib import Path

from backend.core.output_manager import OutputManager


class OutputManagerArchiveTests(unittest.TestCase):
    def test_project_archive_dir_uses_flat_project_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = OutputManager(root)
            archive_dir = output.project_archive_dir("ПСД/48/2026/141")

            self.assertEqual(
                archive_dir,
                root / "output" / "VsePro" / "ПСД_48_2026_141",
            )
            self.assertTrue(archive_dir.exists())

    def test_project_archive_dir_supports_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = OutputManager(root)
            archive_dir = output.project_archive_dir("ПСД/48/2026/111-КОМ")

            self.assertEqual(archive_dir.name, "ПСД_48_2026_111-КОМ")

    def test_save_upload_to_project_archive_keeps_original_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = OutputManager(root)
            saved = output.save_upload_to_project_archive(
                "ПСД/48/2026/052",
                "tu.docx",
                b"test-content",
            )

            self.assertEqual(saved.name, "tu.docx")
            self.assertEqual(saved.read_bytes(), b"test-content")


if __name__ == "__main__":
    unittest.main()
