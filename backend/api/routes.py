from __future__ import annotations

import json
import re
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from backend.cad.oda_converter import OdaConverterError
from backend.cad.oda_dwg_adapter import (
    convert_dwg_plan_to_dxf_with_oda,
    replace_placeholders_in_dwg_with_oda,
)
from backend.core.ai_engineer import (
    chat_with_project,
    load_ai_engineer_chat,
    load_ai_engineer_report,
    llm_configured,
    run_ai_engineer_review,
    save_ai_engineer_chat,
    save_ai_engineer_report,
)
from backend.core.calculator import calculate_materials
from backend.core.calculator_10kv import calculate_materials_10kv
from backend.core.delivery_distance import DeliveryDistanceError, calculate_delivery_distance_from_tu
from backend.core.network import run_with_timeout
from backend.core.dxf_reader import analyze_dxf
from backend.core.output_manager import OutputManager
from backend.core.placeholders_10kv import (
    filter_tu_warnings_10kv,
    template_placeholder_warning_10kv,
)
from backend.core.plan_reader_10kv import read_plan_10kv_data
from backend.core.project_type import resolve_project_is_10kv
from backend.core.replacement_builder import build_replacement_map
from backend.core.replacement_builder_10kv import build_replacement_map_10kv, filter_cad_result_10kv
from backend.core.template_selector import select_template_note_path, template_placeholder_warning
from backend.core.template_selector_10kv import select_template_note_path_10kv
from backend.core.tu_parser import parse_tu, read_tu_text
from backend.core.tu_parser_10kv import enrich_tu_data_10kv
from backend.core.validation import validate_project_files
from backend.core.wire_resolver import WireSelectionError, apply_wire_selection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = PROJECT_ROOT / "examples" / "templates"
PROJECT_NUMBER_RE = re.compile(r"^ПСД/48/2026/\d{3}(?:-[А-ЯA-Z0-9]+)?$")

router = APIRouter(prefix="/api")


class AiEngineerChatBody(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_active_pipeline_workers: dict[str, threading.Thread] = {}
_active_pipeline_lock = threading.Lock()


def _new_run_id() -> str:
    return uuid.uuid4().hex


def _register_pipeline_worker(run_id: str, worker: threading.Thread) -> None:
    with _active_pipeline_lock:
        _active_pipeline_workers[run_id] = worker


def _unregister_pipeline_worker(run_id: str) -> None:
    with _active_pipeline_lock:
        _active_pipeline_workers.pop(run_id, None)


def _pipeline_worker_is_alive(run_id: str) -> bool:
    with _active_pipeline_lock:
        worker = _active_pipeline_workers.get(run_id)
    return bool(worker is not None and worker.is_alive())


def _mark_run_interrupted(run_id: str, current: dict[str, Any] | None = None) -> dict[str, Any]:
    """Если фоновый поток умер (reload/crash), не оставляем UI в вечном processing."""
    payload = dict(current or {})
    message = (
        "Обработка прервана: сервер перезапустился или фоновый поток остановился. "
        "Запустите проект ещё раз."
    )
    steps = dict(payload.get("steps") or {})
    return _write_run_status(
        run_id,
        {
            "success": False,
            "status": "failed",
            "project_number": payload.get("project_number", ""),
            "project_type": payload.get("project_type", ""),
            "warnings": payload.get("warnings") or [],
            "message": message,
            "detail": message,
            "note_download_url": payload.get("note_download_url")
            or _session_download_urls(run_id)["note_download_url"],
            "steps": {
                "files_uploaded": bool(steps.get("files_uploaded")),
                "tu_extracted": bool(steps.get("tu_extracted")),
                "plan_analyzed": bool(steps.get("plan_analyzed")),
                "replacement_map_created": bool(steps.get("replacement_map_created")),
                "dwg_filled": bool(steps.get("dwg_filled")) or _note_ready_for_run(run_id),
                "pdf_created": False,
                "completed": False,
            },
        },
    )


def _validate_run_id(run_id: str) -> str:
    cleaned = (run_id or "").strip()
    if not _RUN_ID_RE.fullmatch(cleaned):
        raise HTTPException(status_code=404, detail="Сессия проекта не найдена.")
    return cleaned


def _output_for_run(run_id: str | None = None) -> OutputManager:
    if run_id:
        return OutputManager.for_run(PROJECT_ROOT, _validate_run_id(run_id))
    return OutputManager(PROJECT_ROOT)


def _read_project_type(run_id: str | None = None) -> str:
    output = _output_for_run(run_id)
    data_path = output.data_dir / "project_data.json"
    if not data_path.exists():
        return ""
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(data.get("project_type", "") or "")


def _resolve_note_download(run_id: str | None = None) -> tuple[Path, str, str]:
    """Возвращает путь, имя файла и media-type для скачивания записки."""
    output = _output_for_run(run_id)
    dxf_path = output.dwg_dir / "note_result.dxf"
    if _read_project_type(run_id) == "10kv" and dxf_path.exists():
        return dxf_path, "note_result_10kV_filled.dxf", "application/dxf"
    dwg_path = output.dwg_dir / "note_result.dwg"
    if dwg_path.exists():
        return dwg_path, "note_result.dwg", "application/acad"
    raise HTTPException(
        status_code=404,
        detail="note_result.dxf или note_result.dwg ещё не создан.",
    )



def _session_download_urls(run_id: str) -> dict[str, str]:
    return {
        "note_download_url": f"/api/download/{run_id}/note",
        "note_dxf_download_url": f"/api/download/{run_id}/note-dxf",
    }


def _run_status_path(run_id: str) -> Path:
    return _output_for_run(run_id).data_dir / "run_status.json"


_STEP_PROGRESS = (
    ("files_uploaded", 8),
    ("tu_extracted", 18),
    ("plan_analyzed", 34),
    ("replacement_map_created", 50),
    ("dwg_filled", 88),
    ("completed", 100),
)


def _merge_run_steps(old: dict[str, Any] | None, new: dict[str, Any] | None) -> dict[str, bool]:
    merged: dict[str, bool] = {}
    for key, _weight in _STEP_PROGRESS:
        merged[key] = bool((old or {}).get(key)) or bool((new or {}).get(key))
    for key, value in {**(old or {}), **(new or {})}.items():
        if key not in merged:
            merged[key] = bool(value) or bool((old or {}).get(key))
    return merged


def _compute_run_progress(payload: dict[str, Any], previous: Any = 0) -> int:
    status = str(payload.get("status") or "")
    if status in {"completed", "completed_with_warnings"}:
        return 100
    steps = payload.get("steps") or {}
    best = 0
    for key, weight in _STEP_PROGRESS:
        if steps.get(key):
            best = weight
    try:
        previous_value = int(previous or 0)
    except (TypeError, ValueError):
        previous_value = 0
    if status == "failed":
        return max(0, min(99, previous_value or best))
    return max(previous_value, min(99, best))


def _write_run_status(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    output = _output_for_run(run_id)
    output.prepare()
    previous = _read_run_status(run_id) or {}
    data = {
        "run_id": run_id,
        **payload,
    }
    data["steps"] = _merge_run_steps(previous.get("steps"), data.get("steps"))
    data["progress"] = _compute_run_progress(data, previous.get("progress"))
    path = _run_status_path(run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)
    return data


def _read_run_status(run_id: str) -> dict[str, Any] | None:
    path = _run_status_path(run_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _note_ready_for_run(run_id: str) -> bool:
    output = _output_for_run(run_id)
    return (output.dwg_dir / "note_result.dwg").exists() or (output.dwg_dir / "note_result.dxf").exists()


def _recover_run_status(run_id: str) -> dict[str, Any] | None:
    output = _output_for_run(run_id)
    if not output.output_root.exists():
        return None
    download_urls = _session_download_urls(run_id)
    note_ready = _note_ready_for_run(run_id)
    project_type = _read_project_type(run_id)
    project_number = ""
    project_data_path = output.data_dir / "project_data.json"
    if project_data_path.exists():
        try:
            project_data = json.loads(project_data_path.read_text(encoding="utf-8"))
            project_number = str(project_data.get("project_number", "") or "")
            project_type = project_type or str(project_data.get("project_type", "") or "")
        except json.JSONDecodeError:
            pass
    if note_ready:
        note_path = output.dwg_dir / "note_result.dwg"
        if not note_path.exists():
            note_path = output.dwg_dir / "note_result.dxf"
        ai_report = load_ai_engineer_report(output.data_dir)
        return {
            "success": True,
            "status": "completed",
            "run_id": run_id,
            "project_number": project_number,
            "project_type": project_type,
            "warnings": [],
            "message": "Записка уже сформирована.",
            "note_download_url": download_urls["note_download_url"],
            "note_file_name": note_path.name,
            "ai_engineer": ai_report,
            "files": {
                "note_result": str(note_path),
                "log": str(output.logs_dir / "log.txt"),
            },
            "steps": {
                "files_uploaded": True,
                "tu_extracted": True,
                "plan_analyzed": True,
                "replacement_map_created": True,
                "dwg_filled": True,
                "pdf_created": False,
                "completed": True,
            },
        }
    return {
        "success": False,
        "status": "processing",
        "run_id": run_id,
        "project_number": project_number,
        "project_type": project_type,
        "warnings": [],
        "message": "Обработка ещё выполняется.",
        "note_download_url": download_urls["note_download_url"],
        "steps": {
            "files_uploaded": True,
            "tu_extracted": (output.data_dir / "tu_data.json").exists(),
            "plan_analyzed": (output.data_dir / "plan_data.json").exists(),
            "replacement_map_created": (output.data_dir / "replacement_map.json").exists(),
            "dwg_filled": False,
            "pdf_created": False,
            "completed": False,
        },
    }


def _update_run_progress(run_id: str, *, message: str, steps: dict[str, bool], **extra: Any) -> None:
    current = _read_run_status(run_id) or {"run_id": run_id, "status": "processing"}
    current.update(extra)
    current["status"] = "processing"
    current["success"] = False
    current["message"] = message
    current["steps"] = {
        **(current.get("steps") or {}),
        **steps,
    }
    _write_run_status(run_id, current)

def _normalize_branch_pole_type(value: str | None) -> str:
    normalized = (value or "").strip().casefold()
    if normalized in {"anchor", "ankernaya", "анкерная", "уок"}:
        return "anchor"
    if normalized in {"intermediate", "promежуточная", "промежуточная", "уоп"}:
        return "intermediate"
    return ""


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


@router.post("/detect")
async def detect_project(
    tu_file: UploadFile = File(...),
    plan_file: UploadFile | None = File(None),
    run_id: str | None = Form(None),
) -> dict[str, Any]:
    if not tu_file.filename:
        raise HTTPException(status_code=422, detail="Не выбран файл ТУ.")

    session_id = _validate_run_id(run_id) if run_id else _new_run_id()
    output = _output_for_run(session_id)
    output.prepare()
    tu_path = output.save_upload_bytes(tu_file.filename, await tu_file.read(), "detect_tu")
    try:
        tu_text = read_tu_text(tu_path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Не удалось прочитать ТУ: {exc}") from exc

    plan_data: dict[str, Any] | None = None
    if plan_file and plan_file.filename:
        plan_extension = Path(plan_file.filename).suffix.lower()
        if plan_extension not in {".dxf", ".dwg"}:
            raise HTTPException(status_code=422, detail="Загрузите план в формате DWG или DXF.")
        plan_path = output.save_upload_bytes(plan_file.filename, await plan_file.read(), "detect_plan")
        if plan_extension == ".dwg":
            plan_dxf_path = convert_dwg_plan_to_dxf_with_oda(
                plan_path,
                output.temp_dir / "detect_plan_converted.dxf",
                output.output_root,
            )
        else:
            plan_dxf_path = plan_path
        plan_data, _ = analyze_dxf(plan_dxf_path)
        plan_10kv_data, _ = read_plan_10kv_data(plan_dxf_path)
        plan_data = {**plan_data, **plan_10kv_data}

    is_10kv = resolve_project_is_10kv(tu_text, plan_data)
    return {
        "run_id": session_id,
        "project_type": "10kv" if is_10kv else "0.4kv",
        "requires_yopk": is_10kv,
    }


@router.post("/process")
async def process_project(
    project_number: str = Form(...),
    tu_file: UploadFile = File(...),
    plan_file: UploadFile = File(...),
    wire_selection_mode: str = Form("auto"),
    wire_manual_value: str | None = Form(None),
    branch_pole_type: str | None = Form(None),
    run_id: str | None = Form(None),
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

    session_id = _validate_run_id(run_id) if run_id else _new_run_id()
    output = _output_for_run(session_id)
    output.prepare()
    logger = output.logger()
    download_urls = _session_download_urls(session_id)

    logger.info("Старт обработки проекта.")
    logger.info(f"Сессия запуска: {session_id}")
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

    initial_status = _write_run_status(
        session_id,
        {
            "success": False,
            "status": "processing",
            "project_number": project_number,
            "warnings": [],
            "message": "Файлы загружены. Обработка запущена в фоне.",
            "note_download_url": download_urls["note_download_url"],
            "steps": {
                "files_uploaded": True,
                "tu_extracted": False,
                "plan_analyzed": False,
                "replacement_map_created": False,
                "dwg_filled": False,
                "pdf_created": False,
                "completed": False,
            },
        },
    )

    worker = threading.Thread(
        target=_execute_project_pipeline,
        kwargs={
            "session_id": session_id,
            "project_number": project_number,
            "tu_path": str(tu_path),
            "plan_path": str(plan_path),
            "plan_extension": plan_extension,
            "wire_selection_mode": wire_selection_mode,
            "wire_manual_value": wire_manual_value,
            "branch_pole_type": branch_pole_type,
        },
        daemon=True,
        name=f"project-pipeline-{session_id[:8]}",
    )
    _register_pipeline_worker(session_id, worker)
    worker.start()
    return initial_status


def _execute_project_pipeline(
    *,
    session_id: str,
    project_number: str,
    tu_path: str,
    plan_path: str,
    plan_extension: str,
    wire_selection_mode: str,
    wire_manual_value: str | None,
    branch_pole_type: str | None,
) -> None:
    output = _output_for_run(session_id)
    logger = output.logger()
    warnings: list[str] = []
    download_urls = _session_download_urls(session_id)
    tu_path_obj = Path(tu_path)
    plan_path_obj = Path(plan_path)

    try:
        tu_data, tu_warnings = parse_tu(tu_path_obj)
        warnings.extend(tu_warnings)
        logger.info("Данные из ТУ извлечены.")
        for warning in tu_warnings:
            logger.warning(warning)
        _update_run_progress(
            session_id,
            message="Данные из ТУ извлечены.",
            steps={"tu_extracted": True},
            project_number=project_number,
            note_download_url=download_urls["note_download_url"],
        )

        branch_pole = _normalize_branch_pole_type(branch_pole_type)

        try:
            wire_data = apply_wire_selection(
                tu_data,
                wire_selection_mode=wire_selection_mode,
                wire_manual_value=wire_manual_value,
                logger=logger,
            )
        except WireSelectionError as exc:
            raise ValueError(str(exc)) from exc

        _update_run_progress(
            session_id,
            message="Считаю километраж до РЭС…",
            steps={"tu_extracted": True},
            project_number=project_number,
            note_download_url=download_urls["note_download_url"],
        )
        try:
            tu_text_for_route = read_tu_text(tu_path_obj)
            fallback_address = str(tu_data.get("ADRESS", "") or "")

            def _calc_delivery() -> dict[str, Any]:
                return calculate_delivery_distance_from_tu(
                    tu_text_for_route,
                    fallback_address=fallback_address,
                    logger=logger,
                )

            route_distance_result = run_with_timeout(_calc_delivery, 8.0)
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
        except TimeoutError:
            warning = (
                "Километраж до РЭС не дождался ответа карт. "
                "Записка собирается без этого поля или по местной оценке."
            )
            warnings.append(warning)
            logger.warning(warning)
        except (DeliveryDistanceError, Exception) as exc:
            warning = str(exc) or "Километраж до РЭС не рассчитан."
            if not isinstance(exc, DeliveryDistanceError):
                warning = (
                    "Километраж до РЭС не рассчитан (нет ответа карт / нет интернета). "
                    "Записка собирается без этого поля."
                )
            warnings.append(warning)
            logger.warning(warning)

        if plan_extension == ".dwg":
            logger.info("План загружен в DWG. Конвертирую DWG в DXF через ODA.")
            plan_dxf_path = convert_dwg_plan_to_dxf_with_oda(
                plan_path_obj,
                output.temp_dir / "uploaded_plan_converted.dxf",
                output.output_root,
                logger=logger,
            )
        else:
            plan_dxf_path = plan_path_obj

        plan_data, plan_warnings = analyze_dxf(plan_dxf_path)
        warnings.extend(plan_warnings)
        logger.info("DXF-план проанализирован.")
        for warning in plan_warnings:
            logger.warning(warning)

        plan_10kv_data, plan_10kv_warnings = read_plan_10kv_data(plan_dxf_path)
        plan_data = {**plan_data, **plan_10kv_data}
        _update_run_progress(
            session_id,
            message="План проанализирован.",
            steps={"plan_analyzed": True},
            project_number=project_number,
            note_download_url=download_urls["note_download_url"],
            warnings=warnings,
        )

        project_is_10kv = resolve_project_is_10kv(read_tu_text(tu_path_obj), plan_data)
        if project_is_10kv:
            logger.info("Определён проект 10 кВ по данным плана.")
            if not branch_pole:
                raise ValueError(
                    "Для проекта 10 кВ укажите тип ответвления: intermediate (УОП) или anchor (УОК)."
                )
            tu_data, tu_10kv_warnings = enrich_tu_data_10kv(tu_path_obj, tu_data)
            warnings.extend(plan_10kv_warnings)
            warnings.extend(tu_10kv_warnings)
            warnings = filter_tu_warnings_10kv(warnings)
            for warning in plan_10kv_warnings:
                logger.warning(warning)
            for warning in tu_10kv_warnings:
                logger.warning(warning)
            logger.info("Данные 10 кВ из плана извлечены.")
        else:
            logger.info("Определён проект 0,4 кВ по данным плана.")
            if plan_10kv_warnings:
                for warning in plan_10kv_warnings:
                    logger.warning(warning)

        materials_10kv_data: dict[str, Any] = {}
        materials_data = calculate_materials(tu_data, plan_data)
        logger.info("Производные значения рассчитаны.")

        if project_is_10kv:
            materials_10kv_data = calculate_materials_10kv(
                tu_data,
                plan_data,
                branch_pole_type=branch_pole,
            )
            logger.info("Производные значения 10 кВ рассчитаны.")
            template_note_path, template_warning = select_template_note_path_10kv(
                TEMPLATES_DIR,
                plan_data,
                logger,
            )
        else:
            template_note_path, template_warning = select_template_note_path(
                TEMPLATES_DIR, tu_data, plan_data, logger
            )
        if template_warning:
            warnings.append(template_warning)

        project_data = {
            "project_number": project_number,
            "project_number_placeholder": "{{PROJNUMB}}",
            "project_type": "10kv" if project_is_10kv else "0.4kv",
            "branch_pole_type": branch_pole or None,
            "template_note": template_note_path.name,
            "wire_selection_mode": wire_data["wire_selection_mode"],
            "wire_manual_value": wire_data["wire_manual_value"],
            "wire_auto_detected": wire_data["wire_auto_detected"],
            "wire_final_value": wire_data["wire_final_value"],
            "wire_weight_final": wire_data["wire_weight_final"],
            "tu_data": tu_data,
            "plan_data": plan_data,
            "materials_data": materials_data,
            "materials_10kv_data": materials_10kv_data,
        }
        if project_is_10kv:
            replacement_map = build_replacement_map_10kv(
                project_number,
                tu_data,
                materials_data,
                materials_10kv_data,
            )
        else:
            replacement_map = build_replacement_map(project_number, tu_data, materials_data)

        tu_data_path = output.write_json("tu_data.json", tu_data)
        plan_data_path = output.write_json("plan_data.json", plan_data)
        materials_data_path = output.write_json("materials_data.json", materials_data)
        if project_is_10kv:
            output.write_json("materials_10kv_data.json", materials_10kv_data)
        project_data_path = output.write_json("project_data.json", project_data)
        replacement_map_path = output.write_json("replacement_map.json", replacement_map)
        logger.info("JSON-файлы сформированы.")
        _update_run_progress(
            session_id,
            message="Карта замен создана. Заполняю записку…",
            steps={"replacement_map_created": True},
            project_number=project_number,
            project_type="10kv" if project_is_10kv else "0.4kv",
            note_download_url=download_urls["note_download_url"],
            warnings=warnings,
        )

        logger.info("Начинаю заполнение DWG-записки (ODA). Это может занять несколько минут...")
        _update_run_progress(
            session_id,
            message="Заполняю пояснительную записку…",
            steps={"replacement_map_created": True},
            project_number=project_number,
            project_type="10kv" if project_is_10kv else "0.4kv",
            note_download_url=download_urls["note_download_url"],
            warnings=warnings,
        )
        note_path = output.dwg_dir / "note_result.dwg"
        for stale_name in ("note_result.dxf", "note_result_filled.dxf"):
            stale_path = output.dwg_dir / stale_name
            if stale_path.exists():
                stale_path.unlink()
                logger.info(f"Удалён устаревший {stale_name}.")
        cad_result = replace_placeholders_in_dwg_with_oda(
            template_note_path,
            note_path,
            replacement_map,
            output.output_root,
            logger=logger,
            preserve_template_structure=project_is_10kv,
        )
        if project_is_10kv:
            cad_result = filter_cad_result_10kv(cad_result)
            named_outputs = output.copy_note_result_for_project(project_number)
            for label, path in named_outputs.items():
                if path is not None:
                    logger.info(f"10 кВ: {label}: {path.name}")
        for cad_warning in cad_result.get("warnings", []) or []:
            warnings.append(cad_warning)
            logger.warning(cad_warning)
        unresolved = cad_result.get("unresolved_placeholders", [])
        note_created = note_path.exists()
        if unresolved:
            logger.warning("Записка сформирована, но часть placeholders осталась незаменённой.")
        elif note_created:
            logger.info("Записка сформирована. Placeholders заменены.")
        if project_is_10kv:
            template_placeholder_warning_msg = template_placeholder_warning_10kv(
                template_note_path,
                plan_data,
                cad_result.get("template_placeholders", []),
            )
        else:
            template_placeholder_warning_msg = template_placeholder_warning(
                template_note_path,
                plan_data,
                cad_result.get("template_placeholders", []),
            )
        if template_placeholder_warning_msg:
            warnings.append(template_placeholder_warning_msg)
            logger.warning(template_placeholder_warning_msg)

        logger.info("Экспорт PDF отключён — формируется только записка.")

        archive_dir = output.archive_generated_files(
            project_number,
            note_path=note_path,
            final_pdf_path=None,
        )
        logger.info(f"Архив проекта обновлён: {archive_dir}")

        ai_report = None
        ai_report_path = None
        if note_created:
            logger.info("Запускаю AI Engineer (пост-проверка, проект не изменяется)...")
            try:
                tu_text_for_ai = ""
                try:
                    tu_text_for_ai = read_tu_text(tu_path_obj)
                except Exception:
                    tu_text_for_ai = ""
                ai_report = run_ai_engineer_review(
                    project_data=project_data,
                    replacement_map=replacement_map,
                    cad_result=cad_result,
                    pipeline_warnings=warnings,
                    note_path=note_path,
                    plan_path=plan_dxf_path,
                    tu_text=tu_text_for_ai,
                    enable_llm=False,
                )
                ai_report_path = save_ai_engineer_report(output.data_dir, ai_report)
                # Дублируем геометрические warning в общий список — видно даже без вкладки AI.
                for finding in ai_report.get("findings") or []:
                    if finding.get("severity") != "warning":
                        continue
                    title = str(finding.get("title") or "").strip()
                    if not title:
                        continue
                    if title not in warnings:
                        warnings.append(f"AI Engineer: {title}")
                logger.info(
                    "AI Engineer готов: рейтинг "
                    f"{ai_report.get('score')}%, замечаний "
                    f"{len(ai_report.get('findings') or [])}."
                )
            except Exception as ai_exc:
                logger.warning(f"AI Engineer не выполнил проверку: {ai_exc}")
                ai_report = {
                    "module": "AI Engineer",
                    "readonly": True,
                    "does_not_modify_project": True,
                    "mode": "error",
                    "score": 0,
                    "status": "critical",
                    "summary": "Не удалось сформировать отчёт AI Engineer",
                    "checked": [],
                    "findings": [
                        {
                            "id": "ai_engineer_failed",
                            "severity": "warning",
                            "category": "general",
                            "title": "AI Engineer завершился с ошибкой",
                            "reason": str(ai_exc),
                            "action": "Посмотреть →",
                        }
                    ],
                    "disclaimer": (
                        "Все замечания — рекомендации для проектировщика. "
                        "AI Engineer не изменяет проект."
                    ),
                }

        result = {
            "success": note_created,
            "status": "completed_with_warnings" if note_created and (unresolved or warnings) else (
                "completed" if note_created else "failed"
            ),
            "warnings": warnings,
            "run_id": session_id,
            "project_number": project_number,
            "project_type": "10kv" if project_is_10kv else "0.4kv",
            "message": "Записка готова." if note_created else "Не удалось сформировать записку.",
            "note_download_url": download_urls["note_download_url"],
            "note_file_name": note_path.name,
            "files": {
                "tu_data": str(tu_data_path),
                "plan_data": str(plan_data_path),
                "materials_data": str(materials_data_path),
                "project_data": str(project_data_path),
                "replacement_map": str(replacement_map_path),
                "template_note": str(template_note_path),
                "note_result": str(note_path),
                "project_archive": str(archive_dir),
                "tu_upload": str(tu_path_obj),
                "plan_upload": str(plan_path_obj),
                "log": str(output.logs_dir / "log.txt"),
                "ai_engineer_report": str(ai_report_path) if ai_report_path else None,
            },
            "cad": cad_result,
            "wire": wire_data,
            "ai_engineer": ai_report,
            "steps": {
                "files_uploaded": True,
                "tu_extracted": True,
                "plan_analyzed": True,
                "replacement_map_created": True,
                "dwg_filled": note_created,
                "pdf_created": False,
                "completed": note_created,
            },
        }
        _write_run_status(session_id, result)
    except Exception as exc:
        logger.error(str(exc))
        _write_run_status(
            session_id,
            {
                "success": False,
                "status": "failed",
                "project_number": project_number,
                "warnings": warnings,
                "message": str(exc),
                "detail": str(exc),
                "note_download_url": download_urls["note_download_url"],
                "steps": {
                    "files_uploaded": True,
                    "tu_extracted": (output.data_dir / "tu_data.json").exists(),
                    "plan_analyzed": (output.data_dir / "plan_data.json").exists(),
                    "replacement_map_created": (output.data_dir / "replacement_map.json").exists(),
                    "dwg_filled": _note_ready_for_run(session_id),
                    "pdf_created": False,
                    "completed": False,
                },
            },
        )
    finally:
        _unregister_pipeline_worker(session_id)


@router.get("/status/{run_id}")
def get_run_status(run_id: str) -> dict[str, Any]:
    session_id = _validate_run_id(run_id)
    status = _read_run_status(session_id)
    if status:
        # Если статус устарел, а записка уже есть — отдаём готовность.
        if status.get("status") == "processing" and _note_ready_for_run(session_id):
            recovered = _recover_run_status(session_id)
            if recovered and recovered.get("status") == "completed":
                return _write_run_status(session_id, recovered)
        if status.get("status") == "processing" and not _pipeline_worker_is_alive(session_id):
            return _mark_run_interrupted(session_id, status)
        if not status.get("ai_engineer"):
            report = load_ai_engineer_report(_output_for_run(session_id).data_dir)
            if report:
                status = {**status, "ai_engineer": report}
        if status.get("progress") is None:
            status = {**status, "progress": _compute_run_progress(status)}
        return status
    recovered = _recover_run_status(session_id)
    if recovered:
        if recovered.get("status") == "processing" and not _pipeline_worker_is_alive(session_id):
            return _mark_run_interrupted(session_id, recovered)
        recovered["progress"] = _compute_run_progress(recovered)
        return recovered
    raise HTTPException(status_code=404, detail="Сессия проекта не найдена.")


def _resolve_plan_dxf_for_run(session_id: str, output: OutputManager) -> Path | None:
    """Ищет DXF плана для AI Engineer: uploads, temp, archive, путь из status."""
    status = _read_run_status(session_id) or {}
    candidates: list[Path] = []

    plan_upload = status.get("files", {}).get("plan_upload") if isinstance(status.get("files"), dict) else None
    if plan_upload:
        upload_path = Path(str(plan_upload))
        if upload_path.exists() and upload_path.suffix.lower() == ".dxf":
            candidates.append(upload_path)

    archive = status.get("files", {}).get("project_archive") if isinstance(status.get("files"), dict) else None
    if archive:
        archive_dir = Path(str(archive))
        if archive_dir.is_dir():
            candidates.extend(sorted(archive_dir.glob("*.dxf"), key=lambda path: path.stat().st_mtime, reverse=True))

    for folder in (output.uploads_dir, output.temp_dir):
        if folder.exists():
            candidates.extend(sorted(folder.glob("*.dxf"), key=lambda path: path.stat().st_mtime, reverse=True))

    # Предпочитаем detect_plan / uploaded plan, не template_temp / filled_temp.
    preferred = [
        path
        for path in candidates
        if path.exists()
        and path.suffix.lower() == ".dxf"
        and "template" not in path.name.lower()
        and "filled" not in path.name.lower()
        and "note" not in path.name.lower()
    ]
    if preferred:
        return preferred[0]
    for path in candidates:
        if path.exists() and path.suffix.lower() == ".dxf":
            return path
    return None


def _general_chat_dir() -> Path:
    # Desktop/output в iCloud может зависнуть на записи — чат тогда падает в браузере.
    path = Path.home() / "Library" / "Application Support" / "PRO-VL" / "ai_engineer_chat"
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.get("/ai-engineer/chat")
def get_ai_engineer_general_chat() -> dict[str, Any]:
    """Чат по нормам без сформированного проекта."""
    return {
        "configured": llm_configured(),
        "scope": "general",
        "messages": load_ai_engineer_chat(_general_chat_dir()),
    }


@router.post("/ai-engineer/chat")
def post_ai_engineer_general_chat(body: AiEngineerChatBody) -> dict[str, Any]:
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Введите вопрос.")
    data_dir = _general_chat_dir()
    history = load_ai_engineer_chat(data_dir)
    result = chat_with_project(
        message=message,
        project_data={},
        replacement_map={},
        report={},
        cad_result={},
        history=history,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=str(result.get("error") or "Чат недоступен."))
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": str(result.get("reply") or "")})
    try:
        save_ai_engineer_chat(data_dir, history)
        messages = load_ai_engineer_chat(data_dir)
    except OSError:
        messages = history[-40:]
    return {
        "ok": True,
        "reply": result["reply"],
        "model": result.get("model") or "",
        "scope": "general",
        "messages": messages,
    }


@router.get("/ai-engineer/{run_id}")
def get_ai_engineer_report(run_id: str, refresh: bool = False) -> dict[str, Any]:
    """Возвращает отчёт AI Engineer по готовому проекту (без изменения файлов)."""
    session_id = _validate_run_id(run_id)
    output = _output_for_run(session_id)
    if not refresh:
        report = load_ai_engineer_report(output.data_dir)
        if report:
            return report

    project_path = output.data_dir / "project_data.json"
    map_path = output.data_dir / "replacement_map.json"
    if not project_path.exists() or not map_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Отчёт AI Engineer ещё не готов: сначала сформируйте проект.",
        )
    try:
        project_data = json.loads(project_path.read_text(encoding="utf-8"))
        replacement_map = json.loads(map_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Повреждены JSON проекта: {exc}") from exc

    status = _read_run_status(session_id) or {}
    note_path = output.dwg_dir / "note_result.dwg"
    if not note_path.exists():
        note_path = output.dwg_dir / "note_result.dxf"
    plan_path = _resolve_plan_dxf_for_run(session_id, output)
    report = run_ai_engineer_review(
        project_data=project_data,
        replacement_map=replacement_map,
        cad_result=status.get("cad") or {},
        pipeline_warnings=list(status.get("warnings") or []),
        note_path=note_path if note_path.exists() else None,
        plan_path=plan_path,
        tu_text="",
        enable_llm=False,
    )
    save_ai_engineer_report(output.data_dir, report)
    return report


@router.get("/ai-engineer/{run_id}/chat")
def get_ai_engineer_chat(run_id: str) -> dict[str, Any]:
    session_id = _validate_run_id(run_id)
    output = _output_for_run(session_id)
    if not (output.data_dir / "project_data.json").exists():
        raise HTTPException(status_code=404, detail="Сначала сформируйте проект.")
    return {
        "configured": llm_configured(),
        "messages": load_ai_engineer_chat(output.data_dir),
    }


@router.post("/ai-engineer/{run_id}/chat")
def post_ai_engineer_chat(run_id: str, body: AiEngineerChatBody) -> dict[str, Any]:
    session_id = _validate_run_id(run_id)
    output = _output_for_run(session_id)
    project_path = output.data_dir / "project_data.json"
    map_path = output.data_dir / "replacement_map.json"
    if not project_path.exists() or not map_path.exists():
        raise HTTPException(status_code=404, detail="Сначала сформируйте проект.")
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Введите вопрос.")
    try:
        project_data = json.loads(project_path.read_text(encoding="utf-8"))
        replacement_map = json.loads(map_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Повреждены JSON проекта: {exc}") from exc

    report = load_ai_engineer_report(output.data_dir) or {}
    status = _read_run_status(session_id) or {}
    history = load_ai_engineer_chat(output.data_dir)
    result = chat_with_project(
        message=message,
        project_data=project_data,
        replacement_map=replacement_map,
        report=report,
        cad_result=status.get("cad") or {},
        history=history,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=503, detail=str(result.get("error") or "Чат недоступен."))
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": str(result.get("reply") or "")})
    try:
        save_ai_engineer_chat(output.data_dir, history)
        messages = load_ai_engineer_chat(output.data_dir)
    except OSError:
        messages = history[-40:]
    return {
        "ok": True,
        "reply": result["reply"],
        "model": result.get("model") or "",
        "messages": messages,
    }


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
    path, filename, media_type = _resolve_note_download()
    return FileResponse(path, filename=filename, media_type=media_type)


@router.get("/download/note-dxf")
def download_note_dxf() -> FileResponse:
    path = PROJECT_ROOT / "output" / "result" / "dwg" / "note_result.dxf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="note_result.dxf ещё не создан.")
    return FileResponse(path, filename="note_result.dxf", media_type="application/dxf")


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


@router.get("/download/{run_id}/note")
def download_note_for_run(run_id: str) -> FileResponse:
    path, filename, media_type = _resolve_note_download(run_id)
    return FileResponse(path, filename=filename, media_type=media_type)


@router.get("/download/{run_id}/note-dxf")
def download_note_dxf_for_run(run_id: str) -> FileResponse:
    output = _output_for_run(run_id)
    path = output.dwg_dir / "note_result.dxf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="note_result.dxf ещё не создан.")
    return FileResponse(path, filename="note_result.dxf", media_type="application/dxf")


@router.get("/download/{run_id}/final-pdf")
def download_final_pdf_for_run(run_id: str):
    output = _output_for_run(run_id)
    path = output.pdf_dir / "final_project.pdf"
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
