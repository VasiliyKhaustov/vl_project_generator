from __future__ import annotations

from pathlib import Path
from typing import Any


TEMPLATES_10KV_DIR_NAME = "examples/templates/Готовые записки 10 кВ"


def _support_flags(supports: dict[str, Any]) -> dict[str, bool]:
    return {
        "p23": int(supports.get("P23") or 0) > 0 or int(supports.get("PP23") or 0) > 0,
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


def _file_prefixes(flags: dict[str, bool]) -> list[str]:
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
        return []
    if len(names) == 1:
        # В каталоге встречаются и «Опора X», и «Опоры X».
        return [f"Опора {names[0]}", f"Опоры {names[0]}"]
    joined = " и ".join(names)
    return [f"Опоры ({joined})"]


def _10kv_suffix(supports_10kv: dict[str, Any]) -> str:
    """Суффикс файла по опорам 10 кВ на плане."""
    p20 = int(supports_10kv.get("P20") or 0)
    a20 = int(supports_10kv.get("A20") or 0)
    up = int(supports_10kv.get("UP") or 0)
    ua = int(supports_10kv.get("UA") or 0)
    arlk = int(supports_10kv.get("ARLK") or 0)

    has_p20 = p20 > 0
    has_a20 = a20 > 0
    has_ua_family = ua > 0 or up > 0

    # Новые шаблоны без промежуточных П20.
    if has_a20 and not has_p20 and not has_ua_family:
        return "опоры А20-3Н и А20-3Н с РЛК"
    if has_ua_family and not has_p20 and not has_a20:
        return "опоры УА20-3Н и А20 РЛК"

    # Классические шаблоны с П20.
    if has_a20:
        return "опоры П20 и А20 и А20 РЛК"
    if has_ua_family:
        return "опоры П20 и УА20 и А20 РЛК"
    if has_p20 or arlk > 0:
        return "опорыП20 и А20 РЛК"
    return "опоры П20 и А20 и А20 РЛК"


def _suffix_variants(suffix: str) -> list[str]:
    variants = [suffix]
    compact = suffix.replace("опоры ", "опоры", 1)
    if compact != suffix:
        variants.append(compact)
    return variants


def _candidate_filenames(prefixes: list[str], suffix: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for prefix in prefixes:
        for suffix_variant in _suffix_variants(suffix):
            name = f"{prefix} и {suffix_variant}.dwg"
            if name in seen:
                continue
            seen.add(name)
            names.append(name)
    return names


def _find_by_suffix(folder_path: Path, suffix: str) -> list[Path]:
    """Запасной поиск по суффиксу 10 кВ, если префикс в имени файла слегка отличается."""
    if not folder_path.exists():
        return []
    endings = tuple(f" и {variant}.dwg" for variant in _suffix_variants(suffix))
    matches = [
        path
        for path in sorted(folder_path.glob("*.dwg"))
        if path.name.endswith(endings)
    ]
    return matches


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
    prefixes = _file_prefixes(flags)
    suffix = _10kv_suffix(supports_10kv)

    if not folder or not prefixes:
        message = "Не удалось определить папку шаблона 10 кВ по опорам 0,4 кВ на плане."
        if logger:
            logger.error(message)
        raise FileNotFoundError(message)

    folder_path = templates_dir / folder
    candidates = _candidate_filenames(prefixes, suffix)
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

    suffix_matches = _find_by_suffix(folder_path, suffix)
    if suffix_matches:
        template_path = suffix_matches[0]
        warning = (
            f"Точное имя шаблона 10 кВ не найдено. "
            f"Использую файл по суффиксу опор 10 кВ: {template_path.name}."
        )
        if logger:
            logger.warning(warning)
            logger.info(
                "Выбран шаблон записки 10 кВ: "
                f"{folder}/{template_path.name} "
                f"(P23: {flags['p23']}, A23: {flags['a23']}, "
                f"YA23*: {flags['ya23']}, K21: {flags['k21']}; "
                f"P20: {supports_10kv.get('P20', 0)}, A20: {supports_10kv.get('A20', 0)}, "
                f"UP: {supports_10kv.get('UP', 0)}, UA: {supports_10kv.get('UA', 0)}, "
                f"ARLK: {supports_10kv.get('ARLK', 0)})."
            )
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
