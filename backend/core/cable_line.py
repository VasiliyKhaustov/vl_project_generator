"""Определение проекта кабельной линии и поля, которых нет в записках 0,4 кВ и 10 кВ."""

from __future__ import annotations

import re
from typing import Any


# Ток и диаметр пока никуда не подставляются. Таблица остаётся на будущее.
CABLE_SECTION_REFERENCE = {
    "4х50": {"weight_kg_per_km": 1408, "current_a": 132, "diameter_mm": 32.4},
    "4х70": {"weight_kg_per_km": 1776, "current_a": 165, "diameter_mm": 35.5},
    "4х95": {"weight_kg_per_km": 2284, "current_a": 199, "diameter_mm": 39.2},
    "4х120": {"weight_kg_per_km": 2645, "current_a": 226, "diameter_mm": 41.9},
    "4х150": {"weight_kg_per_km": 3146, "current_a": 254, "diameter_mm": 48.6},
    "4х185": {"weight_kg_per_km": 3787, "current_a": 290, "diameter_mm": 53.2},
}

CABLE_ONLY_TEMPLATE_NAME = "Кабельная линия пример с ПЗК и соединительными муфтами.dwg"


def fold_text(value: str) -> str:
    return (value or "").casefold().replace("ё", "е")


# Пункт есть почти в каждом ТУ и не означает, что в этом проекте строится КЛ.
_BOILERPLATE_CABLE = re.compile(
    r"строительств\w+\s+воздушн\w+\s+и\s+\(\s*или\s*\)\s+кабельн\w+\s+лини\w*"
    r"|замен\w+\s+воздушн\w+\s+лини\w+\s+кабельн\w*"
)


def is_cable_line_project(tu_text: str) -> bool:
    """КЛ — только если в ТУ прямо задана кабельная линия.

    Фраза «сечением кабеля» у ВЛИ 0,4 кВ сюда не попадает.
    Типовой пункт «воздушной и (или) кабельной линии» тоже не попадает:
    он есть и в обычных ТУ на ВЛ.
    """
    text = _BOILERPLATE_CABLE.sub(" ", fold_text(tu_text))
    if re.search(r"кабельн\w*\s+лини", text):
        return True
    if re.search(r"смонтировать\s+кл\b", text):
        return True
    if re.search(r"\bкл\s*0\s*[,.]?\s*4", text):
        return True
    if re.search(r"проклад\w*\s+кабел", text):
        return True
    if re.search(r"кабел\w*\s+в\s+транше", text):
        return True
    return False


def tu_requires_vl_04(tu_text: str) -> bool:
    """В ТУ прямо сказано строить ВЛ 0,4 кВ вместе с кабельной линией."""
    text = fold_text(tu_text)
    vl = r"(?:воздушн\w+\s+лини|(?:вли|вл)\s*0\s*[,.]?\s*4)"
    build = r"(?:построить|смонтировать|строительств\w+)"
    if re.search(rf"{build}.{{0,80}}{vl}", text):
        return True
    if re.search(rf"{vl}.{{0,80}}{build}", text):
        return True
    if re.search(rf"кабельн\w*\s+лини\w*.{{0,80}}(?:и|,)\s*{vl}", text):
        return True
    if re.search(rf"{vl}.{{0,80}}(?:и|,)\s*кабельн\w*\s+лини", text):
        return True
    return False


def sech_kl_from_tu(tu_text: str) -> str:
    """Сечение КЛ из ТУ.

    «до 50 мм²» — 4х50. «от 50 до 70» и «от 50 до 100» — 4х70.
    Окно широкое: типовая фраза про траншею и изоляцию длиннее 120 символов,
    а «сечением кабеля» стоит после слова «сечение», не перед ним.
    """
    text = fold_text(tu_text)
    windows: list[str] = []
    for match in re.finditer(
        r"кабельн\w*\s+лини|кабел\w*\s+сечен|сечен\w*\s+кабел|\bкл\b",
        text,
    ):
        windows.append(text[max(0, match.start() - 160) : match.end() + 500])
    corpus = " ".join(windows) or text
    for size in (185, 150, 120, 95, 70, 50):
        if re.search(rf"4\s*[xх×*]\s*{size}(?!\d)", corpus):
            return f"4х{size}"
    if re.search(r"от\s*50\s*до\s*(?:70|100)(?!\d)", corpus):
        return "4х70"
    if re.search(r"до\s*50(?!\d)", corpus):
        return "4х50"
    return ""


def is_vl04_plan_noise(warning: str) -> bool:
    """Предупреждения чтения ВЛ 0,4 кВ. На чистой КЛ их показывать не нужно."""
    folded = fold_text(warning)
    marks = (
        "электрика_04",
        "полилиния 0,4",
        "полилиний 0,4",
        "esmt",
        "пл_заземление",
        "заземлен",
    )
    return any(mark in folded for mark in marks)


def cable_weight_kg_per_km(section: str) -> int | None:
    item = CABLE_SECTION_REFERENCE.get(section or "")
    if not item:
        return None
    return int(item["weight_kg_per_km"])


def extract_otk_str_kl(tu_text: str) -> str:
    """Откуда строить КЛ, если в ТУ она идёт вместе с воздушной линией."""
    paragraphs = [part.strip() for part in re.split(r"[\r\n]+", tu_text or "") if part.strip()]
    origin = re.compile(
        r"(от\s+.+?\s+до\s+опор\w*(?:\s*№\s*[\w\-]+)?)",
        re.IGNORECASE,
    )
    for paragraph in paragraphs:
        folded = fold_text(paragraph)
        if "кабел" not in folded and not re.search(r"\bкл\b", folded):
            continue
        match = origin.search(paragraph)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" .;")
    match = origin.search(tu_text or "")
    if match and is_cable_line_project(tu_text):
        return re.sub(r"\s+", " ", match.group(1)).strip(" .;")
    return ""


def kl_support_counts(plan_data: dict[str, Any]) -> dict[str, int]:
    supports = plan_data.get("supports") or {}
    return {
        "P23": int(supports.get("P23") or 0) + int(supports.get("PP23") or 0),
        "A23": int(supports.get("A23") or 0),
        "YA23": int(supports.get("YA23") or 0),
        "K21": int(supports.get("K21") or 0),
    }
