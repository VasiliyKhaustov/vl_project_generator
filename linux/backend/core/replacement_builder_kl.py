"""Подстановка полей КЛ поверх уже собранной карты. Карту 0,4 кВ и 10 кВ не собирает."""

from __future__ import annotations

from typing import Any

from backend.core.replacement_builder import _format_value


KL_FIELDS = (
    "SECH_KL",
    "SQUARE_KL",
    "POWER_KL",
    "DL_KL",
    "DL_OB",
    "DL_KL_KM",
    "RYT_TR",
    "ZAS_OG",
    "ZAS_P",
    "KM_KG",
    "MASSA",
    "TR",
    "PZK",
    "MFT",
    "YPKL",
    "OTK_STR_KL",
    "S",
    "P72",
    "E778",
)


def apply_kl_replacements(
    replacement_map: dict[str, str],
    materials_kl: dict[str, Any],
) -> dict[str, str]:
    updated = dict(replacement_map)
    for field_name in KL_FIELDS:
        value = materials_kl.get(field_name, "")
        if value == "" or value is None:
            continue
        updated[f"{{{{{field_name}}}}}"] = _format_value(value, field_name)
    return updated
