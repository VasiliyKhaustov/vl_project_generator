from __future__ import annotations

import re
from typing import Any

from .cable_format import calculate_sip4_kg, format_cable_section_display


WIND_LOCALITIES = {
    "I": (
        "Елец",
        "Сахаровка",
        "Трубицино",
        "Казинка",
        "Воронец",
        "Паниковец",
    ),
    "II": (
        "Данков",
        "Красное",
        "Донское",
        "Каменная Лубна",
        "Галичья гора",
        "Бутырки",
        "Липецк",
        "Фащевка",
        "Двуречки",
        "Первомайский",
        "Куликово",
        "Боровое",
        "Пады",
        "Малей",
        "Чаплыгин",
        "Юсово",
        "Демкино",
    ),
    "III": (
        "Сырский",
        "Подгорное",
        "Боринское",
        "Стебаево",
        "Круглое",
        "Замартынье",
        "Кузьминка",
        "Кузьминские Отвержки",
        "Ленино",
    ),
    "IV": (
        "Лев Толстой",
        "Гагрино",
        "Ясная Поляна",
        "Частая Дубрава",
    ),
}

ICE_LOCALITIES = {
    "I": (
        "Елец",
        "Трубицино",
    ),
    "II": (
        "Казинка",
        "Паниковец",
        "Чаплыгин",
        "Доброе",
        "Кореневщино",
        "Большой Хомутец",
        "Бутырки",
        "Желтые пески",
        "Жёлтые пески",
        "Липецк",
        "Ленино",
        "Троицкое",
        "Матырский",
        "Двуречки",
    ),
    "III": (
        "Кузьминские Отвержки",
        "Новоселье",
        "Студеные Выселки",
        "Студёные Выселки",
        "Сырский",
        "Сырское",
        "Подгорное",
        "Крутые Хутора",
        "Боринское",
        "Стебаево",
        "Елецкая Лозовка",
        "Гнилуша",
        "Задонск",
    ),
    "IV": (
        "Ясная Поляна",
        "Бруслановка",
        "Кулешовка",
        "Сенцово",
        "Веселое",
        "Весёлое",
        "Тербуны",
    ),
}

CLIMATE_VALUES = {
    "I": {"ice_thickness": 10, "wind_speed": 25, "wind_pressure": 400},
    "II": {"ice_thickness": 15, "wind_speed": 29, "wind_pressure": 500},
    "III": {"ice_thickness": 20, "wind_speed": 32, "wind_pressure": 650},
    "IV": {"ice_thickness": 25, "wind_speed": 36, "wind_pressure": 800},
}


def calculate_materials(tu_data: dict[str, Any], plan_data: dict[str, Any]) -> dict[str, Any]:
    supports = plan_data.get("supports", {})
    p23 = int(supports.get("P23", 0) or 0)
    a23 = int(supports.get("A23", 0) or 0)
    ya23 = int(supports.get("YA23", 0) or 0)
    k21 = int(supports.get("K21", 0) or 0)
    ground = int(plan_data.get("grounding_count", 0) or 0)

    line_length_m = float(plan_data.get("line_length_m", 0) or 0)
    line_length_km = float(plan_data.get("line_length_km", line_length_m / 1000) or 0)
    phase = str(tu_data.get("FAZE", "")).lower()
    cable_section = str(tu_data.get("SECH_KABEL", ""))
    wire_weight_per_km = tu_data.get("wire_weight_final")

    sech_km = line_length_km * 1.045
    if wire_weight_per_km is not None:
        sech_kg = sech_km * float(wire_weight_per_km)
    elif cable_section == "3x70+1x70":
        sech_kg = sech_km * 1112
    elif cable_section == "3x50+1x50":
        sech_kg = sech_km * 775
    else:
        sech_kg = ""

    total_supports = p23 + a23 + ya23 + k21
    p23_1 = p23 * 0.36
    a231 = a23 * 0.72
    ya231 = ya23 * 0.9
    k21_1 = k21 * 0.45
    s1 = p23_1 + a231 + ya231 + k21_1
    pole_5 = k21 + ya23 * 2
    pole_3 = p23 + a23 * 2

    is_three_phase = "трехфаз" in phase or "трёхфаз" in phase
    is_single_phase = "однофаз" in phase
    sech_sip4 = (
        format_cable_section_display("4x16")
        if is_three_phase
        else format_cable_section_display("2x16")
        if is_single_phase
        else ""
    )
    sip4_kg = calculate_sip4_kg(sech_sip4, line_length_km) if sech_sip4 else None
    breaker = _breaker_spec(power_kw=tu_data.get("POWER_KW", ""), is_three_phase=is_three_phase, is_single_phase=is_single_phase)
    breaker_current = _breaker_current(breaker)
    climate = _climate_values(tu_data)
    a3_sheet_count = int(plan_data.get("a3_sheet_count", 1) or 1)
    sheet_labels = _sheet_labels_from_a3_count(a3_sheet_count)

    return {
        "LINE_LENGTH_M": line_length_m,
        "LINE_LENGTH_KM": line_length_km,
        "P23": p23,
        "A23": a23,
        "YA23": ya23,
        "K21": k21,
        "GROUND": ground,
        "SQUARE": line_length_m * 4,
        "FOBOS_FAZE": "ФОБОС 3" if is_three_phase else "ФОБОС 1" if is_single_phase else "",
        "SHIT": "КМПн-8" if is_three_phase else "КМПн-4" if is_single_phase else "",
        "QUANTITY": 8 if is_three_phase else 4 if is_single_phase else "",
        "SECH_SIP4": sech_sip4,
        "SIP4_KG": sip4_kg if sip4_kg is not None else "",
        "SECH_KM": sech_km,
        "SECH_KG": sech_kg,
        "S": total_supports,
        "SUPPORTS_COUNT": total_supports,
        "SUPPORTS_INSTALL_NOTE": _supports_install_note(total_supports),
        "BREAKER": breaker,
        "BREAKER_CURRENT": breaker_current,
        "BREAKER_POLES_TEXT": "трехполюсный" if is_three_phase else "однополюсный" if is_single_phase else "",
        "BREAKER_POLES_TEXT_GENITIVE": "трехполюсного" if is_three_phase else "однополюсного" if is_single_phase else "",
        "ICE_DISTRICT": climate["ice_district"],
        "WIND_DISTRICT": climate["wind_district"],
        "CLIMATE_DISTRICT": climate["ice_district"],
        "ICE_THICKNESS_MM": climate["ice_thickness"],
        "WIND_SPEED_MS": climate["wind_speed"],
        "WIND_PRESSURE_PA": climate["wind_pressure"],
        "THUNDERSTORM_HOURS": "80-100",
        "P23_1": p23_1,
        "A231": a231,
        "YA231": ya231,
        "K21_1": k21_1,
        "S1": s1,
        "Y4": a23,
        "5": pole_5,
        "51": pole_5 * 0.45,
        "3": pole_3,
        "31": pole_3 * 0.36,
        "ZP6": p23 * 0.3 + ya23 + k21 * 0.65 + a23 * 0.65,
        "X89": ya23,
        "F207": p23 * 2 + ya23 * 4 + k21 * 2 + a23 * 2 + 6,
        "NC20": p23 * 2 + ya23 * 4 + k21 * 2 + a23 * 2 + 6,
        "ES15": p23,
        "CS10": k21 * 2 + a23 * 2 + ya23 * 2,
        "PA15": k21 * 2 + a23 * 2 + ya23 * 2,
        "P95": 4,
        "P645": 4 if is_three_phase else 2 if is_single_phase else "",
        "P72": total_supports,
        "CD35": p23 + a23 * 2 + k21 * 2 + ya23 * 2,
        "E778": total_supports * 2,
        "GR": ground * 3,
        "A3_SHEET_COUNT": a3_sheet_count,
        "ROUTE_PLAN_SHEET": sheet_labels["route_plan_sheet"],
        "TOTAL_SHEETS": sheet_labels["total_sheets"],
    }


def _sheet_labels_from_a3_count(a3_sheet_count: int) -> dict[str, int | str]:
    count = max(1, int(a3_sheet_count or 1))
    total_sheets = 4 + count
    route_plan_sheet = "5" if count == 1 else f"5-{total_sheets}"
    return {
        "route_plan_sheet": route_plan_sheet,
        "total_sheets": total_sheets,
    }


def _supports_install_note(count: int) -> str:
    if count == 1:
        return "по одной опоре"
    return f"по {count} опорам"


def _breaker_spec(power_kw: Any, is_three_phase: bool, is_single_phase: bool) -> str:
    try:
        power = float(str(power_kw).replace(",", "."))
    except ValueError:
        return ""

    if is_three_phase:
        current = _match_breaker_current(
            power,
            (
                (3, 5),
                (5, 8),
                (7, 16),
                (7.5, 16),
                (8, 16),
                (9, 16),
                (10, 16),
                (12.5, 25),
                (15, 32),
                (20, 40),
                (30, 50),
            ),
        )
        return f"ВА47-29 3Р {current}А" if current else ""

    if is_single_phase:
        current = _match_breaker_current(
            power,
            (
                (1, 5),
                (2, 10),
                (3, 16),
                (5, 25),
                (6, 32),
                (6.7, 32),
                (8, 40),
            ),
        )
        return f"ВА47-29 1Р {current}А" if current else ""

    return ""


def _match_breaker_current(power: float, table: tuple[tuple[float, int], ...]) -> int:
    exact_epsilon = 0.001
    for kw, current in table:
        if abs(power - kw) <= exact_epsilon:
            return current

    for kw, current in table:
        if power <= kw:
            return current
    return table[-1][1] if table else 0


def _breaker_current(spec: str) -> str:
    if not spec:
        return ""
    return spec.rsplit(" ", 1)[-1]


def _climate_values(tu_data: dict[str, Any]) -> dict[str, Any]:
    ice_district = _detect_ice_district(tu_data) or "III"
    wind_district = _detect_wind_district(tu_data) or "III"
    ice_values = CLIMATE_VALUES[ice_district]
    wind_values = CLIMATE_VALUES[wind_district]
    return {
        "ice_district": ice_district,
        "wind_district": wind_district,
        "ice_thickness": ice_values["ice_thickness"],
        "wind_speed": wind_values["wind_speed"],
        "wind_pressure": wind_values["wind_pressure"],
    }


def _detect_wind_district(tu_data: dict[str, Any]) -> str:
    return _detect_climate_district(tu_data, WIND_LOCALITIES)


def _detect_ice_district(tu_data: dict[str, Any]) -> str:
    return _detect_climate_district(tu_data, ICE_LOCALITIES)


def _detect_climate_district(
    tu_data: dict[str, Any],
    localities: dict[str, tuple[str, ...]] | None = None,
) -> str:
    locality_map = localities or WIND_LOCALITIES
    address_parts = [
        str(tu_data[key])
        for key in ("ADRESS", "ADDRESS")
        if isinstance(tu_data.get(key), (str, int, float)) and str(tu_data[key]).strip()
    ]
    if address_parts:
        district = _match_climate_district_in_source(
            _normalize_climate_source(" ".join(address_parts)),
            locality_map,
        )
        if district:
            return district

    source = _normalize_climate_source(
        " ".join(str(value) for value in tu_data.values() if isinstance(value, (str, int, float)))
    )
    return _match_climate_district_in_source(source, locality_map)


def _match_climate_district_in_source(
    source: str,
    localities: dict[str, tuple[str, ...]],
) -> str:
    candidates: list[tuple[int, str, str]] = []
    for district, district_localities in localities.items():
        for locality in district_localities:
            normalized = _normalize_climate_source(locality)
            candidates.append((len(normalized), district, normalized))

    for _, district, locality in sorted(candidates, reverse=True):
        if _contains_locality(source, locality):
            return district
    return ""


def _normalize_climate_source(value: str) -> str:
    value = value.casefold().replace("ё", "е")
    return re.sub(r"\s+", " ", value).strip()


def _contains_locality(source: str, locality: str) -> bool:
    escaped = re.escape(locality)
    if " " in locality:
        pattern = escaped.replace(r"\ ", r"[\s,.;:()/\\-]+")
        return bool(re.search(rf"(?<![а-яa-z0-9]){pattern}(?![а-яa-z0-9])", source))
    return bool(re.search(rf"(?<![а-яa-z0-9]){escaped}(?![а-яa-z0-9])", source))
