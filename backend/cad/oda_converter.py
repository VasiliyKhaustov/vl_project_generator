from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


class OdaConverterError(RuntimeError):
    pass


# ODA File Converter небезопасен при параллельных запусках на одной машине.
_ODA_LOCK = threading.Lock()


class OdaConverter:
    def __init__(self, project_root: Path, logger: Any | None = None) -> None:
        self.project_root = project_root
        self.logger = logger
        self.executable = self._find_executable()

    def convert_file(
        self,
        source_path: Path,
        output_path: Path,
        output_format: str,
        work_dir: Path,
        output_version: str = "ACAD2018",
    ) -> Path:
        with _ODA_LOCK:
            return self._convert_file_unlocked(
                source_path,
                output_path,
                output_format,
                work_dir,
                output_version=output_version,
            )

    def _convert_file_unlocked(
        self,
        source_path: Path,
        output_path: Path,
        output_format: str,
        work_dir: Path,
        output_version: str = "ACAD2018",
    ) -> Path:
        source_path = source_path.resolve()
        output_path = output_path.resolve()
        output_format = output_format.upper()

        if output_format not in {"DXF", "DWG"}:
            raise ValueError("ODA output_format должен быть DXF или DWG.")
        if not source_path.exists():
            raise FileNotFoundError(f"Не найден файл для конвертации: {source_path}")

        input_dir = work_dir / f"{source_path.stem}_in"
        output_dir = work_dir / f"{source_path.stem}_out"
        shutil.rmtree(input_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        input_copy = input_dir / f"{source_path.stem}{source_path.suffix.upper()}"
        shutil.copy2(source_path, input_copy)
        input_filter = f"*{source_path.suffix.upper()}"

        command = [
            str(self.executable),
            str(input_dir),
            str(output_dir),
            output_version,
            output_format,
            "0",
            "1",
            input_filter,
        ]
        self._log(f"ODA command: {' '.join(command)}")

        process = self._run_with_retry(command)
        if process.stdout.strip():
            self._log(f"ODA stdout: {process.stdout.strip()}")
        if process.stderr.strip():
            self._log(f"ODA stderr: {process.stderr.strip()}")
        if process.returncode != 0:
            raise OdaConverterError(
                f"ODA File Converter завершился с кодом {process.returncode}. {process.stderr or process.stdout}"
            )

        converted = self._find_converted_file(output_dir, source_path.stem, output_format)
        if not converted:
            raise OdaConverterError(
                f"ODA File Converter не создал файл {output_format} для {source_path.name}."
            )

        if output_path.exists():
            output_path.chmod(output_path.stat().st_mode | stat.S_IWUSR)
        shutil.copy2(converted, output_path)
        output_path.chmod(output_path.stat().st_mode | stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self._log(f"ODA converted: {source_path} -> {output_path}")
        return output_path

    def _run_with_retry(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        last_process: subprocess.CompletedProcess[str] | None = None
        for attempt in range(1, 4):
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=180,
            )
            last_process = process
            if process.returncode == 0:
                return process

            combined_output = f"{process.stderr}\n{process.stdout}"
            transient_macos_error = process.returncode == -6 or "PasteBoard: Error creating pasteboard" in combined_output
            if not transient_macos_error or attempt == 3:
                return process

            self._log(f"ODA transient macOS error, retry {attempt + 1}/3.")
            time.sleep(1)

        return last_process

    def _find_executable(self) -> Path:
        candidates: list[str] = []
        env_path = os.environ.get("ODA_FILE_CONVERTER")
        if env_path:
            candidates.append(env_path)

        path_candidate = shutil.which("ODAFileConverter")
        if path_candidate:
            candidates.append(path_candidate)

        settings = self._load_settings()
        system = platform.system()
        if system == "Darwin":
            candidates.extend(
                [
                    settings.get("oda", {}).get("mac_exec_path", ""),
                    "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
                ]
            )
        elif system == "Windows":
            candidates.extend(
                [
                    settings.get("oda", {}).get("windows_exec_path", ""),
                    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
                ]
            )

        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate).expanduser()
            if path.exists() and path.is_file():
                return path

        raise OdaConverterError(
            "ODA File Converter не найден. Установите ODA File Converter или укажите путь к нему в config/settings.json."
        )

    def _load_settings(self) -> dict[str, Any]:
        path = self.project_root / "config" / "settings.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise OdaConverterError(f"Некорректный config/settings.json: {exc}") from exc

    def _find_converted_file(self, directory: Path, source_stem: str, output_format: str) -> Path | None:
        suffix = f".{output_format.lower()}"
        files = [path for path in directory.iterdir() if path.suffix.lower() == suffix]
        for path in files:
            if path.stem.lower() == source_stem.lower():
                return path
        return files[0] if files else None

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger.info(message)
