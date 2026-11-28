"""Расчёт полей кабельной линии. Формулы записок 0,4 кВ и 10 кВ не меняет."""

from __future__ import annotations

import math
from typing import Any

from backend.core.cable_line import cable_weight_kg_per_km, kl_support_counts
from backend.core.calculator import round_line_length_m


def calculate_materials_kl(
    tu_data: dict[str, Any],
    plan_data: dict[str, Any],
    *,
    requires_vl_04: bool,
) -> dict[str, Any]:
    raw_length = float(plan_data.get("line_length_kl_m", 0) or 0)
    length_m = round_line_length_m(raw_length) if raw_length else 0
    length_with_reserve_m = length_m + 20 if length_m else 0
    length_km = length_with_reserve_m / 1000 if length_with_reserve_m else 0
    section = str(tu_data.get("SECH_KL", "") or "")
    weight_per_km = cable_weight_kg_per_km(section)
    km_kg = length_km * 1.045 if length_km else 0
    pzk = int(math.floor(length_m / 0.48 + 0.5)) if length_m else 0
    pipe_m = 3
    mft = int(math.floor((pipe_m + pzk) / 6 + 0.5)) if length_m else 0

    counts = kl_support_counts(plan_data)
    # В карте КЛ общее число опор считается без А23.
    total_without_a23 = counts["P23"] + counts["K21"] + counts["YA23"]

    return {
        "SECH_KL": section,
        "SQUARE_KL": length_m,
        "POWER_KL": tu_data.get("POWER_KW", ""),
        "DL_KL": length_m,
        "DL_OB": length_with_reserve_m,
        "DL_KL_KM": length_km,
        "RYT_TR": length_m * 0.18,
        "ZAS_OG": length_m * 0.12,
        "ZAS_P": length_m * 0.06,
        "KM_KG": km_kg,
        "MASSA": km_kg * weight_per_km if weight_per_km is not None else "",
        "TR": pipe_m,
        "PZK": pzk,
        "MFT": mft,
        "YPKL": mft * 2,
        "OTK_STR_KL": tu_data.get("OTK_STR_KL", "") if requires_vl_04 else "",
        "S": total_without_a23,
        "P72": total_without_a23,
        "E778": total_without_a23 * 2,
    }
