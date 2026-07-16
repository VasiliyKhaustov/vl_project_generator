from __future__ import annotations

import re
from typing import Any

from .tu_parser import _normalize, _numbered_item, _search, read_tu_text


def enrich_tu_data_10kv(tu_path: Any, tu_data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    text = read_tu_text(tu_path)
    warnings: list[str] = []
    extra: dict[str, Any] = {}

    voltage_ratio = _extract_voltage_ratio(text)
    if voltage_ratio:
        extra["6-10"] = voltage_ratio
    else:
        warnings.append("Поле {{6-10}} не удалось извлечь из ТУ.")

    ps_name = _extract_ps_name(text)
    if ps_name:
        extra["PS_NAME"] = ps_name
    else:
        warnings.append("Поле {{PS_NAME}} не удалось извлечь из ТУ.")

    otkuda = _extract_otkudastroit_10kv(text)
    if otkuda:
        # В эталоне встречается оба написания placeholder.
        extra["OTKUDA_STROIT_10kV"] = otkuda
        extra["OTKUDASTROIT_10kV"] = otkuda
    else:
        warnings.append("Поле {{OTKUDASTROIT_10kV}} не удалось извлечь из ТУ.")

    sech = _extract_sech_kabel_10kv(text)
    if sech:
        extra["SECH_KABEL_10kV"] = sech
    else:
        warnings.append("Поле {{SECH_KABEL_10kV}} не удалось извлечь из ТУ.")

    mosh = _extract_mosh(text)
    if mosh:
        extra["MOSH"] = mosh
    else:
        warnings.append("Поле {{MOSH}} не удалось извлечь из ТУ.")

    merged = {**tu_data, **extra}
    return merged, warnings


def _extract_voltage_ratio(text: str) -> str:
    for item_number, next_number in (("10.1.2", "10.1.3"), ("10.1.1.1", "10.1.1.2")):
        item = _numbered_item(text, item_number, next_number)
        value = _search_voltage_ratio(item)
        if value:
            return value

    return _search_voltage_ratio(text)


def _search_voltage_ratio(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"(\d+)\s*/\s*0[,.]\s*4\s*кв", text, flags=re.IGNORECASE)
    if not match:
        return ""
    high = match.group(1)
    return f"{high}/0,4"


def _extract_ps_name(text: str) -> str:
    item = _numbered_item(text, "10.1.1.1", "10.1.1.2")
    source = item or text
    match = re.search(
        r"от\s+опоры\s+вл\s*10\s*кв\s+([А-ЯЁ][а-яё-]+)",
        source,
        flags=re.IGNORECASE,
    )
    if match:
        return f"ПС {_normalize(match.group(1))}"

    patterns = (
        r"базовая\s+подстанция[^:]*:\s*ПС\s+(?:\d+/\d+\s*кВ\s+)?([А-ЯЁ][а-яё-]+)",
        r"ПС\s+\d+/\d+\s*кВ\s+([А-ЯЁ][а-яё-]+)",
        r"ПС\s+([А-ЯЁ][а-яё-]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return f"ПС {_normalize(match.group(1))}"
    return ""


def _extract_otkudastroit_10kv(text: str) -> str:
    """
    Из «От опоры ВЛ 10 кВ Романово по п. 10.2.2. до РУ 10 кВ...»
    оставляем нейтральную фразу без имени фидера и пункта ТУ.
    """
    item = _numbered_item(text, "10.1.1.1", "10.1.1.2")
    source = item or text
    if re.search(
        r"от\s+опоры\s+вл\s*10\s*кв.+?до\s+ру\s*10\s*кв",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        return "от опоры ВЛ 10 кВ до РУ 10 кВ"
    if re.search(r"от\s+опоры\s+вл\s*10\s*кв", source, flags=re.IGNORECASE):
        return "от опоры ВЛ 10 кВ до РУ 10 кВ"
    return ""


def _extract_sech_kabel_10kv(text: str) -> str:
    item = _numbered_item(text, "10.1.1.1", "10.1.1.2")
    source = (item or text).casefold().replace("х", "x")
    if re.search(r"от\s*50[^.\n;]{0,40}до\s*(70|100)", source):
        return "1х70"
    if re.search(r"до\s*50\s*мм", source):
        return "1х50"
    return ""


def _extract_mosh(text: str) -> str:
    item = _numbered_item(text, "10.1.2", "10.1.3")
    source = item or text
    match = re.search(r"мощност\w*\s+(\d+)\s*кв[аa]", source, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"(\d+)\s*кв[аa]", source, flags=re.IGNORECASE)
    return match.group(1) if match else ""
