from __future__ import annotations

import re
from typing import Any


def is_10kv_project(tu_text: str) -> bool:
    """
    Определение 10 кВ по тексту ТУ (для /detect и fallback без плана).

    Главный маркер из ТУ: «От опоры ВЛ 10 кВ … до РУ 10 кВ» (п. 10.1.1.1).
    Обычное упоминание «ВЛ 10 кВ» в источнике питания 0,4 кВ-проекта сюда не подходит.
    """
    normalized = tu_text.casefold().replace("ё", "е")

    # Явный старт строительства ВЛЗ 10 кВ от существующей опоры.
    if re.search(r"от\s+опоры\s+вл\s*10\s*кв", normalized):
        return True

    if re.search(r"10\.1\.1\.1", normalized):
        return True

    if re.search(r"влз[\s-]*10\s*кв", normalized):
        return True

    if re.search(
        r"10\.1\.2\.\s*строительство\s+новых\s+подстанций:\s*смонтировать",
        normalized,
    ):
        return True

    if re.search(
        r"строительство\s+новых\s+подстанций:\s*смонтировать\s+тп\s*10",
        normalized,
    ):
        return True

    if re.search(r"лэп\s*10\s*кв", normalized) and re.search(
        r"тп\s*10\s*/\s*0[,.]\s*4",
        normalized,
    ):
        return True

    return False


def has_10kv_plan_features(plan_data: dict[str, Any]) -> bool:
    """
    10 кВ по плану:
    - полилиния ВЛЗ 10 кВ на слое `10` (или Электрика_10);
    - и/или опоры П20/А20/УП20/УА20/А20 РЛК.
    Линия 0,4 кВ в том же проекте читается со слоя `04` — сама по себе 10 кВ не включает.
    """
    supports = plan_data.get("supports_10kv") or {}
    if any(int(supports.get(key, 0) or 0) > 0 for key in ("P20", "A20", "UP", "UA", "ARLK")):
        return True
    if float(plan_data.get("line_length_10kv_m", 0) or 0) > 1.0:
        return True
    return False


def resolve_project_is_10kv(tu_text: str, plan_data: dict[str, Any] | None = None) -> bool:
    """
    Итоговый тип проекта.
    Если план уже прочитан — решает он (слой 10 / опоры 10 кВ).
    Тогда спрашиваем «от какой опоры ответвляемся?» (УОП/УОК).
    ТУ с «От опоры ВЛ 10 кВ» используется, когда плана ещё нет.
    """
    if plan_data is not None:
        return has_10kv_plan_features(plan_data)
    return is_10kv_project(tu_text)
