from __future__ import annotations

from pathlib import Path
from typing import Any


TEMPLATES_DIR_NAME = "examples/templates"


def _support_flags(supports: dict[str, Any]) -> dict[str, bool]:
    return {
        "p23": int(supports.get("P23") or 0) > 0,
        "a23": int(supports.get("A23") or 0) > 0,
        "ya23": int(supports.get("YA23") or 0) > 0,
        "k21": int(supports.get("K21") or 0) > 0,
    }


def _template_suffix(flags: dict[str, bool]) -> str | None:
    has_p23 = flags["p23"]
    has_a23 = flags["a23"]
    has_ya23 = flags["ya23"]
    has_k21 = flags["k21"]

    if has_p23 and has_a23 and has_ya23 and has_k21:
        return "_A23_YA23"
    if has_p23 and has_a23 and has_ya23 and not has_k21:
        return "_A23_YA23_bezK21"
    if has_p23 and has_a23 and has_k21 and not has_ya23:
        return "_A23"
    if has_p23 and has_a23 and not has_ya23 and not has_k21:
        return "_P23_A23"
    if has_p23 and has_ya23 and not has_a23:
        return "_YA23"
    if has_a23 and has_ya23 and not has_p23:
        return "_A23_YA23_bezP"
    if has_a23 and not has_ya23 and not has_p23:
        return "_A23"
    if has_ya23 and not has_a23 and not has_p23:
        return "_YA23"
    if has_p23 and not has_a23 and not has_ya23 and not has_k21:
        return "_P23"

    return None


def _template_candidate_names(
    *,
    has_komapparat: bool,
    suffix: str | None,
) -> list[str]:
    prefix = "template_note_komapparat" if has_komapparat else "template_note"
    candidates: list[str] = []

    if suffix:
        candidates.append(f"{prefix}{suffix}.dwg")
        if suffix == "_A23_YA23_bezP":
            candidates.append(f"{prefix}_A23_YA23.dwg")
        if suffix == "_A23_YA23_bezK21":
            candidates.append(f"{prefix}_A23_YA23.dwg")

    if has_komapparat:
        candidates.append("template_note_komapparat.dwg")
    candidates.append("template_note.dwg")
    return candidates


def select_template_note_path(
    templates_dir: Path,
    tu_data: dict[str, Any],
    plan_data: dict[str, Any],
    logger: Any | None = None,
) -> tuple[Path, str | None]:
    supports = plan_data.get("supports", {})
    flags = _support_flags(supports)
    has_komapparat = bool(tu_data.get("requires_komapparat_template"))
    suffix = _template_suffix(flags)
    candidates = _template_candidate_names(has_komapparat=has_komapparat, suffix=suffix)
    preferred_name = candidates[0] if suffix else (
        "template_note_komapparat.dwg" if has_komapparat else "template_note.dwg"
    )

    for template_name in candidates:
        template_path = templates_dir / template_name
        if not template_path.exists():
            continue
        warning = None
        if template_name != preferred_name:
            warning = (
                f"Шаблон {preferred_name} не найден. Использую {template_name}."
            )
        if logger:
            logger.info(
                "Выбран шаблон записки: "
                f"{template_name} "
                f"(коммутационный аппарат: {has_komapparat}, "
                f"P23: {flags['p23']}, A23: {flags['a23']}, "
                f"YA23*: {flags['ya23']}, K21: {flags['k21']})."
            )
            if warning:
                logger.warning(warning)
        return template_path, warning

    message = (
        "Не найден подходящий шаблон записки в examples/templates. "
        f"Ожидались файлы: {', '.join(candidates)}."
    )
    if logger:
        logger.error(message)
    raise FileNotFoundError(message)


def template_placeholder_warning(
    template_path: Path,
    plan_data: dict[str, Any],
    template_placeholders: list[str],
) -> str | None:
    supports = plan_data.get("supports", {})
    expected: set[str] = set()
    if int(supports.get("P23") or 0) > 0:
        expected.update({"{{P23}}", "{{P23_1}}", "{{ES15}}"})
    if int(supports.get("A23") or 0) > 0:
        expected.update({"{{A23}}", "{{A231}}", "{{Y4}}"})
    if int(supports.get("YA23") or 0) > 0:
        expected.update({"{{YA23}}", "{{YA231}}", "{{X89}}"})
    if int(supports.get("K21") or 0) > 0:
        expected.update({"{{K21}}", "{{K21_1}}"})

    missing = sorted(expected - set(template_placeholders))
    if not missing:
        return None
    return (
        f"Шаблон {template_path.name} не содержит placeholders: {', '.join(missing)}. "
        "Проверьте эталонный DWG."
    )
