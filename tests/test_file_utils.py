import errno
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.core.file_utils import copy_file_with_retry


def test_copy_file_with_retry_recovers_from_eintr(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    destination = tmp_path / "dest.txt"
    source.write_text("payload", encoding="utf-8")

    original_copy = __import__("shutil").copy2
    calls = {"count": 0}

    def flaky_copy(src, dst):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError(errno.EINTR, "Interrupted system call")
        return original_copy(src, dst)

    with patch("backend.core.file_utils.shutil.copy2", side_effect=flaky_copy):
        copy_file_with_retry(source, destination, retries=3)

    assert destination.read_text(encoding="utf-8") == "payload"
    assert calls["count"] == 2
