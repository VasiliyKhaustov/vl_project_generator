from __future__ import annotations

import errno
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


def clear_macos_extended_attributes(path: Path) -> None:
    """Снимает quarantine и прочие xattr — иначе AutoCAD Mac может не открыть DWG."""
    if platform.system() != "Darwin":
        return
    try:
        subprocess.run(
            ["xattr", "-cr", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return


def copy_file_with_retry(
    source: Path,
    destination: Path,
    *,
    retries: int = 5,
    logger: Any | None = None,
    clear_macos_xattr: bool = False,
) -> None:
    last_error: OSError | None = None
    for attempt in range(1, retries + 1):
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            if clear_macos_xattr:
                clear_macos_extended_attributes(destination)
            return
        except OSError as exc:
            last_error = exc
            if exc.errno != errno.EINTR or attempt == retries:
                raise
            if logger:
                logger.warning(
                    f"Повтор копирования файла ({attempt}/{retries}): "
                    f"{source.name} -> {destination.name}"
                )
            time.sleep(0.15 * attempt)
    if last_error is not None:
        raise last_error
