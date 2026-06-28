from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from backend.cad.dwg_pdf_exporter import export_note_dwg_to_pdf
from backend.cad.oda_converter import OdaConverterError
from backend.cad.oda_dwg_adapter import (
    convert_dwg_plan_to_dxf_with_oda,
    replace_placeholders_in_dwg_with_oda,
)
from backend.core.calculator import calculate_materials
from backend.core.delivery_distance import DeliveryDistanceError, calculate_delivery_distance_from_tu
from backend.core.dxf_reader import analyze_dxf
from backend.core.output_manager import OutputManager
from backend.core.pdf_exporter import merge_project_pdfs, render_dxf_to_pdf, render_tu_docx_to_pdf
from backend.core.replacement_builder import build_replacement_map
from backend.core.template_selector import select_template_note_path, template_placeholder_warning
from backend.core.tu_parser import parse_tu, read_tu_text
from backend.core.validation import validate_project_files
from backend.core.wire_resolver import WireSelectionError, apply_wire_selection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = PROJECT_ROOT / "examples" / "templates"
PROJECT_NUMBER_RE = re.compile(r"^ПСД/48/2026/\d{3}(?:-[А-ЯA-Z0-9]+)?$")

router = APIRouter(prefix="/api")


def _normalize_wire_form_params(
    wire_selection_mode: str,
    wire_manual_value: str | None,
) -> tuple[str, str | None]:
    mode = (wire_selection_mode or "auto").strip()
    manual = (wire_manual_value or "").strip() or None

    if mode.startswith("manual:"):
        manual = manual or mode.split(":", 1)[1].strip()
        mode = "manual"

    if mode == "manual" and not manual:
        raise WireSelectionError("Выбран ручной режим провода, но провод не указан.")
    if mode != "manual":
        mode = "auto"
        manual = None
    return mode, manual


@router.post("/process")
async def process_project(
    project_number: str = Form(...),
    tu_file: UploadFile = File(...),
    plan_file: UploadFile = File(...),
    wire_selection_mode: str = Form("auto"),
    wire_manual_value: str | None = Form(None),
) -> dict[str, Any]:
    project_number = project_number.strip()
    try:
        wire_selection_mode, wire_manual_value = _normalize_wire_form_params(
            wire_selection_mode,
            wire_manual_value,
        )
    except WireSelectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not PROJECT_NUMBER_RE.match(project_number):
        raise HTTPException(
            status_code=422,
            detail="Номер проекта должен соответствовать формату ПСД/48/2026/XXX или ПСД/48/2026/XXX-СУФФИКС.",
        )

    if not tu_file.filename:
        raise HTTPException(status_code=422, detail="Не выбран файл ТУ.")
    if not plan_file.filename:
        raise HTTPException(status_code=422, detail="Не выбран файл плана.")

    plan_extension = Path(plan_file.filename).suffix.lower()
    if plan_extension not in {".dxf", ".dwg"}:
        raise HTTPException(status_code=422, detail="Загрузите план в формате DWG или DXF.")

    output = OutputManager(PROJECT_ROOT)
    output.prepare()
    logger = output.logger()
    warnings: list[str] = []

    try:
        logger.info("Старт обработки проекта.")
        logger.info(f"Номер проекта получен из интерфейса: {project_number}")
        logger.info(
            "Параметры провода из формы: "
            f"mode={wire_selection_mode}, manual={wire_manual_value or '—'}"
        )

        tu_path = output.save_upload_to_project_archive(
            project_number,
            tu_file.filename,
            await tu_file.read(),
        )
        plan_path = output.save_upload_to_project_archive(
            project_number,
            plan_file.filename,
            await plan_file.read(),
        )
        logger.info(f"Файл ТУ сохранён в архив проекта: {tu_path}")
        logger.info(f"Файл плана сохранён в архив проекта: {plan_path}")

        tu_data, tu_warnings = parse_tu(tu_path)
        warnings.extend(tu_warnings)
        logger.info("Данные из ТУ извлечены.")
        for warning in tu_warnings:
            logger.warning(warning)

        try:
            wire_data = apply_wire_selection(
                tu_data,
                wire_selection_mode=wire_selection_mode,
                wire_manual_value=wire_manual_value,
                logger=logger,
            )
        except WireSelectionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        try:
            route_distance_result = calculate_delivery_distance_from_tu(
                read_tu_text(tu_path),
                fallback_address=str(tu_data.get("ADRESS", "") or ""),
                logger=logger,
            )
            tu_data["route_distance_km"] = route_distance_result["distanceKm"]
            tu_data["route_distance_meta"] = route_distance_result
            logger.info(
                "Километраж до РЭС рассчитан: "
                f"{route_distance_result['distanceKm']} км "
                f"(провайдер: {route_distance_result['provider']})."
            )
            if route_distance_result.get("locationConfidence") == "low":
                warnings.append(
                    "Километраж рассчитан по приблизительной точке района. "
                    "Проверьте значение вручную или уточните адрес в ТУ."
                )
            elif route_distance_result.get("locationConfidence") == "medium":
                warnings.append(
                    "Координаты участка определены приблизительно "
                    f"({route_distance_result.get('sourceMethod', 'неизвестно')}). "
                    "При необходимости проверьте километраж."
                )
        except DeliveryDistanceError as exc:
            warning = str(exc)
            warnings.append(warning)
            logger.warning(warning)

        if plan_extension == ".dwg":
            logger.info("План загружен в DWG. Конвертирую DWG в DXF через ODA.")
            plan_dxf_path = convert_dwg_plan_to_dxf_with_oda(
                plan_path,
                output.temp_dir / "uploaded_plan_converted.dxf",
                output.output_root,
                logger=logger,
            )
        else:
            plan_dxf_path = plan_path

        plan_data, plan_warnings = analyze_dxf(plan_dxf_path)
        warnings.extend(plan_warnings)
        logger.info("DXF-план проанализирован.")
        for warning in plan_warnings:
            logger.warning(warning)

        materials_data = calculate_materials(tu_data, plan_data)
        logger.info("Производные значения рассчитаны.")

        template_note_path, template_warning = select_template_note_path(
            TEMPLATES_DIR, tu_data, plan_data, logger
        )
        if template_warning:
            warnings.append(template_warning)

        project_data = {
            "project_number": project_number,
            "project_number_placeholder": "{{PROJNUMB}}",
            "template_note": template_note_path.name,
            "wire_selection_mode": wire_data["wire_selection_mode"],
            "wire_manual_value": wire_data["wire_manual_value"],
            "wire_auto_detected": wire_data["wire_auto_detected"],
            "wire_final_value": wire_data["wire_final_value"],
            "wire_weight_final": wire_data["wire_weight_final"],
            "tu_data": tu_data,
            "plan_data": plan_data,
            "materials_data": materials_data,
        }
        replacement_map = build_replacement_map(project_number, tu_data, materials_data)

        tu_data_path = output.write_json("tu_data.json", tu_data)
        plan_data_path = output.write_json("plan_data.json", plan_data)
        materials_data_path = output.write_json("materials_data.json", materials_data)
        project_data_path = output.write_json("project_data.json", project_data)
        replacement_map_path = output.write_json("replacement_map.json", replacement_map)
        logger.info("JSON-файлы сформированы.")

        logger.info("Начинаю заполнение DWG-записки (ODA). Это может занять несколько минут...")
        note_path = output.dwg_dir / "note_result.dwg"
        cad_result = replace_placeholders_in_dwg_with_oda(
            template_note_path,
            note_path,
            replacement_map,
            output.output_root,
            logger=logger,
        )
        if cad_result.get("unresolved_placeholders"):
            logger.warning("DWG сформирован, но часть placeholders осталась незаменённой.")
        else:
            logger.info("DWG-записка сформирована. Placeholders заменены.")
        template_placeholder_warning_msg = template_placeholder_warning(
            template_note_path,
            plan_data,
            cad_result.get("template_placeholders", []),
        )
        if template_placeholder_warning_msg:
            warnings.append(template_placeholder_warning_msg)
            logger.warning(template_placeholder_warning_msg)

        pdf_files: dict[str, str] = {}
        note_pdf_meta: dict[str, Any] = {}
        try:
            note_pdf_path = output.pdf_dir / "note_result.pdf"
            note_pdf_meta = export_note_dwg_to_pdf(
                note_path,
                note_pdf_path,
                work_dir=output.output_root,
                project_root=PROJECT_ROOT,
                logger=logger,
            )
            plan_pdf_path = render_dxf_to_pdf(plan_dxf_path, output.pdf_dir / "plan_result.pdf")
            tu_pdf_path = tu_path if tu_path.suffix.lower() == ".pdf" else None
            if tu_pdf_path is None and tu_path.suffix.lower() == ".docx":
                try:
                    tu_pdf_path = render_tu_docx_to_pdf(tu_path, output.pdf_dir / "tu_upload.pdf")
                    logger.info("DOCX-ТУ сконвертировано в PDF и будет вставлено в итоговый комплект.")
                except Exception as exc:
                    warning = f"ТУ не вставлено в итоговый PDF: не удалось сконвертировать DOCX в PDF ({exc})."
                    warnings.append(warning)
                    logger.warning(warning)
            final_pdf_path = merge_project_pdfs(
                note_pdf_path,
                plan_pdf_path,
                tu_pdf_path,
                output.pdf_dir / "final_project.pdf",
            )
            pdf_files = {
                "note_pdf": str(note_pdf_path),
                "plan_pdf": str(plan_pdf_path),
                "final_pdf": str(final_pdf_path),
            }
            if tu_pdf_path is not None:
                pdf_files["tu_pdf"] = str(tu_pdf_path)
            logger.info(
                "PDF-комплект сформирован. Записка экспортирована из готового DWG "
                f"({note_pdf_meta.get('method', 'unknown')})."
            )
        except Exception as exc:
            warning = f"PDF-комплект не сформирован: {exc}"
            warnings.append(warning)
            logger.warning(warning)

        archive_dir = output.archive_generated_files(
            project_number,
            note_path=note_path,
            final_pdf_path=Path(pdf_files["final_pdf"]) if pdf_files.get("final_pdf") else None,
        )
        logger.info(f"Архив проекта обновлён: {archive_dir}")

        return {
            "success": True,
            "status": "completed_with_warnings" if cad_result.get("unresolved_placeholders") else "completed",
            "warnings": warnings,
            "files": {
                "tu_data": str(tu_data_path),
                "plan_data": str(plan_data_path),
                "materials_data": str(materials_data_path),
                "project_data": str(project_data_path),
                "replacement_map": str(replacement_map_path),
                "template_note": str(template_note_path),
                "note_result": str(note_path),
                "project_archive": str(archive_dir),
                "tu_upload": str(tu_path),
                "plan_upload": str(plan_path),
                "log": str(output.logs_dir / "log.txt"),
                **pdf_files,
            },
            "cad": cad_result,
            "note_pdf": note_pdf_meta,
            "wire": wire_data,
            "steps": {
                "files_uploaded": True,
                "tu_extracted": True,
                "plan_analyzed": True,
                "replacement_map_created": True,
                "dwg_filled": not bool(cad_result.get("unresolved_placeholders")),
                "pdf_created": bool(pdf_files),
                "completed": not bool(cad_result.get("unresolved_placeholders")),
            },
        }
    except HTTPException:
        raise
    except WireSelectionError as exc:
        logger.error(str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OdaConverterError as exc:
        logger.error(str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(str(exc))
        raise HTTPException(status_code=500, detail=f"Ошибка обработки: {exc}") from exc


@router.post("/validate")
async def validate_project(
    tu_file: UploadFile = File(...),
    plan_file: UploadFile = File(...),
    note_file: UploadFile | None = File(None),
    project_number: str | None = Form(None),
    wire_selection_mode: str = Form("auto"),
    wire_manual_value: str | None = Form(None),
) -> dict[str, Any]:
    if not tu_file.filename:
        raise HTTPException(status_code=422, detail="Не выбран файл ТУ.")
    if not plan_file.filename:
        raise HTTPException(status_code=422, detail="Не выбран файл плана.")

    try:
        wire_selection_mode, wire_manual_value = _normalize_wire_form_params(
            wire_selection_mode,
            wire_manual_value,
        )
    except WireSelectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    output = OutputManager(PROJECT_ROOT)
    output.prepare()

    tu_path = output.save_upload_bytes(tu_file.filename, await tu_file.read(), "validate_tu")
    plan_path = output.save_upload_bytes(plan_file.filename, await plan_file.read(), "validate_plan")
    note_path = None
    if note_file and note_file.filename:
        note_path = output.save_upload_bytes(note_file.filename, await note_file.read(), "validate_note")

    try:
        return validate_project_files(
            tu_path=tu_path,
            plan_path=plan_path,
            note_path=note_path,
            templates_dir=TEMPLATES_DIR,
            work_dir=output.output_root,
            project_number=project_number,
            wire_selection_mode=wire_selection_mode,
            wire_manual_value=wire_manual_value,
            logger=output.logger(),
        )
    except OdaConverterError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка проверки: {exc}") from exc


@router.get("/download/note")
def download_note() -> FileResponse:
    path = PROJECT_ROOT / "output" / "result" / "dwg" / "note_result.dwg"
    if not path.exists():
        raise HTTPException(status_code=404, detail="note_result.dwg ещё не создан.")
    return FileResponse(path, filename="note_result.dwg", media_type="application/acad")


@router.get("/download/final-pdf")
def download_final_pdf():
    path = PROJECT_ROOT / "output" / "result" / "pdf" / "final_project.pdf"
    if not path.exists():
        return JSONResponse(
            status_code=202,
            content={
                "success": False,
                "status": "not_ready",
                "message": "PDF-комплект ещё не сформирован. Запустите обработку проекта или проверьте log.txt.",
            },
        )
    return FileResponse(path, filename="final_project.pdf", media_type="application/pdf")
