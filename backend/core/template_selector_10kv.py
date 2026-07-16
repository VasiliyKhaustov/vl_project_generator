from __future__ import annotations

from pathlib import Path
from typing import Any


TEMPLATES_10KV_DIR_NAME = "examples/templates/Готовые записки 10 кВ"


def _support_flags(supports: dict[str, Any]) -> dict[str, bool]:
    return {
        "p23": int(supports.get("P23") or 0) > 0,
        "a23": int(supports.get("A23") or 0) > 0,
        "ya23": int(supports.get("YA23") or 0) > 0,
        "k21": int(supports.get("K21") or 0) > 0,
    }


def _folder_name(flags: dict[str, bool]) -> str | None:
    names: list[str] = []
    if flags["p23"]:
        names.append("П23")
    if flags["a23"]:
        names.append("А23")
    if flags["ya23"]:
        names.append("УА23")
    if flags["k21"]:
        names.append("К21")
    if not names:
        return None
    return " и ".join(names)


def _file_prefix(flags: dict[str, bool]) -> str | None:
    names: list[str] = []
    if flags["p23"]:
        names.append("П23")
    if flags["a23"]:
        names.append("А23")
    if flags["ya23"]:
        names.append("УА23")
    if flags["k21"]:
        names.append("К21")
    if not names:
        return None
    if len(names) == 1:
        return f"Опора {names[0]}"
    return f"Опоры ({' и '.join(names)})"


def _10kv_suffix(supports_10kv: dict[str, Any]) -> str:
    p20 = int(supports_10kv.get("P20") or 0)
    a20 = int(supports_10kv.get("A20") or 0)
    up = int(supports_10kv.get("UP") or 0)
    ua = int(supports_10kv.get("UA") or 0)
    arlk = int(supports_10kv.get("ARLK") or 0)

    if a20 > 0:
        return "опоры П20 и А20 и А20 РЛК"
    if ua > 0 or up > 0:
        return "опоры П20 и УА20 и А20 РЛК"
    if p20 > 0 or arlk > 0:
        return "опорыП20 и А20 РЛК"
    return "опоры П20 и А20 и А20 РЛК"


def _candidate_filenames(prefix: str, suffix: str) -> list[str]:
    compact_suffix = suffix.replace("опоры ", "опоры", 1)
    return [
        f"{prefix} и {suffix}.dwg",
        f"{prefix} и {compact_suffix}.dwg",
    ]


def select_template_note_path_10kv(
    templates_root: Path,
    plan_data: dict[str, Any],
    logger: Any | None = None,
) -> tuple[Path, str | None]:
    templates_dir = templates_root / "Готовые записки 10 кВ"
    supports = plan_data.get("supports", {})
    supports_10kv = plan_data.get("supports_10kv", {})
    flags = _support_flags(supports)
    folder = _folder_name(flags)
    prefix = _file_prefix(flags)
    suffix = _10kv_suffix(supports_10kv)

    if not folder or not prefix:
        message = "Не удалось определить папку шаблона 10 кВ по опорам 0,4 кВ на плане."
        if logger:
            logger.error(message)
        raise FileNotFoundError(message)

    folder_path = templates_dir / folder
    candidates = _candidate_filenames(prefix, suffix)
    preferred_name = candidates[0]

    for template_name in candidates:
        template_path = folder_path / template_name
        if not template_path.exists():
            continue
        warning = None
        if template_name != preferred_name:
            warning = f"Шаблон {preferred_name} не найден. Использую {template_name}."
        if logger:
            logger.info(
                "Выбран шаблон записки 10 кВ: "
                f"{folder}/{template_name} "
                f"(P23: {flags['p23']}, A23: {flags['a23']}, "
                f"YA23*: {flags['ya23']}, K21: {flags['k21']}; "
                f"P20: {supports_10kv.get('P20', 0)}, A20: {supports_10kv.get('A20', 0)}, "
                f"UP: {supports_10kv.get('UP', 0)}, UA: {supports_10kv.get('UA', 0)}, "
                f"ARLK: {supports_10kv.get('ARLK', 0)})."
            )
            if warning:
                logger.warning(warning)
        return template_path, warning

    fallback_files = sorted(folder_path.glob("*.dwg")) if folder_path.exists() else []
    if fallback_files:
        warning = (
            f"Точный шаблон 10 кВ не найден в {folder}. "
            f"Использую {fallback_files[0].name}."
        )
        if logger:
            logger.warning(warning)
        return fallback_files[0], warning

    message = (
        f"Не найден подходящий шаблон 10 кВ в {folder_path}. "
        f"Ожидались файлы: {', '.join(candidates)}."
    )
    if logger:
        logger.error(message)
    raise FileNotFoundError(message)
