"""AI Engineer — пост-проверка готового проекта.

Модуль НЕ участвует в генерации, расчётах и выборе шаблонов.
Он только читает уже построенный результат и формирует рекомендации.
Проект никогда не изменяется.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from backend.core.ai_engineer_handbook import (
    chat_system_prompt,
    human_project_facts,
    is_generic_local_chat,
    local_chat_reply,
    sanitize_chat_reply,
)
from backend.core.network import run_with_timeout
from backend.core.plan_geometry_audit import audit_plan_geometry, expected_groundings_04kv


CHECK_ITEMS = (
    ("tu", "ТУ"),
    ("plan", "План"),
    ("note", "Записка"),
    ("armature", "Арматура"),
    ("supports", "Опоры"),
    ("cable", "Кабель"),
    ("grounding", "Заземления"),
    ("sections", "Сечения"),
)


def run_ai_engineer_review(
    *,
    project_data: dict[str, Any],
    replacement_map: dict[str, str],
    cad_result: dict[str, Any] | None = None,
    pipeline_warnings: list[str] | None = None,
    note_path: Path | None = None,
    plan_path: Path | None = None,
    tu_text: str = "",
    enable_llm: bool = True,
) -> dict[str, Any]:
    """Строит инженерное заключение по готовому проекту."""
    cad_result = cad_result or {}
    pipeline_warnings = list(pipeline_warnings or [])
    geometry_audit = audit_plan_geometry(plan_path)

    findings = _collect_rule_findings(
        project_data=project_data,
        replacement_map=replacement_map,
        cad_result=cad_result,
        pipeline_warnings=pipeline_warnings,
        note_path=note_path,
        tu_text=tu_text,
        geometry_audit=geometry_audit,
    )
    mode = "rules"

    if enable_llm and _llm_configured():
        llm_findings = _enrich_with_llm(
            project_data=project_data,
            replacement_map=replacement_map,
            cad_result=cad_result,
            pipeline_warnings=pipeline_warnings,
            existing_findings=findings,
            tu_text=tu_text,
            geometry_audit=geometry_audit,
        )
        if llm_findings:
            findings.extend(llm_findings)
            mode = "rules+llm"

    findings = _drop_llm_geometry_guesses(findings, geometry_audit)
    findings = _dedupe_findings(findings)
    checked = _build_checked_items(
        project_data=project_data,
        replacement_map=replacement_map,
        cad_result=cad_result,
        findings=findings,
    )
    score = _compute_score(checked=checked, findings=findings, cad_result=cad_result)
    critical = [item for item in findings if item.get("severity") == "critical"]
    warnings_list = [item for item in findings if item.get("severity") == "warning"]
    soft_recs = [item for item in findings if item.get("severity") == "recommendation"]

    if critical:
        status = "critical"
        summary = f"Найдено критических замечаний: {len(critical)}"
    elif warnings_list:
        status = "warnings"
        summary = _summarize_warnings(warnings_list)
    elif soft_recs:
        status = "warnings"
        summary = (
            f"{len(soft_recs)} рекомендация"
            if len(soft_recs) == 1
            else f"{len(soft_recs)} рекомендаций"
        )
    else:
        status = "ok"
        summary = "Критических замечаний нет"

    report = {
        "module": "AI Engineer",
        "readonly": True,
        "does_not_modify_project": True,
        "mode": mode,
        "project_number": str(project_data.get("project_number", "") or ""),
        "project_type": str(project_data.get("project_type", "") or ""),
        "score": score,
        "status": status,
        "summary": summary,
        "checked": checked,
        "findings": findings,
        "geometry_audit": geometry_audit,
        "stats": {
            "critical": len(critical),
            "warnings": len(warnings_list),
            "recommendations": len(soft_recs),
            "checked_ok": sum(1 for item in checked if item.get("ok")),
            "checked_total": len(checked),
        },
        "disclaimer": (
            "Все замечания — рекомендации для проектировщика. "
            "AI Engineer не изменяет проект и не заменяет инженерные решения программы."
        ),
        "placement_notes": _placement_notes(geometry_audit),
    }
    return report


def load_ai_engineer_report(data_dir: Path) -> dict[str, Any] | None:
    path = Path(data_dir) / "ai_engineer_report.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_ai_engineer_report(data_dir: Path, report: dict[str, Any]) -> Path:
    path = Path(data_dir) / "ai_engineer_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _collect_rule_findings(
    *,
    project_data: dict[str, Any],
    replacement_map: dict[str, str],
    cad_result: dict[str, Any],
    pipeline_warnings: list[str],
    note_path: Path | None,
    tu_text: str,
    geometry_audit: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    plan_data = dict(project_data.get("plan_data") or {})
    project_type = str(project_data.get("project_type", "") or "")
    is_10kv = project_type == "10kv"
    geometry_audit = geometry_audit or {}

    unresolved = list(cad_result.get("unresolved_placeholders") or [])
    if unresolved:
        findings.append(
            _finding(
                "unresolved_placeholders",
                "critical",
                "note",
                "В записке остались незаменённые placeholders",
                f"Не заменено: {', '.join(str(item) for item in unresolved[:12])}",
                "Это текстовые метки вида {{ПОЛЕ}}, которые программа должна была заменить на реальные значения. "
                "Если они остались, в записке видны «дыры». Откройте записку и проверьте эти поля вручную.",
            )
        )

    if note_path is not None and not Path(note_path).exists():
        findings.append(
            _finding(
                "note_missing",
                "critical",
                "note",
                "Файл записки не найден",
                "Генерация завершилась без note_result.dwg.",
                "Без файла записки комплект нельзя считать готовым. Запустите генерацию ещё раз.",
            )
        )

    # Главные инженерные рекомендации — по геометрии плана.
    findings.extend(_geometry_findings(plan_data, geometry_audit, is_10kv=is_10kv))

    # Только действительно важные предупреждения пайплайна (не «проверьте РЛК»).
    for warning in pipeline_warnings:
        text = str(warning or "").strip()
        if not text:
            continue
        lower = text.casefold()
        if "вне основной трассы" in lower or "вне трассы" in lower:
            # уже покрыто геометрическим аудитом
            continue
        if "placeholder" in lower or "{{" in text:
            findings.append(
                _finding(
                    f"pipeline_{abs(hash(text)) % 10_000_000}",
                    "warning",
                    "note",
                    "Проблема с шаблоном / placeholders",
                    text,
                    "В шаблоне записки есть поля, которые система не смогла уверенно заполнить. "
                    "Это стоит проверить глазами перед выдачей комплекта.",
                )
            )
        elif "полилини" in lower:
            findings.append(
                _finding(
                    f"pipeline_{abs(hash(text)) % 10_000_000}",
                    "recommendation",
                    "plan",
                    "На плане несколько полилиний трассы",
                    text,
                    "Программа выбирает одну основную линию. Если выбрана не та, длина и материалы могут быть неточными. "
                    "Убедитесь, что на плане одна явная трасса ВЛ 0,4 кВ.",
                )
            )

    supports = dict(plan_data.get("supports") or {})
    total_04 = sum(int(supports.get(key, 0) or 0) for key in ("P23", "PP23", "A23", "YA23", "K21"))
    if not is_10kv and total_04 == 0:
        findings.append(
            _finding(
                "no_supports_04",
                "warning",
                "supports",
                "На плане 0,4 кВ не найдены опоры",
                "Счётчики П23/ПП23/А23/УА23*/К21 равны нулю.",
                "Опоры ищутся по блокам AutoCAD. Если блоки названы иначе или стоят на другом слое, "
                "программа их не увидит — проверьте имена блоков на плане.",
            )
        )

    tu_data = dict(project_data.get("tu_data") or {})
    pp23 = int(supports.get("PP23", 0) or 0)
    if not is_10kv and tu_data.get("vl_in_10kv_gabarit") and pp23 == 0:
        findings.append(
            _finding(
                "pp23_missing_for_10kv_gabarit",
                "warning",
                "supports",
                "В ТУ участок в габаритах 10 кВ, а опор ПП23 на плане нет",
                "В технических условиях есть фраза про строительство в габаритах 10 кВ.",
                "На таком участке ставят промежуточные опоры ПП23 на слое PP23: арматура как у П23, "
                "стойка СВ110-5 вместо СВ95-3. Проверьте слой и подпись блока.",
                why=(
                    "ТУ требует часть ВЛИ 0,4 кВ в габаритах 10 кВ. Для этого на плане нужны опоры ПП23, "
                    "а не обычные П23 со стойкой СВ95-3."
                ),
                how="Поставьте опоры ПП23 на слой PP23 вдоль участка в габаритах 10 кВ и пересчитайте проект.",
            )
        )

    if not str(replacement_map.get("{{SECH_KABEL}}", "") or "").strip() and not is_10kv:
        findings.append(
            _finding(
                "cable_missing",
                "warning",
                "cable",
                "Сечение кабеля не заполнено",
                "В карте замен пустое {{SECH_KABEL}}.",
                "Сечение должно прийти из ТУ или из ручного выбора провода. Без него в записке останется пустая ячейка.",
            )
        )

    _ = tu_text  # reserved for future text heuristics
    return findings


def _summarize_warnings(warnings_list: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    ids = [str(item.get("id") or "") for item in warnings_list]
    if any(item.startswith("support_off_route") or item.startswith("grounding_off_route") for item in ids):
        parts.append("объект вне трассы")
    if any(item in {"no_grounding_on_04", "no_supports_04", "pp23_missing_for_10kv_gabarit"} or item.startswith("missing_") for item in ids):
        parts.append("отсутствует обязательный объект")
    if any("gap_" in item or item.startswith("grounding_spacing") for item in ids):
        parts.append("подозрительное расстояние")
    if any(item.startswith("duplicate_") for item in ids):
        parts.append("дублирование объектов")
    if any(item.startswith("support_number_sequence") for item in ids):
        parts.append("номера опор не по порядку")
    if any(item.startswith("support_wrong_angle") for item in ids):
        parts.append("опора не подходит к углу трассы")
    if parts:
        return "Нужно проверить: " + ", ".join(parts)
    if len(warnings_list) == 1:
        return "1 предупреждение"
    return f"{len(warnings_list)} предупреждения"


def _geometry_findings(
    plan_data: dict[str, Any],
    geometry_audit: dict[str, Any],
    *,
    is_10kv: bool,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    # Количество и длина — как у основного расчёта (plan_data), не «угадываем» заново.
    if is_10kv:
        length_04 = float(plan_data.get("line_length_04kv_m") or 0)
    else:
        length_04 = float(plan_data.get("line_length_m") or 0)
    if length_04 <= 0:
        length_04 = float(geometry_audit.get("line_length_04_m") or 0)

    grounding_count = int(plan_data.get("grounding_count", 0) or 0)
    if grounding_count <= 0 and geometry_audit.get("available"):
        grounding_count = int(geometry_audit.get("grounding_count", 0) or 0)

    expected = expected_groundings_04kv(length_04)
    touch_m = float(geometry_audit.get("touch_tolerance_m") or 1.0)

    # Без DXF нельзя сказать «замечаний нет» — иначе UI показывает ложные 99.9%.
    # Норму по количеству заземлений всё равно считаем из plan_data.
    if not geometry_audit.get("available"):
        findings.append(
            _finding(
                "geometry_plan_unavailable",
                "warning",
                "plan",
                "Геометрия плана не проверена — DXF недоступен",
                "AI Engineer не смог открыть DXF-план для проверки опор и заземлений на полилинии.",
                "Без файла плана нельзя проверить, касаются ли опоры и заземления трассы. "
                "Перезапустите генерацию или откройте вкладку AI Engineer ещё раз после готовности проекта. "
                "Рейтинг без этой проверки не означает, что план исправен.",
                why=(
                    "Проверка геометрии не выполнена: DXF-план недоступен. "
                    "Допустимое расстояние до полилинии для касания — "
                    f"{touch_m:g} м, но без чертежа его нельзя измерить."
                ),
                how="Перезапустите генерацию с DXF-планом или откройте вкладку AI Engineer после готовности проекта.",
            )
        )

    length_10 = float(plan_data.get("line_length_10kv_m") or 0)
    if length_10 <= 0:
        length_10 = float(geometry_audit.get("line_length_10_m") or 0)
    supports_04 = int(geometry_audit.get("supports_04_count") or 0)
    supports_10 = int(geometry_audit.get("supports_10_count") or 0)
    if supports_04 <= 0:
        supports_04 = sum(int((plan_data.get("supports") or {}).get(key, 0) or 0) for key in ("P23", "PP23", "A23", "YA23", "K21"))
    if supports_10 <= 0:
        supports_10 = sum(
            int((plan_data.get("supports_10kv") or {}).get(key, 0) or 0) for key in ("P20", "A20", "UA", "UP", "ARLK")
        )
    max_gap_04 = float(geometry_audit.get("max_support_gap_04_m") or 42)
    max_gap_10 = float(geometry_audit.get("max_support_gap_10_m") or 70)
    max_gap_ground = float(geometry_audit.get("max_grounding_gap_m") or 100)

    for item in geometry_audit.get("supports_off_route") or []:
        name = item.get("display_name") or "Опора"
        distance = item.get("distance_m")
        voltage_label = "10 кВ" if str(item.get("voltage") or "") == "10" else "0,4 кВ"
        titled = name[0].upper() + name[1:] if name else "Опора"
        why = (
            f"{titled} находится на расстоянии {distance} м от полилинии {voltage_label}. "
            f"Допустимое расстояние для данной проверки — {touch_m:g} м "
            "(блок должен касаться трассы)."
        )
        findings.append(
            _finding(
                f"support_off_route_{item.get('support_type')}_{item.get('number')}_{distance}",
                "warning",
                "supports",
                f"{titled} не на полилинии {voltage_label} — исправьте на плане",
                f"До полилинии {voltage_label} ≈ {distance} м (нужно касание, допуск {touch_m:g} м).",
                f"Опора должна стоять прямо на полилинии {voltage_label}. "
                f"Сейчас {name} смещена примерно на {distance} м. "
                "Подвиньте опору на трассу или уберите лишний блок. "
                "Расчёт материалов при этом уже выполнен и не меняется.",
                why=why,
                how=(
                    f"Подвиньте {name} на полилинию {voltage_label} "
                    f"(касание, до {touch_m:g} м) или удалите лишний блок."
                ),
            )
        )

    off_grounds = list(geometry_audit.get("groundings_off_route") or [])
    on_grounds = int(geometry_audit.get("groundings_on_route", 0) or 0)
    for item in off_grounds:
        label = item.get("label") or f"Заземление #{item.get('index')}"
        distance = item.get("distance_m")
        why = (
            f"{label} находится на расстоянии {distance} м от полилинии 0,4 кВ. "
            f"Допустимое расстояние для данной проверки — {touch_m:g} м."
        )
        findings.append(
            _finding(
                f"grounding_off_route_{item.get('index')}_{distance}",
                "warning",
                "grounding",
                f"{label} не на полилинии 0,4 кВ — исправьте на плане",
                f"До полилинии 0,4 кВ ≈ {distance} м (нужно касание, допуск {touch_m:g} м).",
                f"Заземление должно стоять на полилинии 0,4 кВ (обычно у опоры трассы). "
                f"Сейчас «{label}» не касается линии — примерно {distance} м в стороне. "
                f"Всего заземлений на плане (как в расчёте): {grounding_count}, "
                f"из них касается трассы 0,4 кВ: {on_grounds}.",
                why=why,
                how=(
                    f"Подвиньте «{label}» на полилинию 0,4 кВ "
                    f"(касание, до {touch_m:g} м) или поставьте заземление у опоры на трассе."
                ),
            )
        )

    if length_04 > 0 and supports_04 == 0:
        findings.append(
            _finding(
                "missing_supports_04",
                "warning",
                "supports",
                "Отсутствует обязательный объект: нет опор 0,4 кВ",
                f"Есть трасса 0,4 кВ ≈ {length_04:.0f} м, но опоры П23/А23/УА23*/К21 не найдены.",
                "На плане 0,4 кВ должны быть блоки опор на полилинии. "
                "Проверьте имена блоков и слой трассы.",
                why=(
                    f"Полилиния 0,4 кВ есть (≈ {length_04:.0f} м), а опор 0,4 кВ на плане 0. "
                    "Для этой проверки обязателен хотя бы один блок опоры на трассе."
                ),
                how="Добавьте на полилинию 0,4 кВ опоры нужного типа: П23/А23/К21 на прямых, УА23* на поворотах до 90°.",
            )
        )
    if is_10kv and length_10 > 0 and supports_10 == 0:
        findings.append(
            _finding(
                "missing_supports_10",
                "warning",
                "supports",
                "Отсутствует обязательный объект: нет опор 10 кВ",
                f"Есть трасса 10 кВ ≈ {length_10:.0f} м, но опоры П20/А20/УА20/РЛК не найдены.",
                "На плане 10 кВ должны быть опоры на полилинии слоя 10. Проверьте блоки и слои.",
                why=(
                    f"Полилиния 10 кВ есть (≈ {length_10:.0f} м), а опор 10 кВ на плане 0. "
                    "Для этой проверки обязателен хотя бы один блок опоры 10 кВ на трассе."
                ),
                how="Добавьте опоры 10 кВ на полилинию слоя 10 и проверьте имена блоков.",
            )
        )
    if length_04 > 0 and grounding_count == 0:
        findings.append(
            _finding(
                "missing_grounding",
                "warning",
                "grounding",
                "Отсутствует обязательный объект: нет заземлений",
                f"Длина линии 0,4 кВ ≈ {length_04:.0f} м, в расчёте заземлений: 0.",
                "При наличии трассы 0,4 кВ заземления обычно есть отдельными блоками на полилинии.",
                why=(
                    f"Трасса 0,4 кВ ≈ {length_04:.0f} м, заземлений не найдено. "
                    "Для этой проверки нужен минимум 1 блок заземления на полилинии "
                    f"(ориентир — не реже чем раз в {max_gap_ground:g} м)."
                ),
                how="Поставьте на полилинию 0,4 кВ хотя бы одно заземление (ориентир — не реже чем раз в 100 м).",
            )
        )
    elif length_04 > 0 and expected > 0 and grounding_count < expected:
        missing = expected - grounding_count
        findings.append(
            _finding(
                "grounding_spacing_04",
                "warning",
                "grounding",
                f"Мало заземлений на трассе 0,4 кВ: в расчёте {grounding_count}, нужно около {expected}",
                (
                    f"Длина полилинии 0,4 кВ ≈ {length_04:.0f} м. "
                    f"Норма — примерно одно заземление на каждые {max_gap_ground:g} м."
                ),
                (
                    f"Длина участка 0,4 кВ ≈ {length_04:.0f} м → ориентир {expected} шт. "
                    f"На плане {grounding_count}. Рекомендуется добавить ещё {missing}."
                ),
                why=(
                    f"Найдено заземлений: {grounding_count}. "
                    f"При длине {length_04:.0f} м и шаге {max_gap_ground:g} м нужно около {expected}."
                ),
                how=f"Добавьте ещё {missing} заземлений на трассу 0,4 кВ с шагом не больше {max_gap_ground:g} м.",
            )
        )

    for gap in geometry_audit.get("support_gaps_04") or []:
        findings.append(
            _finding(
                f"gap_support_04_{gap.get('from_name')}_{gap.get('to_name')}_{gap.get('distance_m')}",
                "warning",
                "supports",
                f"Подозрительное расстояние между опорами 0,4 кВ: {gap.get('distance_m')} м",
                f"{gap.get('from_name')} — {gap.get('to_name')}: {gap.get('distance_m')} м (норма ≤ {max_gap_04:g} м).",
                "Проверьте, не пропущена ли опора на плане или не съехал ли блок с трассы.",
                why=(
                    f"Между «{gap.get('from_name')}» и «{gap.get('to_name')}» "
                    f"{gap.get('distance_m')} м вдоль трассы 0,4 кВ. "
                    f"Допустимое расстояние для данной проверки — {max_gap_04:g} м."
                ),
                how=(
                    f"Уменьшите расстояние между опорами 0,4 кВ до {max_gap_04:g} м: "
                    "добавьте промежуточную опору или подвиньте существующие ближе."
                ),
            )
        )
    for gap in geometry_audit.get("support_gaps_10") or []:
        findings.append(
            _finding(
                f"gap_support_10_{gap.get('from_name')}_{gap.get('to_name')}_{gap.get('distance_m')}",
                "warning",
                "supports",
                f"Подозрительное расстояние между опорами 10 кВ: {gap.get('distance_m')} м",
                f"{gap.get('from_name')} — {gap.get('to_name')}: {gap.get('distance_m')} м (норма ≤ {max_gap_10:g} м).",
                "Проверьте шаг опор 10 кВ на плане.",
                why=(
                    f"Между «{gap.get('from_name')}» и «{gap.get('to_name')}» "
                    f"{gap.get('distance_m')} м вдоль трассы 10 кВ. "
                    f"Допустимое расстояние для данной проверки — {max_gap_10:g} м."
                ),
                how=(
                    f"Уменьшите расстояние между опорами 10 кВ до {max_gap_10:g} м: "
                    "добавьте промежуточную опору или подвиньте существующие ближе."
                ),
            )
        )
    for gap in geometry_audit.get("grounding_gaps") or []:
        findings.append(
            _finding(
                f"gap_grounding_{gap.get('from_name')}_{gap.get('to_name')}_{gap.get('distance_m')}",
                "warning",
                "grounding",
                f"Подозрительное расстояние между заземлениями: {gap.get('distance_m')} м",
                f"{gap.get('from_name')} — {gap.get('to_name')}: {gap.get('distance_m')} м (норма ≤ {max_gap_ground:g} м).",
                "Заземления на ВЛ 0,4 кВ ставят примерно через каждые 100 м трассы.",
                why=(
                    f"Между «{gap.get('from_name')}» и «{gap.get('to_name')}» "
                    f"{gap.get('distance_m')} м. "
                    f"Допустимое расстояние для данной проверки — {max_gap_ground:g} м."
                ),
                how=(
                    f"Уменьшите расстояние между заземлениями до {max_gap_ground:g} м: "
                    "добавьте заземление на участке между ними."
                ),
            )
        )

    for item in geometry_audit.get("duplicate_supports") or []:
        number = item.get("number")
        count = item.get("count")
        names = ", ".join(str(name) for name in (item.get("names") or [])[:4])
        findings.append(
            _finding(
                f"duplicate_support_{number}_{count}",
                "warning",
                "supports",
                f"Дублирование объектов: опора №{number} встречается {count} раза",
                f"На плане несколько блоков с одним номером: {names}.",
                "Оставьте один блок с этим номером или перенумеруйте дубликат.",
                why=(
                    f"Номер опоры №{number} найден {count} раза ({names}). "
                    "Для данной проверки номер опоры должен быть уникальным."
                ),
                how=f"Оставьте один блок с номером №{number}, а дубликат удалите или перенумеруйте.",
            )
        )

    for item in geometry_audit.get("number_sequence_issues") or []:
        voltage = str(item.get("voltage") or "04")
        voltage_label = "10 кВ" if voltage == "10" else "0,4 кВ"
        along = item.get("along") or ""
        expected = item.get("expected") or ""
        direction = item.get("direction") or "по возрастанию"
        first_break = (item.get("breaks") or [{}])[0]
        from_name = first_break.get("from_name") or "опора"
        to_name = first_break.get("to_name") or "опора"
        expected_next = first_break.get("expected_next")
        findings.append(
            _finding(
                f"support_number_sequence_{voltage}_{along}",
                "warning",
                "supports",
                f"Номера опор {voltage_label} идут не по порядку вдоль трассы",
                f"Вдоль полилинии: {along}. Ожидается {direction}: {expected}.",
                "Номера опор должны расти или убывать подряд по ходу трассы, как №1, №2, №3.",
                why=(
                    f"По порядку вдоль трассы {voltage_label} сейчас {along}. "
                    f"Правильная последовательность {direction}: {expected}."
                ),
                how=(
                    f"Перенумеруйте блоки на плане. После «{from_name}» должна быть "
                    f"опора №{expected_next}, а не «{to_name}»."
                    if expected_next is not None
                    else "Перенумеруйте опоры подряд вдоль полилинии: №1, №2, №3…"
                ),
            )
        )

    for item in geometry_audit.get("wrong_angle_supports") or []:
        name = item.get("display_name") or "Опора"
        titled = name[0].upper() + name[1:] if name else "Опора"
        angle = item.get("angle_deg")
        allowed = item.get("allowed_max_deg")
        suggested = item.get("suggested") or "УА23*"
        type_code = str(item.get("support_type") or "")
        type_label = {
            "P23": "П23",
            "PP23": "ПП23",
            "A23": "А23",
            "K21": "К21",
            "YA23": "УА23*",
        }.get(type_code, type_code)
        findings.append(
            _finding(
                f"support_wrong_angle_{type_code}_{item.get('number')}_{angle}",
                "warning",
                "supports",
                f"Неверный тип опоры на угле трассы: {titled}",
                (
                    f"{titled} стоит на повороте ≈ {angle}°. "
                    f"Для {type_label} допустимо до {allowed:g}°."
                ),
                (
                    "Тип опоры 0,4 кВ должен соответствовать геометрии полилинии: "
                    "П23, А23 и К21 — только на прямой (угол ≈ 0°), УА23* — на повороте до 90°."
                ),
                why=(
                    f"{titled} находится на угле поворота полилинии ≈ {angle}°. "
                    f"Допустимый угол для {type_label} — до {allowed:g}°. "
                    f"Для этого места подходит: {suggested}."
                ),
                how=(
                    f"Замените {type_label} на подходящий тип ({suggested}) "
                    f"или измените геометрию полилинии, чтобы угол был не больше {allowed:g}°."
                ),
            )
        )

    return findings


def _finding(
    finding_id: str,
    severity: str,
    category: str,
    title: str,
    reason: str,
    detail: str,
    why: str = "",
    how: str = "",
) -> dict[str, Any]:
    explanation = why or detail
    fix = how or (
        "Проверьте объект на плане и исправьте вручную. AI Engineer проект не меняет."
    )
    return {
        "id": finding_id,
        "severity": severity,
        "category": category,
        "title": title,
        "reason": reason,
        "detail": explanation,
        "why": explanation,
        "how": fix,
        "action": "Почему?",
        "fix_action": "Как решить?",
    }


def _build_checked_items(
    *,
    project_data: dict[str, Any],
    replacement_map: dict[str, str],
    cad_result: dict[str, Any],
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tu_data = dict(project_data.get("tu_data") or {})
    plan_data = dict(project_data.get("plan_data") or {})
    materials = dict(project_data.get("materials_data") or {})
    unresolved = list(cad_result.get("unresolved_placeholders") or [])
    finding_cats = {str(item.get("category") or "") for item in findings if item.get("severity") in {"critical", "warning"}}

    supports = dict(plan_data.get("supports") or {})
    supports_10 = dict(plan_data.get("supports_10kv") or {})
    support_total = sum(int(supports.get(key, 0) or 0) for key in ("P23", "PP23", "A23", "YA23", "K21"))
    support_total += sum(int(supports_10.get(key, 0) or 0) for key in ("P20", "A20", "UA", "UP", "ARLK"))

    checks = {
        "tu": bool(tu_data),
        "plan": bool(plan_data.get("line_length_m") or plan_data.get("line_length_10kv_m") or support_total),
        "note": not unresolved,
        "armature": bool(materials) or bool(project_data.get("materials_10kv_data")),
        "supports": support_total > 0,
        "cable": bool(replacement_map.get("{{SECH_KABEL}}") or replacement_map.get("{{SECH_KABEL_10kV}}")),
        "grounding": True if project_data.get("project_type") == "10kv" else int(plan_data.get("grounding_count", 0) or 0) >= 0,
        "sections": bool(
            replacement_map.get("{{SECH_KABEL}}")
            or replacement_map.get("{{SECH_SIP4}}")
            or replacement_map.get("{{SECH_KABEL_10kV}}")
        ),
    }
    result = []
    for item_id, label in CHECK_ITEMS:
        has_problem = item_id in finding_cats
        ok = bool(checks.get(item_id)) and not has_problem
        result.append(
            {
                "id": item_id,
                "label": label,
                "ok": ok,
                "attention": has_problem,
            }
        )
    return result


def _compute_score(
    *,
    checked: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    cad_result: dict[str, Any],
) -> float:
    base = 100.0
    ok_ratio = 0.0
    if checked:
        ok_ratio = sum(1 for item in checked if item.get("ok")) / len(checked)
    base = 70.0 + 30.0 * ok_ratio

    for item in findings:
        severity = item.get("severity")
        if severity == "critical":
            base -= 12.0
        elif severity == "warning":
            base -= 4.0
        else:
            base -= 1.2

    unresolved = list((cad_result or {}).get("unresolved_placeholders") or [])
    base -= min(20.0, 3.0 * len(unresolved))
    return round(max(55.0, min(99.9, base)), 1)


def _normalize_phase(value: str) -> str:
    text = value.casefold().replace("ё", "е")
    if "трехфаз" in text or "трёхфаз" in text:
        return "3"
    if "однофаз" in text:
        return "1"
    return text


def _digits_only(value: str) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    severity_rank = {"critical": 0, "warning": 1, "recommendation": 2, "info": 3}
    ordered = sorted(findings, key=lambda item: severity_rank.get(str(item.get("severity")), 9))
    for item in ordered:
        key = f"{item.get('id')}|{item.get('title')}|{item.get('reason')}"
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def llm_configured() -> bool:
    return _llm_configured()


def _llm_configured() -> bool:
    return bool(_llm_settings()["api_key"])


def _llm_settings() -> dict[str, str]:
    api_key = (
        os.environ.get("AI_ENGINEER_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
    )
    base_url = (
        os.environ.get("AI_ENGINEER_BASE_URL", "").strip()
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or "https://api.aitunnel.ru/v1"
    ).rstrip("/")
    model = (
        os.environ.get("AI_ENGINEER_MODEL", "").strip()
        or "gpt-5.6-luna-pro"
    )
    return {"api_key": api_key, "base_url": base_url, "model": model}


CHAT_HISTORY_NAME = "ai_engineer_chat.json"


def load_ai_engineer_chat(data_dir: Path) -> list[dict[str, str]]:
    path = Path(data_dir) / CHAT_HISTORY_NAME
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    messages = payload.get("messages") if isinstance(payload, dict) else payload
    if not isinstance(messages, list):
        return []
    result: list[dict[str, str]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        result.append({"role": role, "content": content})
    return result[-40:]


def save_ai_engineer_chat(data_dir: Path, messages: list[dict[str, str]]) -> Path:
    path = Path(data_dir) / CHAT_HISTORY_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"messages": messages[-40:]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def chat_with_project(
    *,
    message: str,
    project_data: dict[str, Any],
    replacement_map: dict[str, str],
    report: dict[str, Any] | None,
    cad_result: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Ответ чат-бота. С проектом — по фактам запуска; без проекта — по нормам. Проект не изменяется."""
    text = str(message or "").strip()
    if not text:
        return {"ok": False, "error": "Пустой вопрос.", "reply": ""}
    has_project = bool(project_data) and bool(replacement_map)
    try:
        if has_project:
            facts = human_project_facts(
                project_data=project_data,
                replacement_map=replacement_map,
                report=report or {},
                cad_result=cad_result or {},
            )
        else:
            facts = {
                "статус": "проект ещё не сформирован",
                "что_можно": "нормы ВЛ, арматура, опоры, пролёты, ПП23, как пользоваться программой",
            }
        local_reply = local_chat_reply(text, facts, has_project=has_project, history=history)
    except Exception:
        local_reply = (
            "Могу ответить по нормам ВЛ 0,4 и 10 кВ: опоры, арматура, пролёты, заземления. "
            "Спросите, например: «сколько F207 на А23»."
        )
        facts = {}
        has_project = False

    settings = _llm_settings()
    if not settings["api_key"] or not is_generic_local_chat(local_reply):
        return {"ok": True, "reply": local_reply, "model": "rules", "error": ""}

    def _ask_llm() -> str:
        return _llm_chat_reply(
            text,
            facts=facts,
            has_project=has_project,
            history=history,
            settings=settings,
        )

    try:
        reply = run_with_timeout(_ask_llm, 8.0)
    except Exception:
        reply = ""
    if reply:
        return {"ok": True, "reply": reply, "model": settings["model"], "error": ""}
    return {"ok": True, "reply": local_reply, "model": "rules", "error": ""}


def _llm_chat_reply(
    text: str,
    *,
    facts: dict[str, Any],
    has_project: bool,
    history: list[dict[str, str]] | None,
    settings: dict[str, str],
) -> str:
    import httpx

    system = chat_system_prompt(facts, has_project=has_project)
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for item in (history or [])[-16:]:
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": text})
    response = httpx.post(
        f"{settings['base_url']}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings["model"],
            "temperature": 0.2,
            "max_tokens": 450,
            "messages": messages,
        },
        timeout=httpx.Timeout(7.0, connect=2.0),
    )
    response.raise_for_status()
    payload = response.json()
    return sanitize_chat_reply(str(payload["choices"][0]["message"]["content"] or ""))


def _enrich_with_llm(
    *,
    project_data: dict[str, Any],
    replacement_map: dict[str, str],
    cad_result: dict[str, Any],
    pipeline_warnings: list[str],
    existing_findings: list[dict[str, Any]],
    tu_text: str,
    geometry_audit: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Опциональное LLM-дополнение. При ошибке/отсутствии ключа — пустой список."""
    settings = _llm_settings()
    api_key = settings["api_key"]
    if not api_key:
        return []
    base_url = settings["base_url"]
    model = settings["model"]

    payload_context = {
        "project_number": project_data.get("project_number"),
        "project_type": project_data.get("project_type"),
        "branch_pole_type": project_data.get("branch_pole_type"),
        "template_note": project_data.get("template_note"),
        "tu_data": project_data.get("tu_data"),
        "plan_data": project_data.get("plan_data"),
        "materials_data": project_data.get("materials_data"),
        "materials_10kv_data": project_data.get("materials_10kv_data"),
        "wire": {
            "mode": project_data.get("wire_selection_mode"),
            "auto": project_data.get("wire_auto_detected"),
            "final": project_data.get("wire_final_value"),
        },
        "unresolved_placeholders": cad_result.get("unresolved_placeholders"),
        "pipeline_warnings": pipeline_warnings[:20],
        "existing_findings": existing_findings[:20],
        "geometry_audit": {
            "line_length_04_m": (geometry_audit or {}).get("line_length_04_m"),
            "grounding_count": (geometry_audit or {}).get("grounding_count"),
            "groundings_on_route": (geometry_audit or {}).get("groundings_on_route"),
            "grounding_positions": (geometry_audit or {}).get("grounding_positions") or [],
            "grounding_gaps": (geometry_audit or {}).get("grounding_gaps") or [],
            "support_positions_04": (geometry_audit or {}).get("support_positions_04") or [],
            "support_gaps_04": (geometry_audit or {}).get("support_gaps_04") or [],
            "support_gaps_10": (geometry_audit or {}).get("support_gaps_10") or [],
            "number_sequence_issues": (geometry_audit or {}).get("number_sequence_issues") or [],
        },
        "tu_text_excerpt": (tu_text or "")[:4000],
        "replacement_sample": {
            key: replacement_map.get(key)
            for key in (
                "{{PROJNUMB}}",
                "{{FAZE}}",
                "{{SECH_KABEL}}",
                "{{SECH_KABEL_10kV}}",
                "{{P23}}",
                "{{A23}}",
                "{{YA23}}",
                "{{K21}}",
                "{{GROUND}}",
                "{{YOPK}}",
            )
            if key in replacement_map
        },
    }

    system = (
        "Ты — AI Engineer, второй опытный проектировщик ВЛ 0,4/10 кВ. "
        "Проект УЖЕ построен другой системой. Ты НЕ меняешь проект и НЕ пересчитываешь материалы. "
        "Ищи конкретные инженерные риски: опора/заземление вне трассы, мало заземлений "
        "(норма ~каждые 100 м на 0,4 кВ), несоответствие длины и количества элементов. "
        "Не пиши общие фразы вроде «проверьте РЛК» без факта. "
        "Не оценивай пролёт как длину линии, делённую на число опор. "
        "Расположение заземлений и опор бери из geometry_audit.grounding_positions "
        "и support_positions_04 (station_m — метры вдоль трассы). "
        "Не пиши, что расположение «не приведено», если в geometry_audit уже есть точки. "
        "Пролёты и шаг заземлений — только из support_gaps_* / grounding_gaps. "
        "Пролёт 0,4 кВ в этой проверке — не больше 42 м; не пиши норму 30 м. "
        "Порядок номеров опор — из number_sequence_issues: вдоль трассы должно быть №1, №2, №3 "
        "или с другого конца по убыванию. Не выдумывай скачки номеров, если списка нет. "
        "Для проекта 0,4 кВ длина трассы — plan_data.line_length_m; "
        "line_length_04kv_m бывает пустым и это нормально. "
        "Не упоминай имена JSON-полей. "
        "Ответь строго JSON-массивом объектов "
        '[{"severity":"recommendation|warning","category":"tu|plan|note|supports|cable|armature|grounding|sections|general",'
        '"title":"...","reason":"...","detail":"простое объяснение почему"}]. '
        "Максимум 5 пунктов. Не дублируй already existing_findings. "
        "Если новых идей нет — верни []."
    )
    import httpx

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": json.dumps(payload_context, ensure_ascii=False),
                    },
                ],
            },
            timeout=45.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_llm_findings(content)
    except Exception:
        return []


def _placement_notes(geometry_audit: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    grounds = [
        item
        for item in (geometry_audit.get("grounding_positions") or [])
        if isinstance(item, dict) and item.get("on_route")
    ]
    if not grounds:
        return notes
    ordered = sorted(grounds, key=lambda item: float(item.get("station_m") or 0))
    parts = []
    for item in ordered[:8]:
        label = str(item.get("label") or "заземление").strip() or "заземление"
        station = float(item.get("station_m") or 0)
        parts.append(f"{label} — {station:.0f} м от начала трассы")
    note = "Расположение заземлений: " + "; ".join(parts) + "."
    if len(ordered) >= 2:
        step = float(ordered[-1].get("station_m") or 0) - float(ordered[0].get("station_m") or 0)
        limit = float(geometry_audit.get("max_grounding_gap_m") or 100)
        note += f" Между крайними {step:.0f} м (норма шага ≤ {limit:g} м)."
    notes.append(note)
    return notes


def _drop_llm_geometry_guesses(
    findings: list[dict[str, Any]],
    geometry_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    """Убирает догадки LLM про пролёты и имена JSON-полей."""
    has_measured_gaps = bool(geometry_audit.get("support_gaps_04") or geometry_audit.get("support_gaps_10"))
    cleaned: list[dict[str, Any]] = []
    for item in findings:
        if item.get("source") != "llm":
            cleaned.append(item)
            continue
        blob = " ".join(
            str(item.get(key) or "") for key in ("title", "reason", "detail", "why")
        ).casefold()
        if "line_length_" in blob or "plan_data." in blob or "{{" in blob:
            continue
        if not has_measured_gaps and ("пролёт" in blob or "пролет" in blob):
            continue
        locations_known = bool(geometry_audit.get("grounding_positions")) or int(
            geometry_audit.get("groundings_on_route") or 0
        ) > 0
        if locations_known and not (geometry_audit.get("grounding_gaps") or []):
            if "зазем" in blob and (
                "расположен" in blob
                or "не привед" in blob
                or "не подтвержда" in blob
                or "шаг" in blob
            ):
                continue
        cleaned.append(item)
    return cleaned


def _parse_llm_findings(content: str) -> list[dict[str, Any]]:
    text = str(content or "").strip()
    if not text:
        return []
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        return []

    result: list[dict[str, Any]] = []
    for index, item in enumerate(data[:5]):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        reason = str(item.get("reason") or "").strip()
        detail = str(item.get("detail") or reason).strip()
        if not title or not reason:
            continue
        severity = str(item.get("severity") or "recommendation").strip().casefold()
        if severity not in {"recommendation", "warning"}:
            severity = "recommendation"
        category = str(item.get("category") or "general").strip().casefold()
        result.append(
            {
                "id": f"llm_{index}_{abs(hash(title)) % 100000}",
                "severity": severity,
                "category": category,
                "title": title,
                "reason": reason,
                "detail": detail,
                "action": "Почему?",
                "fix_action": "Как решить?",
                "why": detail,
                "how": str(item.get("how") or detail).strip(),
                "source": "llm",
            }
        )
    return result
