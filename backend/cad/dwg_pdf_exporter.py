from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .oda_dwg_adapter import convert_dwg_to_dxf_with_oda
from ..core.pdf_exporter import render_dxf_to_pdf_faithful


class DwgPdfExportError(RuntimeError):
    pass


DEFAULT_QCAD_DWG2PDF_ARGS = (
    "-no-gui",
    "-no-dock-icon",
    "-f",
    "-a",
    "-auto-orientation",
)


def export_note_dwg_to_pdf(
    note_dwg_path: Path,
    output_pdf_path: Path,
    *,
    work_dir: Path,
    project_root: Path,
    logger: Any | None = None,
) -> dict[str, Any]:
    """Экспортирует готовую DWG-записку в PDF без изменения исходного DWG."""
    note_dwg_path = Path(note_dwg_path).resolve()
    output_pdf_path = Path(output_pdf_path).resolve()
    if not note_dwg_path.exists():
        raise DwgPdfExportError(f"DWG-записка не найдена: {note_dwg_path}")

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    external_method = _try_external_pdf_export(
        note_dwg_path,
        output_pdf_path,
        project_root=project_root,
        work_dir=work_dir,
        logger=logger,
    )
    if external_method is not None:
        return {
            "method": external_method,
            "faithful": True,
            "sourceDwg": str(note_dwg_path),
        }

    autocad_method = _try_autocad_accoreconsole_export(
        note_dwg_path,
        output_pdf_path,
        project_root=project_root,
        work_dir=work_dir,
        logger=logger,
    )
    if autocad_method is not None:
        return {
            "method": autocad_method,
            "faithful": True,
            "sourceDwg": str(note_dwg_path),
        }

    qcad_method = _try_qcad_dwg2pdf_export(
        note_dwg_path,
        output_pdf_path,
        project_root=project_root,
        work_dir=work_dir,
        logger=logger,
    )
    if qcad_method is not None:
        return {
            "method": qcad_method,
            "faithful": True,
            "sourceDwg": str(note_dwg_path),
        }

    if _allow_ezdxf_pdf_fallback():
        return _export_note_dwg_to_pdf_via_ezdxf_fallback(
            note_dwg_path,
            output_pdf_path,
            work_dir=work_dir,
            logger=logger,
        )

    raise DwgPdfExportError(
        "Не удалось сформировать PDF 1:1 из DWG. Установите QCAD "
        "(brew install --cask qcad) или задайте DWG_PDF_EXPORT_COMMAND "
        "в config/settings.json / переменных окружения."
    )


def _allow_ezdxf_pdf_fallback() -> bool:
    return os.environ.get("ALLOW_EZDXF_PDF_FALLBACK", "").strip().lower() in {"1", "true", "yes"}


def _export_note_dwg_to_pdf_via_ezdxf_fallback(
    note_dwg_path: Path,
    output_pdf_path: Path,
    *,
    work_dir: Path,
    logger: Any | None,
) -> dict[str, Any]:
    filled_dxf_path = _filled_dxf_for_pdf(work_dir)
    if filled_dxf_path is not None:
        render_dxf_to_pdf_faithful(filled_dxf_path, output_pdf_path)
        if logger:
            logger.warning(
                "PDF записки сформирован через ezdxf (не 1:1 с DWG): "
                f"{filled_dxf_path}"
            )
        return {
            "method": "filled_dxf_faithful_render",
            "faithful": False,
            "sourceDwg": str(note_dwg_path),
            "sourceDxf": str(filled_dxf_path),
        }

    dxf_path = work_dir / "temp" / f"{note_dwg_path.stem}_for_pdf.dxf"
    convert_dwg_to_dxf_with_oda(
        note_dwg_path,
        dxf_path,
        work_dir,
        logger=logger,
    )
    render_dxf_to_pdf_faithful(dxf_path, output_pdf_path)
    if logger:
        logger.warning(
            "PDF записки сформирован через ezdxf (не 1:1 с DWG): "
            f"{output_pdf_path}"
        )

    return {
        "method": "oda_dxf_faithful_render",
        "faithful": False,
        "sourceDwg": str(note_dwg_path),
        "sourceDxf": str(dxf_path),
    }


def _filled_dxf_for_pdf(work_dir: Path) -> Path | None:
    path = Path(work_dir).resolve() / "temp" / "filled_temp.dxf"
    return path if path.exists() else None


def _find_qcad_dwg2pdf_executable(project_root: Path) -> Path | None:
    settings = _load_pdf_export_settings(project_root)
    candidates = [
        os.environ.get("QCAD_DWG2PDF", "").strip(),
        str(settings.get("qcad_dwg2pdf_path", "")).strip(),
        "/Applications/QCAD-Pro.app/Contents/Resources/dwg2pdf",
        "/Applications/QCAD.app/Contents/Resources/dwg2pdf",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.is_file():
            return path

    which_path = shutil.which("dwg2pdf")
    if which_path:
        return Path(which_path)
    return None


def _qcad_dwg2pdf_args(project_root: Path) -> list[str]:
    settings = _load_pdf_export_settings(project_root)
    configured = settings.get("qcad_args", DEFAULT_QCAD_DWG2PDF_ARGS)
    if isinstance(configured, str):
        return shlex.split(configured)
    if isinstance(configured, list):
        return [str(item) for item in configured]
    return list(DEFAULT_QCAD_DWG2PDF_ARGS)


def _try_qcad_dwg2pdf_export(
    dwg_path: Path,
    pdf_path: Path,
    *,
    project_root: Path,
    work_dir: Path,
    logger: Any | None,
) -> str | None:
    executable = _find_qcad_dwg2pdf_executable(project_root)
    if executable is None:
        return None

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    args = [
        str(executable),
        *_qcad_dwg2pdf_args(project_root),
        "-o",
        str(pdf_path),
        str(dwg_path),
    ]

    if logger:
        logger.info(f"Экспорт PDF через QCAD dwg2pdf: {' '.join(args)}")

    process = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=600,
        cwd=str(work_dir),
    )
    if process.returncode != 0:
        details = (process.stderr or process.stdout or "").strip()
        if logger:
            logger.warning(f"QCAD dwg2pdf завершился с ошибкой: {details}")
        return None
    if not pdf_path.exists():
        if logger:
            logger.warning("QCAD dwg2pdf не создал PDF-файл.")
        return None
    return "qcad_dwg2pdf"


def _try_external_pdf_export(
    dwg_path: Path,
    pdf_path: Path,
    *,
    project_root: Path,
    work_dir: Path,
    logger: Any | None,
) -> str | None:
    settings = _load_pdf_export_settings(project_root)
    command_template = (
        os.environ.get("DWG_PDF_EXPORT_COMMAND", "").strip()
        or str(settings.get("external_command", "")).strip()
    )
    if not command_template:
        return None

    command = command_template.format(
        input=str(dwg_path),
        output=str(pdf_path),
        input_dwg=str(dwg_path),
        output_pdf=str(pdf_path),
    )
    args = shlex.split(command)
    if not args:
        return None

    if logger:
        logger.info(f"Экспорт PDF через внешнюю команду: {command}")

    process = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(work_dir),
    )
    if process.returncode != 0:
        details = (process.stderr or process.stdout or "").strip()
        raise DwgPdfExportError(
            f"Внешняя команда экспорта PDF завершилась с ошибкой: {details}"
        )
    if not pdf_path.exists():
        raise DwgPdfExportError("Внешняя команда экспорта PDF не создала выходной файл.")
    return "external_command"


def _try_autocad_accoreconsole_export(
    dwg_path: Path,
    pdf_path: Path,
    *,
    project_root: Path,
    work_dir: Path,
    logger: Any | None,
) -> str | None:
    if platform.system() != "Windows":
        return None

    settings = _load_pdf_export_settings(project_root)
    executable = (
        os.environ.get("AUTOCAD_ACCORECONSOLE", "").strip()
        or str(settings.get("autocad_accoreconsole_path", "")).strip()
        or shutil.which("accoreconsole.exe")
        or ""
    )
    if not executable:
        return None

    script_dir = work_dir / "temp" / "autocad_pdf_export"
    script_dir.mkdir(parents=True, exist_ok=True)
    script_path = script_dir / "export_note_pdf.scr"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        "\n".join(
            [
                "._EXPORTPDF",
                f'"{pdf_path}"',
                "_ALL",
                "",
                "._QUIT",
            ]
        ),
        encoding="utf-8",
    )

    if logger:
        logger.info(f"Экспорт PDF через AutoCAD Core Console: {executable}")

    process = subprocess.run(
        [
            executable,
            "/i",
            str(dwg_path),
            "/s",
            str(script_path),
            "/l",
            "ru-RU",
        ],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(script_dir),
    )
    if process.returncode != 0:
        details = (process.stderr or process.stdout or "").strip()
        if logger:
            logger.warning(f"AutoCAD Core Console PDF export failed: {details}")
        return None
    if not pdf_path.exists():
        if logger:
            logger.warning("AutoCAD Core Console не создал PDF-файл.")
        return None
    return "autocad_accoreconsole"


def _load_pdf_export_settings(project_root: Path) -> dict[str, Any]:
    path = project_root / "config" / "settings.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    pdf_export = payload.get("pdf_export")
    return pdf_export if isinstance(pdf_export, dict) else {}
