from __future__ import annotations

import errno
import shutil
import time
from pathlib import Path
from typing import Any


def copy_file_with_retry(
    source: Path,
    destination: Path,
    *,
    retries: int = 5,
    logger: Any | None = None,
) -> None:
    last_error: OSError | None = None
    for attempt in range(1, retries + 1):
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
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
