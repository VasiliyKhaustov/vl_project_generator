from __future__ import annotations

from typing import Any

from .tu_parser import abbreviate_garden_partnership_terms, build_branch_armature_line


TU_FIELDS = (
    "APPLICANT",
    "ADRESS",
    "PROJECTNUMBER",
    "KADNUMBER",
    "DATE",
    "POWER_KW",
    "VOLTAGE",
    "FAZE",
    "STROIDOM",
    "SECH_KABEL",
    "OTKUDASTROIT",
    "TP_NAME",
)

FALLBACK_VALUES = {
    "KADNUMBER": "не указан",
    "STROIDOM": "объекта",
}


def build_replacement_map(
    project_number: str,
    tu_data: dict[str, Any],
    materials_data: dict[str, Any],
) -> dict[str, str]:
    replacement_map: dict[str, str] = {
        "{{PROJNUMB}}": project_number,
    }

    for key in TU_FIELDS:
        _add_if_known(replacement_map, f"{{{{{key}}}}}", tu_data.get(key, ""))

    _add_if_known(replacement_map, "{{ADDRESS}}", tu_data.get("ADRESS", ""))
    _add_if_known(replacement_map, "{{TO_NAME}}", tu_data.get("TP_NAME", ""))
    _add_if_known(replacement_map, "{{OTUDASTROIT}}", tu_data.get("OTKUDASTROIT", ""))
    _add_if_known(replacement_map, "{{BRANCH_ARMATURE_LINE}}", build_branch_armature_line(tu_data))
    _add_if_known(replacement_map, "{{ROUTE_DISTANCE_KM}}", tu_data.get("route_distance_km", ""))

    for key, value in materials_data.items():
        _add_if_known(replacement_map, f"{{{{{key}}}}}", value)

    for address_key in ("{{ADRESS}}", "{{ADDRESS}}"):
        if address_key in replacement_map and replacement_map[address_key]:
            replacement_map[address_key] = abbreviate_garden_partnership_terms(
                replacement_map[address_key]
            )

    return replacement_map


def _add_if_known(replacement_map: dict[str, str], placeholder: str, value: Any) -> None:
    field_name = _placeholder_name(placeholder)
    formatted = _format_value(value, field_name)
    if formatted == "":
        fallback = FALLBACK_VALUES.get(field_name, "")
        if fallback:
            replacement_map[placeholder] = fallback
        return
    replacement_map[placeholder] = formatted


def _placeholder_name(placeholder: str) -> str:
    if placeholder.startswith("{{") and placeholder.endswith("}}"):
        return placeholder[2:-2]
    return ""


def _format_value(value: Any, field_name: str = "") -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if field_name == "SQUARE":
            return str(int(round(value)))
        if field_name == "SECH_KG":
            return _format_decimal(value, 1)
        if field_name == "SIP4_KG":
            return _format_decimal(value, 3)
        if field_name == "ZP6":
            return _format_decimal(value, 1)
        rounded = round(value, 3)
        if rounded.is_integer():
            return str(int(rounded))
        return f"{rounded:.3f}".rstrip("0").rstrip(".")
    return str(value)


def _format_decimal(value: float, digits: int) -> str:
    rounded = round(value, digits)
    if rounded.is_integer():
        return str(int(rounded))
    return f"{rounded:.{digits}f}".rstrip("0").rstrip(".")
