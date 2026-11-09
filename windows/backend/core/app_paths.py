"""Каталог данных программы: один и тот же смысл на macOS, Windows и Linux."""

from __future__ import annotations

import os
import platform
from pathlib import Path


def app_data_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = Path(base) / "PRO-VL"
    elif system == "Darwin":
        path = Path.home() / "Library" / "Application Support" / "PRO-VL"
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        path = Path(base) / "PRO-VL"
    path.mkdir(parents=True, exist_ok=True)
    return path
