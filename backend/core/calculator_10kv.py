from __future__ import annotations

import math
from typing import Any


_TRANSFORMER_PROTECTION_TABLE: dict[int, dict[str, Any]] = {
    25: {"nom": "36", "qf": ("25", "25", "-", "-"), "10kv": ("101", "5"), "6kv": ("101", "8")},
    40: {"nom": "58", "qf": ("25", "40", "-", "-"), "10kv": ("101", "8"), "6kv": ("101", "10")},
    63: {"nom": "91", "qf": ("40", "63", "-", "-"), "10kv": ("101", "10"), "6kv": ("101", "16")},
    100: {"nom": "144", "qf": ("100", "80", "40", "-"), "10kv": ("101", "16"), "6kv": ("101", "20")},
    160: {"nom": "232", "qf": ("100", "100", "100", "-"), "10kv": ("101", "20"), "6kv": ("102", "31.5")},
    250: {"nom": "360", "qf": ("100", "100", "100", "100"), "10kv": ("102", "40"), "6kv": ("102", "50")},
    400: {"nom": "578", "qf": ("100", "160", "250", "250"), "10kv": ("103", "50"), "6kv": ("103", "80")},
    630: {"nom": "909.3", "qf": ("", "", "", ""), "10kv": ("103", "80"), "6kv": ("103", "100")},
}


def yopk_value(branch_pole_type: str) -> str:
    normalized = (branch_pole_type or "").strip().casefold()
    if normalized in {"anchor", "ankernaya", "анкерная", "уок"}:
        return "УОК"
    return "УОП"


def calculate_materials_10kv(
    tu_data: dict[str, Any],
    plan_data: dict[str, Any],
    *,
    branch_pole_type: str = "intermediate",
) -> dict[str, Any]:
    supports = plan_data.get("supports_10kv", {})
    p20 = int(supports.get("P20", 0) or 0)
    a20 = int(supports.get("A20", 0) or 0)
    up = int(supports.get("UP", 0) or 0)
    ua = int(supports.get("UA", 0) or 0)
    arlk = int(supports.get("ARLK", 0) or 0)
    # А20-3Н с РЛК получает всю базовую арматуру А20-3Н и дополнительно
    # специальные позиции разъединителя.
    a20_base = a20 + arlk

    line_length_m = float(plan_data.get("line_length_10kv_m", 0) or 0)
    line_length_04_m = float(plan_data.get("line_length_04kv_m", 0) or 0)
    km_10_route = float(plan_data.get("line_length_10kv_km", line_length_m / 1000) or 0)
    km_04_route = float(plan_data.get("line_length_04kv_km", line_length_04_m / 1000) or 0)
    has_transformer_substation = bool(str(tu_data.get("6-10", "") or "").strip())
    ktp_entry_km = 0.005 if has_transformer_substation else 0.0
    km_10_total = km_10_route + ktp_entry_km
    km_04_total = km_04_route + ktp_entry_km
    power_10 = _format_km_display(km_10_total)
    km_04 = _format_km_display(km_04_total)
    km_04_display = float(km_04.replace(",", ".")) if km_04 else 0.0
    km_04_with_reserve = km_04_display * 1.045
    power_lengt_m = _format_m_display(km_04_total * 1000)
    power_kw = str(tu_data.get("POWER_KW", "") or "")
    cable_04 = str(tu_data.get("SECH_KABEL", "") or "")
    cable_04_weight = 1112 if "70" in cable_04 else 775

    ps = p20 * 0.051
    a_s = a20_base * 0.102
    u_s = ua * 0.153
    su = ps + a_s + u_s

    sv10 = p20 + a20 * 2 + ua * 3 + arlk * 2
    sv101 = sv10 * 0.45

    km_10_display = float(power_10.replace(",", ".")) if power_10 else 0.0
    km10 = km_10_display * 3 * 1.045
    kmv = km10 * 334

    # А20-3Н с РЛК входит в базовую А20 для ШФ (как и для прочей арматуры).
    shf = 3 * p20 + 3 * up + 3 * ua + a20_base + 3
    # {{PN}} — единственное место, где А20-3Н с РЛК не считается как А20-3Н:
    # только 3*ARLK, без добавления в 6*A20.
    pn = 6 * a20 + 3 * arlk + 6 * ua

    sr = arlk
    total_10kv = p20 + a20 + up + ua + arlk
    bez = max(total_10kv - arlk, 0)

    pole_185 = 2 * bez + sr
    pole_125 = sr

    st12 = 21 * sr + 10 * bez
    st18 = 5 * sr + 5 * (bez * 2)

    mosh = str(tu_data.get("MOSH", "") or "")
    sech_10 = str(tu_data.get("SECH_KABEL_10kV", "") or "")
    voltage_ratio = str(tu_data.get("6-10", "") or "")
    protection = _transformer_protection_values(mosh, voltage_ratio)

    pole_1210 = pole_185
    val_681 = ua

    return {
        "6-10": str(tu_data.get("6-10", "") or ""),
        "PS_NAME": str(tu_data.get("PS_NAME", "") or ""),
        "POWER_KW": power_kw,
        "OTKUDA_STROIT_10kV": str(
            tu_data.get("OTKUDA_STROIT_10kV", "")
            or tu_data.get("OTKUDASTROIT_10kV", "")
            or ""
        ),
        "OTKUDASTROIT_10kV": str(
            tu_data.get("OTKUDASTROIT_10kV", "")
            or tu_data.get("OTKUDA_STROIT_10kV", "")
            or ""
        ),
        "MOSH": mosh,
        "SECH_KABEL_10kV": sech_10,
        "KM_10_ROUTE": _format_km_display(km_10_route),
        "KTP_ENTRY_10_KM": _format_km_display(ktp_entry_km),
        "POWER_10": power_10,
        "KM_04_ROUTE": _format_km_display(km_04_route),
        "KTP_ENTRY_KM": _format_km_display(ktp_entry_km),
        "KM_04": km_04,
        "KM_04_RESERVE": _format_decimal(km_04_with_reserve, 3),
        "KG_04": _format_decimal(km_04_with_reserve * cable_04_weight, 1),
        "POWER_LENGT_M": power_lengt_m,
        "SQUARE_10kV": int(round(line_length_m * 11)) if line_length_m > 0 else "",
        "P20": p20,
        "P": p20,
        "A20": a20,
        "A": a20,
        "А20": a20,
        "UP": up,
        "UA": ua,
        "ARLK": arlk,
        "RAZ": arlk,
        "PS": _format_decimal(ps, 3),
        "AS": _format_decimal(a_s, 3),
        "US": _format_decimal(u_s, 3),
        "SU": _format_decimal(su, 3),
        "PRED": protection["pred"],
        "NOM": protection["nom"],
        "PLAV": protection["plav"],
        "QF1": protection["qf"][0],
        "QF2": protection["qf"][1],
        "QF3": protection["qf"][2],
        "QF4": protection["qf"][3],
        "IZCH": "ШФ20УО",
        "KOL": "3",
        "KM_10": power_10,
        "SHF": shf,
        "PI": 2 * pn,
        "185": pole_185,
        "125": pole_125,
        "1210": pole_1210,
        "K128": pole_185,
        "128": pole_185,
        "YOPK": yopk_value(branch_pole_type),
        "IZM": total_10kv,
        "P201": _format_decimal(p20 * 0.45, 2),
        "ARL1": _format_decimal(arlk * 0.9, 2),
        "SV10": sv10,
        "SV101": _format_decimal(sv101, 2),
        "KM10": _format_decimal(km10, 3),
        "KMV": _format_decimal(kmv, 1),
        "OSH_KM": "0,006",
        "OSH_KG": 2.0,
        "TM73": 1,
        "TM73_KG": 9.85,
        "TM74": 1,
        "TM74_KG": 13.0,
        "BRANCH_04_KM": "0.004",
        "BRANCH_04_KG": 3.239,
        "63": p20,
        "631": _format_decimal(p20 * 22.3, 1),
        "65": a20_base,
        "651": _format_decimal(a20_base * 18.8, 1),
        "66": a20_base,
        "661": _format_decimal(a20_base * 6.7, 1),
        "67": ua,
        "671": _format_decimal(ua * 3.9, 1),
        "68": ua,
        "681": _format_decimal(val_681 * 33, 1),
        "X51": p20 + up + 2,
        "511": _format_decimal((p20 + up + 2) * 1.9, 1),
        "Y52": a20_base + ua * 2,
        "521": _format_decimal((a20_base + ua * 2) * 7.1, 1),
        "ZP1": _format_decimal(0.7 * up + a20_base + 1.5 * ua + 4, 1),
        "ZP": _format_decimal((0.7 * up + a20_base + 1.5 * ua + 4) * 0.9, 1),
        "K9": shf,
        "M20": up + 3 * a20_base + 4 * ua + 1,
        "BLT": 2 * a20_base + 2 * ua,
        "SV": 6 * p20 + 6 * up + 2 * a20_base + 6 * ua + 6,
        "CD": p20 + 3 * a20_base + 3 * ua + 2,
        "PN": pn,
        "SERG": pn,
        "SKOB": pn,
        "USHK": pn,
        "ZVEN": pn,
        "NB": pn,
        "SR": sr,
        "BEZ": bez,
        "ST12": st12,
        "ST18": st18,
        "ST1": _format_decimal(st12 * 0.888, 1),
        "ST8": _format_decimal(st18 * 2, 1),
    }


def _transformer_protection_values(mosh: str, voltage_ratio: str) -> dict[str, Any]:
    try:
        power_kva = int(float(str(mosh).replace(",", ".")))
    except ValueError:
        power_kva = 0
    row = _TRANSFORMER_PROTECTION_TABLE.get(power_kva)
    if row is None:
        return {
            "pred": "",
            "nom": _nominal_current(mosh),
            "plav": "",
            "qf": ("", "", "", ""),
        }

    voltage_key = "6kv" if str(voltage_ratio).strip().startswith("6") else "10kv"
    fuse_type, fuse_current = row[voltage_key]
    return {
        "pred": f"{fuse_type}-{fuse_current}",
        "nom": row["nom"],
        "plav": fuse_current,
        "qf": row["qf"],
    }


def _nominal_current(mosh: str) -> str:
    try:
        power_kva = float(str(mosh).replace(",", "."))
    except ValueError:
        return ""
    if power_kva <= 0:
        return ""
    current = power_kva * 1000 / (math.sqrt(3) * 400)
    return str(int(round(current)))


def _format_decimal(value: float, digits: int) -> str | int | float:
    rounded = round(value, digits)
    if rounded.is_integer():
        return int(rounded)
    return float(f"{rounded:.{digits}f}".rstrip("0").rstrip("."))


def _format_m_display(value: float) -> str:
    if value <= 0:
        return ""
    rounded = round(value, 3)
    if rounded.is_integer():
        return str(int(rounded))
    text = f"{rounded:.3f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _format_km_display(value: float) -> str:
    if value <= 0:
        return ""
    rounded = round(value, 3)
    text = f"{rounded:.3f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")
