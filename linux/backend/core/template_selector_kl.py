"""Выбор готовой записки КЛ. Шаблоны 0,4 кВ и 10 кВ этот модуль не открывает."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from backend.core.cable_line import CABLE_ONLY_TEMPLATE_NAME, kl_support_counts


TEMPLATES_KL_DIR_NAME = "Готовые записки КЛ"


def select_template_note_path_kl(
    templates_dir: Path,
    tu_data: dict[str, Any],
    plan_data: dict[str, Any],
    *,
    requires_vl_04: bool,
    logger: Any | None = None,
) -> tuple[Path, str | None]:
    folder = templates_dir / TEMPLATES_KL_DIR_NAME
    if not folder.is_dir():
        raise FileNotFoundError(f"Не найдена папка шаблонов {folder}.")

    if not requires_vl_04:
        path = _find_named(folder, CABLE_ONLY_TEMPLATE_NAME)
        if path is None:
            raise FileNotFoundError(
                f"В {folder.name} нет файла «{CABLE_ONLY_TEMPLATE_NAME}»."
            )
        if logger:
            logger.info(f"КЛ без ВЛ 0,4 кВ: выбран шаблон {path.name}.")
        return path, None

    counts = kl_support_counts(plan_data)
    phrase = _support_phrase(counts)
    if phrase is None:
        present = ", ".join(key for key, value in counts.items() if value > 0) or "нет опор"
        raise FileNotFoundError(
            "Для КЛ вместе с ВЛ 0,4 кВ нет шаблона под набор опор "
            f"({present}). Нужна одна из комбинаций: "
            "П23; П23 и К21; П23 и А23 и К21; А23 и УА23; "
            "П23 и А23 и УА23; П23 и А23 и УА23 и К21."
        )

    has_pzk = bool(plan_data.get("plan_has_pzk"))
    has_switch = bool(tu_data.get("requires_komapparat_template"))
    match = _match_template(folder, phrase=phrase, has_pzk=has_pzk, has_switch=has_switch)
    if match is None:
        kind = "КЛ (ПЗК и СМ) и ВЛ" if has_pzk else "КЛ и ВЛ"
        if has_switch:
            kind += " коммутационный аппарат"
        raise FileNotFoundError(
            f"В папке {folder.name} нет записки «{kind}» для опор «{phrase}»."
        )
    if logger:
        logger.info(
            "Выбрана записка КЛ: "
            f"{match.name} (ВЛ 0,4 кВ: да, ПЗК: {has_pzk}, "
            f"коммутационный аппарат: {has_switch})."
        )
    return match, None


def _support_phrase(counts: dict[str, int]) -> str | None:
    p23 = counts["P23"] > 0
    a23 = counts["A23"] > 0
    ya23 = counts["YA23"] > 0
    k21 = counts["K21"] > 0
    if p23 and a23 and ya23 and k21:
        return "опоры п23 и а23 и уа23 и к21"
    if p23 and a23 and ya23 and not k21:
        return "опоры п23 и а23 и уа23"
    if p23 and a23 and k21 and not ya23:
        return "опора п23 и а23 и к21"
    if a23 and ya23 and not p23 and not k21:
        return "опоры а23 и уа23"
    if p23 and k21 and not a23 and not ya23:
        return "опоры п23 и к21"
    if p23 and not a23 and not ya23 and not k21:
        return "опора п23"
    return None


def _match_template(folder: Path, *, phrase: str, has_pzk: bool, has_switch: bool) -> Path | None:
    found: list[Path] = []
    for path in folder.glob("*.dwg"):
        if path.name.startswith("~$"):
            continue
        normalized = _normalize_filename(path.name)
        if has_pzk:
            if not normalized.startswith("кл (пзк и см)"):
                continue
        else:
            if not normalized.startswith("кл и вл"):
                continue
            if "пзк" in normalized or normalized.startswith("кл (см)"):
                continue
        if ("коммутацион" in normalized) != has_switch:
            continue
        if not normalized.endswith(phrase):
            continue
        found.append(path)
    if not found:
        return None
    return sorted(found, key=lambda item: (len(item.name), item.name))[0]


def _find_named(folder: Path, filename: str) -> Path | None:
    target = _normalize_filename(filename)
    for path in folder.glob("*.dwg"):
        if _normalize_filename(path.name) == target:
            return path
    return None


def _normalize_filename(name: str) -> str:
    text = unicodedata.normalize("NFC", name)
    text = text.casefold().replace("ё", "е")
    text = text.replace("аппрат", "аппарат")
    text = re.sub(r"\s+", " ", text).strip()
    if text.endswith(".dwg"):
        text = text[:-4].strip()
    return text
