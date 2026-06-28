from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from backend.cad.oda_converter import OdaConverterError
from backend.cad.oda_dwg_adapter import (
    convert_dwg_plan_to_dxf_with_oda,
    find_placeholders_in_dwg_file,
)
from backend.core.calculator import calculate_materials
from backend.core.dxf_reader import analyze_dxf
from backend.core.note_validator import validate_filled_note
from backend.core.replacement_builder import TU_FIELDS, build_replacement_map
from backend.core.template_selector import select_template_note_path, template_placeholder_warning
from backend.core.tu_parser import abbreviate_address_display_terms, parse_tu
from backend.core.wire_resolver import WireSelectionError, apply_wire_selection


PROJECT_NUMBER_RE = re.compile(r"^ПСД/48/2026/\d{3}(?:-[А-ЯA-Z0-9]+)?$")

CORE_NOTE_PLACEHOLDERS = (
    "{{PROJNUMB}}",
    "{{APPLICANT}}",
    "{{ADRESS}}",
    "{{KADNUMBER}}",
    "{{DATE}}",
    "{{FAZE}}",
    "{{SECH_KABEL}}",
    "{{OTKUDASTROIT}}",
    "{{TP_NAME}}",
    "{{LINE_LENGTH_M}}",
    "{{LINE_LENGTH_KM}}",
    "{{P23}}",
    "{{A23}}",
    "{{YA23}}",
    "{{K21}}",
    "{{GROUND}}",
)

LEGACY_PLACEHOLDER_HINTS = {
    "{{PROJECTNUMBER}}": "{{PROJNUMB}}",
    "{{ADDRESS}}": "{{ADRESS}}",
    "{{TO_NAME}}": "{{TP_NAME}}",
    "{{OTUDASTROIT}}": "{{OTKUDASTROIT}}",
}

TU_FIELD_LABELS = {
    "APPLICANT": "заявитель",
    "ADRESS": "адрес объекта",
    "KADNUMBER": "кадастровый номер",
    "DATE": "дата договора",
    "FAZE": "фазность",
    "STROIDOM": "строительство дома",
    "SECH_KABEL": "сечение кабеля",
    "OTKUDASTROIT": "откуда строить",
    "TP_NAME": "трансформаторная подстанция",
}

PLAN_SUPPORT_LABELS = {
    "P23": "П23",
    "A23": "А23",
    "YA23": "УА23*",
    "K21": "К21",
}

ARMATURE_CHECK_FIELDS = (
    ("P23", "{{P23}}"),
    ("A23", "{{A23}}"),
    ("YA23", "{{YA23}}"),
    ("K21", "{{K21}}"),
    ("GROUND", "{{GROUND}}"),
    ("S", "{{S}}"),
    ("F207", "{{F207}}"),
    ("NC20", "{{NC20}}"),
    ("ES15", "{{ES15}}"),
    ("CS10", "{{CS10}}"),
    ("PA15", "{{PA15}}"),
    ("ZP6", "{{ZP6}}"),
    ("X89", "{{X89}}"),
    ("CD35", "{{CD35}}"),
    ("E778", "{{E778}}"),
    ("GR", "{{GR}}"),
    ("P72", "{{P72}}"),
    ("P95", "{{P95}}"),
    ("P645", "{{P645}}"),
    ("SUPPORTS_INSTALL_NOTE", "{{SUPPORTS_INSTALL_NOTE}}"),
)

NOTE_VALUE_CHECK_FIELDS = (
    "P23",
    "A23",
    "YA23",
    "K21",
    "GROUND",
    "S",
    "F207",
    "NC20",
    "ES15",
    "CS10",
    "PA15",
    "ZP6",
    "X89",
    "CD35",
    "E778",
    "GR",
    "P72",
    "P95",
    "P645",
    "LINE_LENGTH_M",
    "SUPPORTS_INSTALL_NOTE",
)

ARMATURE_FIELD_LABELS = {
    "P23": "таблица объёмов, опоры П23",
    "A23": "таблица объёмов, опоры А23",
    "YA23": "таблица объёмов, опоры УА23*",
    "K21": "таблица объёмов, опоры К21",
    "GROUND": "таблица объёмов, заземления",
    "S": "таблица объёмов, всего опор",
    "F207": "таблица «Линейная арматура», F207",
    "NC20": "таблица «Линейная арматура», NC20",
    "ES15": "таблица «Линейная арматура», ES15",
    "CS10": "таблица «Линейная арматура», CS10",
    "PA15": "таблица «Линейная арматура», PA15",
    "ZP6": "таблица «Линейная арматура», ЗП6",
    "X89": "таблица «Линейная арматура», X89",
    "CD35": "таблица «Линейная арматура», CD35",
    "E778": "таблица «Линейная арматура», E778",
    "GR": "таблица «Линейная арматура», GR",
    "P72": "таблица «Линейная арматура», P72",
    "P95": "таблица «Линейная арматура», P95",
    "P645": "таблица «Линейная арматура», P645",
    "LINE_LENGTH_M": "исходные данные, длина линии",
    "SUPPORTS_INSTALL_NOTE": "таблица спецификации, примечание к СИП",
}

NOTE_FIELD_LOCATIONS = {
    "PROJNUMB": "титульный лист, номер проекта",
    "APPLICANT": "титульный лист, заявитель",
    "ADRESS": "титульный лист, адрес объекта",
    "ADDRESS": "титульный лист, адрес объекта",
    "KADNUMBER": "раздел «Исходные данные», кадастровый номер",
    "DATE": "титульный лист / исходные данные, дата",
    "FAZE": "исходные данные, фазность",
    "SECH_KABEL": "исходные данные, сечение кабеля",
    "OTKUDASTROIT": "исходные данные, откуда строить",
    "TP_NAME": "исходные данные, трансформаторная подстанция",
    "BRANCH_ARMATURE_LINE": "раздел «Строительные решения», ответвительная арматура",
    "ROUTE_PLAN_SHEET": "содержание, лист «План трассы ВЛИ-0,4 кВ»",
    "TOTAL_SHEETS": "штамп, общее количество листов",
    "A3_SHEET_COUNT": "комплект чертежей, количество листов А3",
    **ARMATURE_FIELD_LABELS,
}


@dataclass(frozen=True)
class ValidationIssue:
    category: str
    severity: str
    code: str
    message: str
    field: str | None = None
    location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_project_files(
    *,
    tu_path: Path,
    plan_path: Path,
    note_path: Path | None,
    templates_dir: Path,
    work_dir: Path,
    project_number: str | None = None,
    wire_selection_mode: str = "auto",
    wire_manual_value: str | None = None,
    logger: Any | None = None,
) -> dict[str, Any]:
    issues: list[ValidationIssue] = []
    summary: dict[str, Any] = {
        "tu": None,
        "plan": None,
        "note": None,
        "wire": None,
        "template_selected": None,
    }

    project_number = (project_number or "").strip()
    if project_number and not PROJECT_NUMBER_RE.match(project_number):
        issues.append(
            ValidationIssue(
                category="project",
                severity="error",
                code="PROJECT_NUMBER_FORMAT",
                message=(
                    "Номер проекта должен соответствовать формату "
                    "ПСД/48/2026/XXX или ПСД/48/2026/XXX-СУФФИКС."
                ),
                field="PROJNUMB",
            )
        )
    elif not project_number:
        pass

    tu_extension = tu_path.suffix.lower()
    if tu_extension not in {".docx", ".pdf"}:
        issues.append(
            ValidationIssue(
                category="tu",
                severity="error",
                code="TU_FORMAT",
                message="ТУ должен быть в формате DOCX или PDF.",
            )
        )
        return _build_result(issues, summary)

    try:
        tu_data, tu_warnings = parse_tu(tu_path)
    except Exception as exc:
        issues.append(
            ValidationIssue(
                category="tu",
                severity="error",
                code="TU_READ_FAILED",
                message=f"Не удалось прочитать ТУ: {exc}",
            )
        )
        return _build_result(issues, summary)

    summary["tu"] = _public_tu_summary(tu_data)
    issues.extend(_issues_from_tu_warnings(tu_warnings))
    issues.extend(_issues_from_missing_tu_fields(tu_data))

    try:
        wire_data = apply_wire_selection(
            tu_data,
            wire_selection_mode=wire_selection_mode,
            wire_manual_value=wire_manual_value,
            logger=logger,
        )
        summary["wire"] = {
            "mode": wire_data["wire_selection_mode"],
            "auto_detected": wire_data["wire_auto_detected"],
            "final_value": wire_data["wire_final_value"],
            "final_label": wire_data.get("wire_final_label"),
        }
    except WireSelectionError as exc:
        issues.append(
            ValidationIssue(
                category="wire",
                severity="error",
                code="WIRE_SELECTION",
                message=str(exc),
            )
        )
        wire_data = None

    plan_extension = plan_path.suffix.lower()
    if plan_extension not in {".dxf", ".dwg"}:
        issues.append(
            ValidationIssue(
                category="plan",
                severity="error",
                code="PLAN_FORMAT",
                message="План должен быть в формате DWG или DXF.",
            )
        )
        return _build_result(issues, summary)

    try:
        if plan_extension == ".dwg":
            plan_dxf_path = convert_dwg_plan_to_dxf_with_oda(
                plan_path,
                work_dir / "validate_plan.dxf",
                work_dir,
                logger=logger,
            )
        else:
            plan_dxf_path = plan_path
        plan_data, plan_warnings = analyze_dxf(plan_dxf_path)
    except OdaConverterError as exc:
        issues.append(
            ValidationIssue(
                category="plan",
                severity="error",
                code="PLAN_DWG_CONVERT",
                message=f"Не удалось конвертировать DWG-план: {exc}",
            )
        )
        return _build_result(issues, summary)
    except Exception as exc:
        issues.append(
            ValidationIssue(
                category="plan",
                severity="error",
                code="PLAN_READ_FAILED",
                message=f"Не удалось проанализировать план: {exc}",
            )
        )
        return _build_result(issues, summary)

    summary["plan"] = _public_plan_summary(plan_data)
    issues.extend(_issues_from_plan_warnings(plan_warnings))
    issues.extend(_issues_from_plan_data(plan_data))

    template_path, template_warning = select_template_note_path(
        templates_dir,
        tu_data,
        plan_data,
        logger=logger,
    )
    summary["template_selected"] = template_path.name
    if template_warning:
        issues.append(
            ValidationIssue(
                category="note",
                severity="warning",
                code="TEMPLATE_FALLBACK",
                message=template_warning,
            )
        )

    note_source = note_path or template_path
    note_source_label = note_path.name if note_path else f"эталон {template_path.name}"
    if note_path and note_path.suffix.lower() not in {".dwg", ".dxf"}:
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_FORMAT",
                message="Записка должна быть в формате DWG или DXF.",
            )
        )
        return _build_result(issues, summary)

    try:
        placeholders = find_placeholders_in_dwg_file(note_source, work_dir, logger=logger)
    except OdaConverterError as exc:
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_DWG_CONVERT",
                message=f"Не удалось прочитать записку ({note_source_label}): {exc}",
            )
        )
        return _build_result(issues, summary)
    except Exception as exc:
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_READ_FAILED",
                message=f"Не удалось просканировать placeholders в записке ({note_source_label}): {exc}",
            )
        )
        return _build_result(issues, summary)

    note_mode = _note_validation_mode(placeholders)
    summary["note"] = {
        "source": note_source_label,
        "mode": note_mode,
        "placeholders_count": len(placeholders),
        "placeholders": placeholders,
    }

    if note_mode == "template":
        issues.extend(_issues_from_note_placeholders(placeholders, plan_data))
        placeholder_warning = template_placeholder_warning(template_path, plan_data, placeholders)
        if placeholder_warning:
            issues.append(
                ValidationIssue(
                    category="note",
                    severity="error",
                    code="NOTE_MISSING_SUPPORT_PLACEHOLDERS",
                    message=placeholder_warning,
                )
            )
    else:
        pass

    materials_data: dict[str, Any] | None = None
    replacement_map: dict[str, str] | None = None
    if wire_data is not None:
        materials_data = calculate_materials(tu_data, plan_data)
        summary["armature"] = _build_armature_report(plan_data, materials_data, tu_data)
        project_for_map = project_number if project_number and PROJECT_NUMBER_RE.match(project_number) else "ПСД/48/2026/000"
        replacement_map = build_replacement_map(project_for_map, tu_data, materials_data)
        if note_mode == "template" and project_number and PROJECT_NUMBER_RE.match(project_number):
            issues.extend(_issues_from_replacement_map(replacement_map, placeholders))
        if note_mode == "filled" and replacement_map is not None:
            issues.extend(
                validate_filled_note(
                    note_source,
                    work_dir,
                    replacement_map,
                    tu_data,
                    project_number,
                )
            )

    return _build_result(issues, summary)


def _build_result(issues: list[ValidationIssue], summary: dict[str, Any]) -> dict[str, Any]:
    visible = [issue for issue in issues if issue.severity in {"error", "warning"}]
    blocking = [issue for issue in visible if issue.severity == "error"]
    warnings = [issue for issue in visible if issue.severity == "warning"]
    return {
        "ready": len(blocking) == 0,
        "issues": [issue.to_dict() for issue in visible],
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
        "summary": summary,
    }


def _issues_from_tu_warnings(warnings: list[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for warning in warnings:
        field_match = re.search(r"Поле ([A-Z_]+) ", warning)
        if "не удалось уверенно извлечь" in warning and field_match:
            field = field_match.group(1)
            label = TU_FIELD_LABELS.get(field, field)
            issues.append(
                ValidationIssue(
                    category="tu",
                    severity="warning",
                    code="TU_FIELD_MISSING",
                    message=f"В ТУ не найдено поле «{label}» ({field}).",
                    field=field,
                )
            )
            continue
        severity = "warning"
        code = "TU_WARNING"
        if "скан" in warning.lower() or "ocr" in warning.lower():
            code = "TU_SCAN_QUALITY"
            severity = "error"
        issues.append(
            ValidationIssue(
                category="tu",
                severity=severity,
                code=code,
                message=warning,
            )
        )
    return issues


def _issues_from_missing_tu_fields(tu_data: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not tu_data.get("POWER_KW"):
        issues.append(
            ValidationIssue(
                category="tu",
                severity="warning",
                code="TU_POWER_MISSING",
                message="В ТУ не найдена максимальная мощность (кВт).",
                field="POWER_KW",
            )
        )
    if tu_data.get("requires_komapparat_template"):
        pass
    return issues


def _issues_from_plan_warnings(warnings: list[str]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for warning in warnings:
        severity = "warning"
        code = "PLAN_WARNING"
        if "полилиния" in warning.lower() and "не найдена" in warning.lower():
            code = "PLAN_NO_POLYLINE"
            severity = "error"
        issues.append(
            ValidationIssue(
                category="plan",
                severity=severity,
                code=code,
                message=warning,
            )
        )
    return issues


def _issues_from_plan_data(plan_data: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    supports = plan_data.get("supports", {})
    total = sum(int(supports.get(key, 0) or 0) for key in ("P23", "A23", "YA23", "K21"))
    if total == 0:
        issues.append(
            ValidationIssue(
                category="plan",
                severity="error",
                code="PLAN_NO_SUPPORTS",
                message="На плане не найдены опоры (П23, А23, УА23*, К21).",
                location="план DWG/DXF",
            )
        )
    if float(plan_data.get("line_length_m", 0) or 0) <= 0:
        issues.append(
            ValidationIssue(
                category="plan",
                severity="error",
                code="PLAN_ZERO_LENGTH",
                message="Длина основной полилинии ВЛ равна 0 м.",
                field="LINE_LENGTH_M",
            )
        )
    grounding = int(plan_data.get("grounding_count", 0) or 0)
    if grounding == 0:
        issues.append(
            ValidationIssue(
                category="plan",
                severity="warning",
                code="PLAN_NO_GROUNDING",
                message="На плане не найдены заземления.",
                field="GROUND",
            )
        )
    return issues


def _issues_from_note_placeholders(
    placeholders: list[str],
    plan_data: dict[str, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    found = set(placeholders)

    for legacy, preferred in LEGACY_PLACEHOLDER_HINTS.items():
        if legacy in found:
            issues.append(
                ValidationIssue(
                    category="note",
                    severity="warning",
                    code="NOTE_LEGACY_PLACEHOLDER",
                    message=f"В записке найден устаревший placeholder {legacy}. Рекомендуется {preferred}.",
                    field=preferred.strip("{}"),
                )
            )

    missing_core = sorted(set(CORE_NOTE_PLACEHOLDERS) - found)
    if missing_core:
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_MISSING_CORE_PLACEHOLDERS",
                message="В записке отсутствуют обязательные placeholders: " + ", ".join(missing_core),
            )
        )

    supports = plan_data.get("supports", {})
    if int(supports.get("A23", 0) or 0) > 0 and "{{A23}}" not in found:
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_MISSING_A23",
                message="На плане есть опоры А23, но в записке нет {{A23}}.",
                field="A23",
            )
        )
    if int(supports.get("YA23", 0) or 0) > 0 and "{{YA23}}" not in found:
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_MISSING_YA23",
                message="На плане есть опоры УА23*, но в записке нет {{YA23}}.",
                field="YA23",
            )
        )

    if placeholders:
        pass
    else:
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_NO_PLACEHOLDERS",
                message="В шаблоне записки не найдено ни одного placeholder вида {{FIELD}}.",
                location="шаблон записки",
            )
        )
    return issues


def _note_validation_mode(placeholders: list[str]) -> str:
    core_found = sum(1 for item in CORE_NOTE_PLACEHOLDERS if item in placeholders)
    if core_found >= 4 or len(placeholders) >= 6:
        return "template"
    return "filled"


def _build_armature_report(
    plan_data: dict[str, Any],
    materials_data: dict[str, Any],
    tu_data: dict[str, Any],
) -> dict[str, Any]:
    supports = plan_data.get("supports", {})
    p23 = int(supports.get("P23", 0) or 0)
    a23 = int(supports.get("A23", 0) or 0)
    ya23 = int(supports.get("YA23", 0) or 0)
    k21 = int(supports.get("K21", 0) or 0)
    ground = int(plan_data.get("grounding_count", 0) or 0)
    total = p23 + a23 + ya23 + k21
    phase = str(tu_data.get("FAZE", "")).lower()
    is_three_phase = "трехфаз" in phase or "трёхфаз" in phase

    def part(label: str, count: int, coef: int | float) -> str:
        if not count or not coef:
            return ""
        value = count * coef
        if float(coef).is_integer():
            coef_text = str(int(coef))
        else:
            coef_text = str(coef).replace(".", ",")
        return f"{label}×{coef_text}={value:g}"

    f207_parts = [
        part("П23", p23, 2),
        part("А23", a23, 2),
        part("УА23", ya23, 4),
        part("К21", k21, 2),
    ]
    f207_formula = " + ".join(item for item in f207_parts if item) + " + 6"
    cs10_parts = [part("К21", k21, 2), part("А23", a23, 2), part("УА23", ya23, 2)]
    cd35_parts = [part("П23", p23, 1), part("А23", a23, 2), part("К21", k21, 2), part("УА23", ya23, 2)]
    zp6_parts = [part("П23", p23, 0.3), part("А23", a23, 0.65), part("К21", k21, 0.65), part("УА23", ya23, 1)]

    items = [
        {
            "field": "P23",
            "label": "Опоры П23",
            "value": p23,
            "formula": "с плана",
        },
        {
            "field": "A23",
            "label": "Опоры А23",
            "value": a23,
            "formula": "с плана",
        },
        {
            "field": "YA23",
            "label": "Опоры УА23*",
            "value": ya23,
            "formula": "с плана",
        },
        {
            "field": "K21",
            "label": "Опоры К21",
            "value": k21,
            "formula": "с плана",
        },
        {
            "field": "S",
            "label": "Всего опор",
            "value": total,
            "formula": f"{p23}+{a23}+{ya23}+{k21}",
        },
        {
            "field": "GROUND",
            "label": "Заземления",
            "value": ground,
            "formula": "с плана",
        },
        {
            "field": "F207",
            "label": "F207 (монтажная лента)",
            "value": materials_data.get("F207"),
            "formula": f207_formula,
        },
        {
            "field": "NC20",
            "label": "NC20 (скрепа)",
            "value": materials_data.get("NC20"),
            "formula": "равно F207",
        },
        {
            "field": "ES15",
            "label": "ES15 (подвеска)",
            "value": materials_data.get("ES15"),
            "formula": f"П23={p23}",
        },
        {
            "field": "CS10",
            "label": "CS10 (кронштейн)",
            "value": materials_data.get("CS10"),
            "formula": " + ".join(item for item in cs10_parts if item),
        },
        {
            "field": "PA15",
            "label": "PA15 (натяжной зажим)",
            "value": materials_data.get("PA15"),
            "formula": "равно CS10",
        },
        {
            "field": "ZP6",
            "label": "ЗП6 (заземляющий проводник, м)",
            "value": materials_data.get("ZP6"),
            "formula": " + ".join(item for item in zp6_parts if item),
        },
        {
            "field": "X89",
            "label": "X89 (стяжка)",
            "value": materials_data.get("X89"),
            "formula": f"УА23={ya23}",
        },
        {
            "field": "CD35",
            "label": "CD35 (зажим плашечный)",
            "value": materials_data.get("CD35"),
            "formula": " + ".join(item for item in cd35_parts if item),
        },
        {
            "field": "E778",
            "label": "E778 (хомут)",
            "value": materials_data.get("E778"),
            "formula": f"Всего опор×2 = {total}×2",
        },
        {
            "field": "GR",
            "label": "GR (заземление, шт)",
            "value": materials_data.get("GR"),
            "formula": f"Заземления×3 = {ground}×3",
        },
        {
            "field": "P72",
            "label": "P72 (прокалывающий зажим)",
            "value": materials_data.get("P72"),
            "formula": f"1 на каждую опору = {total}",
        },
        {
            "field": "P95",
            "label": "P95",
            "value": materials_data.get("P95"),
            "formula": "всегда 4",
        },
        {
            "field": "P645",
            "label": "P645 (зажим СИП)",
            "value": materials_data.get("P645"),
            "formula": "4 (трёхфаз.)" if is_three_phase else "2 (однофаз.)",
        },
        {
            "field": "SUPPORTS_INSTALL_NOTE",
            "label": "Примечание к СИП",
            "value": materials_data.get("SUPPORTS_INSTALL_NOTE"),
            "formula": f"по {total} опорам",
        },
    ]
    return {
        "supports": {"P23": p23, "A23": a23, "YA23": ya23, "K21": k21, "total": total},
        "grounding_count": ground,
        "items": items,
    }


def _issues_from_filled_note(
    note_text: str,
    replacement_map: dict[str, str],
    materials_data: dict[str, Any],
    tu_data: dict[str, Any],
    project_number: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    searchable = _normalize_search_text(note_text)

    if not project_number:
        issues.append(
            _missing_value_issue(
                "PROJNUMB",
                "—",
                "Укажите номер проекта в основной форме, чтобы проверить титульный лист.",
                severity="warning",
            )
        )
    elif PROJECT_NUMBER_RE.match(project_number):
        expected = replacement_map.get("{{PROJNUMB}}", "")
        if expected and not _value_in_note(searchable, expected):
            issues.append(_missing_value_issue("PROJNUMB", expected))

    tu_checks = (
        ("APPLICANT", "{{APPLICANT}}"),
        ("ADRESS", "{{ADRESS}}"),
        ("ADDRESS", "{{ADDRESS}}"),
        ("KADNUMBER", "{{KADNUMBER}}"),
        ("DATE", "{{DATE}}"),
        ("FAZE", "{{FAZE}}"),
        ("SECH_KABEL", "{{SECH_KABEL}}"),
        ("OTKUDASTROIT", "{{OTKUDASTROIT}}"),
        ("TP_NAME", "{{TP_NAME}}"),
    )
    checked_address = False
    for field, placeholder in tu_checks:
        if field == "ADDRESS" and checked_address:
            continue
        expected = str(replacement_map.get(placeholder, "") or "").strip()
        if not expected:
            continue
        if field in {"ADRESS", "ADDRESS"}:
            checked_address = True
            if not _address_in_note(searchable, expected):
                issues.append(_missing_value_issue(field, expected))
            continue
        if not _value_in_note(searchable, expected):
            issues.append(_missing_value_issue(field, expected))

    branch_line = str(replacement_map.get("{{BRANCH_ARMATURE_LINE}}", "") or "").strip()
    if branch_line and not _value_in_note(searchable, branch_line):
        issues.append(_missing_value_issue("BRANCH_ARMATURE_LINE", branch_line))

    if tu_data.get("requires_komapparat_template"):
        if "коммутационного аппарата" not in searchable:
            issues.append(
                ValidationIssue(
                    category="note",
                    severity="error",
                    code="NOTE_KOMAPPARAT_MISSING",
                    message=(
                        "В ТУ требуется подключение от коммутационного аппарата, "
                        "но в записке не найдена фраза про «коммутационный аппарат»."
                    ),
                    field="BRANCH_ARMATURE_LINE",
                    location=NOTE_FIELD_LOCATIONS["BRANCH_ARMATURE_LINE"],
                )
            )
        elif branch_line and "коммутационного аппарата" not in branch_line.lower():
            issues.append(
                ValidationIssue(
                    category="note",
                    severity="error",
                    code="NOTE_KOMAPPARAT_TEXT",
                    message=(
                        "В ТУ указан коммутационный аппарат, но строка ответвительной арматуры "
                        f"не соответствует: ожидалось «{branch_line[:120]}»."
                    ),
                    field="BRANCH_ARMATURE_LINE",
                    location=NOTE_FIELD_LOCATIONS["BRANCH_ARMATURE_LINE"],
                )
            )

    route_sheet = str(replacement_map.get("{{ROUTE_PLAN_SHEET}}", "") or materials_data.get("ROUTE_PLAN_SHEET", "") or "").strip()
    total_sheets = str(replacement_map.get("{{TOTAL_SHEETS}}", "") or materials_data.get("TOTAL_SHEETS", "") or "").strip()
    a3_count = materials_data.get("A3_SHEET_COUNT")

    if route_sheet and not _sheet_reference_in_note(searchable, route_sheet):
        issues.append(
            _missing_value_issue(
                "ROUTE_PLAN_SHEET",
                f"лист {route_sheet} (план трассы, по {a3_count} лист(ам) А3 на плане)",
            )
        )
    if total_sheets and not _value_in_note(searchable, total_sheets):
        issues.append(_missing_value_issue("TOTAL_SHEETS", f"{total_sheets} листов"))

    for field in NOTE_VALUE_CHECK_FIELDS:
        placeholder = f"{{{{{field}}}}}"
        expected = replacement_map.get(placeholder)
        if expected in (None, ""):
            expected = materials_data.get(field)
        if expected in (None, ""):
            continue
        if not _value_in_note(searchable, expected):
            issues.append(_missing_value_issue(field, expected))

    return issues


def _missing_value_issue(
    field: str,
    expected: Any,
    message: str | None = None,
    severity: str = "error",
) -> ValidationIssue:
    location = NOTE_FIELD_LOCATIONS.get(field, "записка")
    label = TU_FIELD_LABELS.get(field, field)
    if message is None:
        message = f"Не найдено значение «{expected}» ({label})."
    return ValidationIssue(
        category="note",
        severity=severity,
        code=f"NOTE_VALUE_MISSING_{field}",
        message=message,
        field=field,
        location=location,
    )


def _address_in_note(searchable: str, address: str) -> bool:
    if not address:
        return False
    if _value_in_note(searchable, address):
        return True
    abbreviated = abbreviate_address_display_terms(address)
    if _value_in_note(searchable, abbreviated):
        return True
    for part in re.split(r"[,;]", abbreviated):
        cleaned = part.strip().strip("«»")
        if len(cleaned) >= 8 and cleaned.lower() in searchable:
            return True
    return False


def _sheet_reference_in_note(searchable: str, route_sheet: str) -> bool:
    if _value_in_note(searchable, route_sheet):
        return True
    if "план трассы" in searchable and route_sheet.lower() in searchable:
        return True
    if "-" in route_sheet:
        start, end = route_sheet.split("-", 1)
        return start in searchable and end in searchable
    return False


def _armature_info_issues(armature: dict[str, Any]) -> list[ValidationIssue]:
    return []


def _normalize_search_text(value: str) -> str:
    text = value.lower().replace("\u00a0", " ")
    text = text.replace("×", "x").replace("х", "x")
    return re.sub(r"\s+", " ", text)


def _value_in_note(searchable_text: str, expected: Any) -> bool:
    for candidate in _value_search_candidates(expected):
        if candidate and candidate.lower() in searchable_text:
            return True
    return False


def _value_search_candidates(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, float):
        rounded = round(value, 3)
        candidates = [str(value), f"{value:.3f}".rstrip("0").rstrip(".")]
        if rounded.is_integer():
            candidates.append(str(int(rounded)))
        candidates.append(str(rounded).replace(".", ","))
        return list(dict.fromkeys(candidates))
    text = str(value).strip()
    if not text:
        return []
    return list(dict.fromkeys([text, text.replace(".", ",")]))


def _issues_from_replacement_map(
    replacement_map: dict[str, str],
    placeholders: list[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    found = set(placeholders)
    for placeholder in sorted(found):
        field = placeholder.strip("{}")
        if placeholder not in replacement_map:
            continue
        value = str(replacement_map.get(placeholder, "") or "").strip()
        if not value and field in {*TU_FIELDS, "PROJNUMB"}:
            label = TU_FIELD_LABELS.get(field, field)
            issues.append(
                ValidationIssue(
                    category="cross",
                    severity="warning",
                    code="CROSS_EMPTY_VALUE",
                    message=f"Для {placeholder} не удалось подготовить значение ({label}).",
                    field=field,
                )
            )
    proj = replacement_map.get("{{PROJNUMB}}", "")
    if "{{PROJNUMB}}" in found and proj:
        pass
    return issues


def _public_tu_summary(tu_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_file": tu_data.get("source_file"),
        "applicant": tu_data.get("APPLICANT"),
        "address": tu_data.get("ADRESS"),
        "power_kw": tu_data.get("POWER_KW"),
        "phase": tu_data.get("FAZE"),
        "cable_section": tu_data.get("SECH_KABEL"),
        "tp_name": tu_data.get("TP_NAME"),
        "requires_komapparat_template": tu_data.get("requires_komapparat_template"),
    }


def _public_plan_summary(plan_data: dict[str, Any]) -> dict[str, Any]:
    supports = plan_data.get("supports", {})
    return {
        "source_file": plan_data.get("source_file"),
        "line_length_m": plan_data.get("line_length_m"),
        "supports": supports,
        "grounding_count": plan_data.get("grounding_count"),
        "a3_sheet_count": plan_data.get("a3_sheet_count"),
        "supports_total": sum(int(supports.get(key, 0) or 0) for key in ("P23", "A23", "YA23", "K21")),
    }
