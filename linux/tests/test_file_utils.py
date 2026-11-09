import errno
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.core.file_utils import copy_file_with_retry


class FileUtilsTests(unittest.TestCase):
    def test_copy_file_with_retry_recovers_from_eintr(self) -> None:
        source = Path(self._tmp()) / "source.txt"
        destination = Path(self._tmp()) / "dest.txt"
        source.write_text("payload", encoding="utf-8")

        original_copy = __import__("shutil").copy2
        calls = {"count": 0}

        def flaky_copy(src, dst, timeout_s=45.0):
            calls["count"] += 1
            if calls["count"] == 1:
                raise OSError(errno.EINTR, "Interrupted system call")
            return original_copy(src, dst)

        with patch("backend.core.file_utils._copy_bytes", side_effect=flaky_copy):
            copy_file_with_retry(source, destination, retries=3)

        self.assertEqual(destination.read_text(encoding="utf-8"), "payload")
        self.assertEqual(calls["count"], 2)

    def test_copy_file_with_retry_recovers_from_etimedout(self) -> None:
        source = Path(self._tmp()) / "source.txt"
        destination = Path(self._tmp()) / "dest.txt"
        source.write_text("payload", encoding="utf-8")
        original_copy = __import__("shutil").copy2
        calls = {"count": 0}

        def flaky_copy(src, dst, timeout_s=45.0):
            calls["count"] += 1
            if calls["count"] == 1:
                raise OSError(errno.ETIMEDOUT, "Operation timed out")
            return original_copy(src, dst)

        with patch("backend.core.file_utils._copy_bytes", side_effect=flaky_copy):
            copy_file_with_retry(source, destination, retries=3)

        self.assertEqual(destination.read_text(encoding="utf-8"), "payload")

    def test_copy_falls_back_to_git_blob(self) -> None:
        source = Path("examples/templates/template_note_komapparat_A23_YA23.dwg")
        if not source.exists():
            self.skipTest("template is missing")
        import tempfile

        destination = Path(tempfile.mkdtemp()) / "from_git.dwg"

        def fail_copy(src, dst, timeout_s=20.0):
            raise OSError(errno.ETIMEDOUT, "Operation timed out")

        with patch("backend.core.file_utils._copy_bytes", side_effect=fail_copy):
            copy_file_with_retry(source, destination, retries=1)

        self.assertGreater(destination.stat().st_size, 1000)

    def _tmp(self) -> str:
        import tempfile

        return tempfile.mkdtemp()
