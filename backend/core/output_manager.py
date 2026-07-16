from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .logger import RunLogger


class OutputManager:
    PROJECT_ARCHIVE_ROOT = "VsePro"
    SESSIONS_ROOT = "sessions"

    def __init__(self, project_root: Path, *, run_id: str | None = None) -> None:
        self.project_root = project_root
        self.run_id = (run_id or "").strip() or None
        if self.run_id:
            self.output_root = (
                project_root / "output" / self.SESSIONS_ROOT / self.run_id
            )
        else:
            self.output_root = project_root / "output" / "result"
        self.data_dir = self.output_root / "data"
        self.dwg_dir = self.output_root / "dwg"
        self.pdf_dir = self.output_root / "pdf"
        self.temp_dir = self.output_root / "temp"
        self.uploads_dir = self.output_root / "uploads"
        self.logs_dir = self.output_root / "logs"
        self.archive_root = project_root / "output" / self.PROJECT_ARCHIVE_ROOT

    @classmethod
    def for_run(cls, project_root: Path, run_id: str) -> "OutputManager":
        return cls(project_root, run_id=run_id)

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
            archive_name = "note_result.dxf" if note_path.suffix.lower() == ".dxf" else "note_result.dwg"
            shutil.copy2(note_path, archive_dir / archive_name)
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

    def cleanup_stale_10kv_artifacts(self) -> list[Path]:
        removed: list[Path] = []
        stale_names = (
            "note_template.dwg",
            "apply_10kv_replacements.lsp",
            "apply_10kv_replacements.scr",
            "apply_10kv_result.txt",
            "replace_10kv.lsp",
            "replace_10kv.scr",
            "replace_10kv_result.txt",
            "КАК_ОТКРЫТЬ_В_AUTOCAD.txt",
            "note_result.dxf",
            "note_result_filled.dxf",
            "note_result_ACAD2000.dwg",
            "save_strict_dxf_as_dwg.scr",
        )
        for name in stale_names:
            path = self.dwg_dir / name
            if path.exists():
                path.unlink()
                removed.append(path)
        for path in self.dwg_dir.glob("*.dxf"):
            path.unlink()
            removed.append(path)
        note_result = self.dwg_dir / "note_result.dwg"
        note_size = note_result.stat().st_size if note_result.exists() else 3_100_000
        for path in self.dwg_dir.glob("*.dwg"):
            if path.name == "note_result.dwg":
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size < note_size - 100_000:
                path.unlink()
                removed.append(path)
            elif path.name.endswith("_записка_10кВ.dwg") and note_result.exists() and size != note_size:
                path.unlink()
                removed.append(path)
        for path in self.dwg_dir.glob("*_шаблон_10кВ.dwg"):
            path.unlink()
            removed.append(path)
        for path in self.dwg_dir.glob("*_apply_10кВ.lsp"):
            path.unlink()
            removed.append(path)
        return removed

    def copy_note_result_for_project(self, project_number: str) -> dict[str, Path | None]:
        display_name = project_number.strip().replace("/", "-")
        result: dict[str, Path | None] = {
            "filled_dwg": None,
            "filled_dxf": None,
        }
        dwg_source = self.dwg_dir / "note_result.dwg"
        if dwg_source.exists():
            result["filled_dwg"] = self.dwg_dir / f"{display_name}_записка_10кВ.dwg"
            shutil.copy2(dwg_source, result["filled_dwg"])
        dxf_source = self.dwg_dir / "note_result.dxf"
        if dxf_source.exists():
            result["filled_dxf"] = self.dwg_dir / f"{display_name}_записка_10кВ.dxf"
            shutil.copy2(dxf_source, result["filled_dxf"])
        return result

    def cleanup_stale_10kv_broken_dwgs(self) -> list[Path]:
        removed: list[Path] = []
        for path in self.dwg_dir.glob("*_записка_10кВ.dwg"):
            try:
                if path.stat().st_size < 3_100_000:
                    path.unlink()
                    removed.append(path)
            except OSError:
                continue
        return removed

    def write_10kv_autocad_instructions(self, project_number: str) -> Path:
        path = self.dwg_dir / "КАК_ОТКРЫТЬ_В_AUTOCAD.txt"
        display_name = project_number.strip().replace("/", "-")
        text = f"""Проект 10 кВ: {project_number}

=== СПОСОБ 1 (рекомендуется на Mac) ===
  1. Откройте: note_result_filled.dxf
     (все placeholders уже подставлены)
  2. Если AutoCAD спросит про отсутствующий файл — нажмите OK
  3. Файл → Сохранить как → DWG → note_result.dwg

=== СПОСОБ 2 (native-шаблон + LISP) ===
  1. Откройте: note_result.dwg (≈3.2 МБ)
  2. APPLOAD → apply_10kv_replacements.lsp
  3. APPLY10KVREPLACEMENTS
  4. Ctrl+S

НЕ открывайте .scr файлы.

Копия:
  {display_name}_записка_10кВ.dwg
"""
        path.write_text(text, encoding="utf-8")
        return path


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
