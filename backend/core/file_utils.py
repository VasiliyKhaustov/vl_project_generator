from __future__ import annotations

import errno
import platform
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

_TRANSIENT_COPY_ERRNOS = {
    errno.EINTR,
    errno.ETIMEDOUT,
    errno.EAGAIN,
    getattr(errno, "EWOULDBLOCK", errno.EAGAIN),
    getattr(errno, "ECANCELED", 89),
}


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


def local_scratch_dir(namespace: str) -> Path:
    """Рабочая папка вне iCloud Desktop: иначе copy/ODA зависают с ETIMEDOUT."""
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in namespace)[:80]
    path = Path(tempfile.gettempdir()) / "vl_project_generator" / (safe or "scratch")
    path.mkdir(parents=True, exist_ok=True)
    return path


def copy_file_with_retry(
    source: Path,
    destination: Path,
    *,
    retries: int = 2,
    logger: Any | None = None,
    clear_macos_xattr: bool = False,
    timeout_s: float = 20.0,
) -> None:
    last_error: BaseException | None = None
    for attempt in range(1, retries + 1):
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            _copy_bytes(source, destination, timeout_s=timeout_s)
            if clear_macos_xattr:
                clear_macos_extended_attributes(destination)
            return
        except (OSError, subprocess.TimeoutExpired) as exc:
            last_error = exc
            if _copy_git_blob(source, destination, logger=logger):
                if clear_macos_xattr:
                    clear_macos_extended_attributes(destination)
                return
            errno_code = getattr(exc, "errno", None)
            transient = isinstance(exc, subprocess.TimeoutExpired) or errno_code in _TRANSIENT_COPY_ERRNOS
            if not transient or attempt == retries:
                raise OSError(
                    errno.ETIMEDOUT,
                    f"Не удалось скопировать {source} -> {destination}: {exc}",
                ) from exc
            if logger:
                logger.warning(
                    f"Повтор копирования файла ({attempt}/{retries}): "
                    f"{source.name} -> {destination.name} ({exc})"
                )
            time.sleep(0.3 * attempt)
    if last_error is not None:
        raise last_error


def _copy_bytes(source: Path, destination: Path, *, timeout_s: float) -> None:
    if platform.system() == "Darwin":
        process = subprocess.Popen(
            ["/bin/cp", "-f", str(source), str(destination)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _stdout, stderr = process.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                import os

                try:
                    os.kill(process.pid, signal.SIGKILL)
                except OSError:
                    pass
            raise exc
        if process.returncode == 0:
            return
        raise OSError(errno.EIO, (stderr or "").strip() or "cp failed")
    shutil.copy2(source, destination)


def _git_root(path: Path) -> Path | None:
    current = path.resolve().parent
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def _copy_git_blob(source: Path, destination: Path, logger: Any | None = None) -> bool:
    """Если рабочая копия файла зависла (iCloud), берём содержимое из git."""
    root = _git_root(source)
    if root is None:
        return False
    try:
        relative = source.resolve().relative_to(root)
    except ValueError:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = destination.with_name(destination.name + ".gitblob")
    try:
        with tmp_path.open("wb") as handle:
            completed = subprocess.run(
                ["git", "-C", str(root), "show", f"HEAD:{relative.as_posix()}"],
                stdout=handle,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
            )
        if completed.returncode != 0 or not tmp_path.exists() or tmp_path.stat().st_size == 0:
            tmp_path.unlink(missing_ok=True)
            return False
        tmp_path.replace(destination)
        if logger:
            logger.warning(
                f"Файл {source.name} не читается с диска, взял копию из git."
            )
        return True
    except (OSError, subprocess.TimeoutExpired):
        tmp_path.unlink(missing_ok=True)
        return False
