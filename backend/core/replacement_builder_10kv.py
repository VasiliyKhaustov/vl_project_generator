from __future__ import annotations

import re
from typing import Any

from .placeholders_10kv import IGNORED_UNRESOLVED_10KV
from .replacement_builder import _add_if_known, build_replacement_map

_10KV_ONLY_EMPTY_FIELDS = frozenset(
    {
        "{{OTKUDASTROIT}}",
        "{{OTUDASTROIT}}",
        "{{TP_NAME}}",
        "{{TO_NAME}}",
    }
)


def build_replacement_map_10kv(
    project_number: str,
    tu_data: dict[str, Any],
    materials_data: dict[str, Any],
    materials_10kv: dict[str, Any],
) -> dict[str, str]:
    replacement_map = build_replacement_map(project_number, tu_data, materials_data)

    applicant = replacement_map.get("{{APPLICANT}}", "")
    if applicant:
        replacement_map["{{APPLICANT}}"] = re.sub(
            r"\bкрестьянское\s+фермерское\s+хозяйство\b",
            "КФХ",
            applicant,
            flags=re.IGNORECASE,
        )
    for address_key in ("{{ADRESS}}", "{{ADDRESS}}"):
        address = replacement_map.get(address_key, "")
        if address:
            replacement_map[address_key] = re.sub(
                r"\b([А-ЯЁа-яё-]+)\s+муниципальный\s+район\b",
                r"\1 район",
                address,
                flags=re.IGNORECASE,
            )

    for key, value in materials_10kv.items():
        _add_if_known(replacement_map, f"{{{{{key}}}}}", value)

    otkuda_10 = (
        materials_10kv.get("OTKUDASTROIT_10kV", "")
        or materials_10kv.get("OTKUDA_STROIT_10kV", "")
        or tu_data.get("OTKUDASTROIT_10kV", "")
        or tu_data.get("OTKUDA_STROIT_10kV", "")
    )
    if otkuda_10:
        _add_if_known(replacement_map, "{{OTKUDASTROIT_10kV}}", otkuda_10)
        _add_if_known(replacement_map, "{{OTKUDA_STROIT_10kV}}", otkuda_10)

    ps_name = materials_10kv.get("PS_NAME", "") or tu_data.get("PS_NAME", "")
    if ps_name:
        _add_if_known(replacement_map, "{{PS_NAME}}", ps_name)

    if materials_10kv.get("A20") is not None:
        _add_if_known(replacement_map, "{{А20}}", materials_10kv["A20"])

    line_length_km = materials_data.get("LINE_LENGTH_KM")
    if line_length_km not in ("", None):
        _add_if_known(replacement_map, "{{LINELENGTH_KM}}", line_length_km)

    for placeholder in _10KV_ONLY_EMPTY_FIELDS:
        if placeholder in replacement_map and not str(replacement_map[placeholder]).strip():
            replacement_map.pop(placeholder, None)

    if otkuda_10:
        _add_if_known(replacement_map, "{{OTKUDASTROIT}}", otkuda_10)

    _add_if_known(replacement_map, "{{PROJECTNUMBER}}", project_number)

    return replacement_map


def filter_cad_result_10kv(cad_result: dict[str, Any]) -> dict[str, Any]:
    unresolved = cad_result.get("unresolved_placeholders", []) or []
    filtered = [item for item in unresolved if item not in IGNORED_UNRESOLVED_10KV]
    result = dict(cad_result)
    result["unresolved_placeholders"] = filtered
    result["ignored_placeholders"] = sorted(set(unresolved) - set(filtered))
    return result
