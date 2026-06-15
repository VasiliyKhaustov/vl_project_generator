from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .logger import RunLogger


class OutputManager:
    PROJECT_ARCHIVE_ROOT = "VsePro"

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.output_root = project_root / "output" / "result"
        self.data_dir = self.output_root / "data"
        self.dwg_dir = self.output_root / "dwg"
        self.pdf_dir = self.output_root / "pdf"
        self.temp_dir = self.output_root / "temp"
        self.uploads_dir = self.output_root / "uploads"
        self.logs_dir = self.output_root / "logs"
        self.archive_root = project_root / "output" / self.PROJECT_ARCHIVE_ROOT

    def prepare(self) -> None:
        for directory in (
            self.data_dir,
            self.dwg_dir,
            self.pdf_dir,
            self.temp_dir,
            self.uploads_dir,
            self.logs_dir,
            self.archive_root,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def project_archive_dir(self, project_number: str) -> Path:
        folder_name = _project_archive_folder_name(project_number)
        target = self.archive_root / folder_name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def save_upload_to_project_archive(
        self,
        project_number: str,
        filename: str,
        content: bytes,
    ) -> Path:
        safe_name = _sanitize_upload_filename(filename)
        target = self.project_archive_dir(project_number) / safe_name
        target.write_bytes(content)
        return target

    def archive_generated_files(
        self,
        project_number: str,
        *,
        note_path: Path | None = None,
        final_pdf_path: Path | None = None,
    ) -> Path:
        archive_dir = self.project_archive_dir(project_number)
        if note_path is not None and note_path.exists():
            shutil.copy2(note_path, archive_dir / "note_result.dwg")
        if final_pdf_path is not None and final_pdf_path.exists():
            shutil.copy2(final_pdf_path, archive_dir / "final_project.pdf")
        return archive_dir

    def logger(self) -> RunLogger:
        return RunLogger(self.logs_dir / "log.txt")

    def write_json(self, name: str, data: dict[str, Any]) -> Path:
        path = self.data_dir / name
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def save_upload_bytes(self, filename: str, content: bytes, output_name: str) -> Path:
        extension = Path(filename).suffix.lower()
        target = self.uploads_dir / f"{output_name}{extension}"
        target.write_bytes(content)
        return target

    def copy_template_note(self) -> Path:
        source = self.project_root / "examples" / "templates" / "template_note.dwg"
        if not source.exists():
            raise FileNotFoundError("Не найден examples/templates/template_note.dwg")

        target = self.dwg_dir / "note_result.dwg"
        shutil.copy2(source, target)
        return target


def _sanitize_upload_filename(filename: str) -> str:
    safe_name = Path(filename).name.strip()
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError(f"Некорректное имя файла: {filename!r}")
    return safe_name


def _project_archive_folder_name(project_number: str) -> str:
    folder_name = project_number.strip().replace("/", "_")
    if not folder_name:
        raise ValueError("Номер проекта не может быть пустым.")
    return folder_name
