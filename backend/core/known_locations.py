from __future__ import annotations

from dataclasses import dataclass

from .cadastral_geocoder import Coordinates


# Проверенные координаты РЭС и запасных точек районов в Липецкой области.
RES_COORDINATES: dict[str, Coordinates] = {
    "Липецкая область, Добринский район, посёлок Добринка, Профсоюзная улица, 8": Coordinates(
        lat=52.170900,
        lon=40.466800,
    ),
    "Липецкая область, Липецк, улица Механизаторов, 16": Coordinates(
        lat=52.583727,
        lon=39.565908,
    ),
    "Липецкая область, Данков, Коммунальная улица, 23": Coordinates(
        lat=53.247913,
        lon=39.110207,
    ),
    "Липецкая область, село Доброе, Советская улица, 58А": Coordinates(
        lat=52.864888,
        lon=39.803317,
    ),
    "Липецкая область, Грязи, Песковатская улица, 7": Coordinates(
        lat=52.487222,
        lon=39.928056,
    ),
}

SETTLEMENT_COORDINATES: dict[str, Coordinates] = {
    "Добринский район / Добринка": Coordinates(lat=52.170456, lon=40.467195),
    "Грязи / Грязинский район": Coordinates(lat=52.471000, lon=39.790000),
    "Данков / Данковский район": Coordinates(lat=53.244472, lon=39.141798),
    "Чаплыгин / Чаплыгинский район": Coordinates(lat=53.243000, lon=39.967000),
    "Доброе / Добровский район": Coordinates(lat=52.786024, lon=39.854840),
    "Липецк / Липецкий район": Coordinates(lat=52.610278, lon=39.594167),
}

MIN_DISTANCE_TO_RES_KM = 1.0

# Справочник центров населённых пунктов и СНТ, которые плохо находятся через API.
SETTLEMENT_GAZETTEER: dict[tuple[str, str], Coordinates] = {
    ("добрин", "добринка"): Coordinates(lat=52.170456, lon=40.467195),
    ("добров", "большой хомутец"): Coordinates(lat=52.783138, lon=39.850802),
    ("данков", "дружба"): Coordinates(lat=53.238023, lon=39.130602),
    ("гряз", "двуречки"): Coordinates(lat=52.456365, lon=39.6516635),
}

# Улицы внутри населённого пункта, когда РЭС находится в том же НП.
STREET_GAZETTEER: dict[tuple[str, str, str], Coordinates] = {
    ("добрин", "добринка", "новая"): Coordinates(lat=52.189000, lon=40.486000),
}

@dataclass(frozen=True)
class GazetteerLookup:
    coordinates: Coordinates
    street_specific: bool
    label: str

LIPETSK_OBLAST_BOUNDS = {
    "min_lat": 51.8,
    "max_lat": 53.6,
    "min_lon": 37.5,
    "max_lon": 41.0,
}

DISTRICT_BOUNDS: dict[str, dict[str, float]] = {
    "добрин": {"min_lat": 52.05, "max_lat": 52.25, "min_lon": 40.35, "max_lon": 40.60},
    "гряз": {"min_lat": 52.35, "max_lat": 52.60, "min_lon": 39.45, "max_lon": 40.10},
    "данков": {"min_lat": 53.10, "max_lat": 53.40, "min_lon": 38.90, "max_lon": 39.30},
    "добров": {"min_lat": 52.55, "max_lat": 52.95, "min_lon": 39.45, "max_lon": 40.15},
    "чаплыгин": {"min_lat": 52.95, "max_lat": 53.45, "min_lon": 39.70, "max_lon": 40.25},
    "липецк": {"min_lat": 52.45, "max_lat": 52.75, "min_lon": 39.35, "max_lon": 39.85},
}


def get_res_coordinates(address: str) -> Coordinates | None:
    return RES_COORDINATES.get(address.strip())


def get_settlement_coordinates(matched_rule: str) -> Coordinates | None:
    return SETTLEMENT_COORDINATES.get(matched_rule)


def is_within_lipetsk_oblast(coordinates: Coordinates) -> bool:
    return (
        LIPETSK_OBLAST_BOUNDS["min_lat"] <= coordinates.lat <= LIPETSK_OBLAST_BOUNDS["max_lat"]
        and LIPETSK_OBLAST_BOUNDS["min_lon"] <= coordinates.lon <= LIPETSK_OBLAST_BOUNDS["max_lon"]
    )


def is_within_district_hint(address: str, coordinates: Coordinates) -> bool:
    normalized = address.lower().replace("ё", "е")
    for hint, bounds in DISTRICT_BOUNDS.items():
        if hint in normalized:
            return (
                bounds["min_lat"] <= coordinates.lat <= bounds["max_lat"]
                and bounds["min_lon"] <= coordinates.lon <= bounds["max_lon"]
            )
    return is_within_lipetsk_oblast(coordinates)


def is_near_res(
    coordinates: Coordinates,
    res_coordinates: Coordinates,
    *,
    min_distance_km: float = MIN_DISTANCE_TO_RES_KM,
) -> bool:
    from .route_distance import straight_line_km

    return straight_line_km(coordinates, res_coordinates) < min_distance_km


def ensure_not_near_res(
    coordinates: Coordinates,
    res_coordinates: Coordinates,
    *,
    min_distance_km: float = MIN_DISTANCE_TO_RES_KM,
) -> Coordinates:
    if not is_near_res(coordinates, res_coordinates, min_distance_km=min_distance_km):
        return coordinates
    shifted = Coordinates(
        lat=round(coordinates.lat + 0.015, 6),
        lon=round(coordinates.lon + 0.015, 6),
    )
    if is_near_res(shifted, res_coordinates, min_distance_km=min_distance_km):
        shifted = Coordinates(
            lat=round(coordinates.lat - 0.02, 6),
            lon=round(coordinates.lon + 0.02, 6),
        )
    return shifted


def lookup_gazetteer_coordinates(
    *,
    district_hint: str,
    settlement_name: str | None = None,
    garden_partnership: str | None = None,
    street: str | None = None,
) -> Coordinates | None:
    result = lookup_gazetteer(district_hint=district_hint, settlement_name=settlement_name,
                              garden_partnership=garden_partnership, street=street)
    return result.coordinates if result else None


def lookup_gazetteer(
    *,
    district_hint: str,
    settlement_name: str | None = None,
    garden_partnership: str | None = None,
    street: str | None = None,
) -> GazetteerLookup | None:
    normalized_district = district_hint.lower().replace("ё", "е")
    district_key = _match_district_key(normalized_district)
    if district_key is None:
        return None

    settlement_candidates: list[tuple[str, str]] = []
    if garden_partnership:
        settlement_candidates.append(("garden", garden_partnership.lower().replace("ё", "е")))
    if settlement_name:
        settlement_candidates.append(("settlement", settlement_name.lower().replace("ё", "е")))

    if street:
        normalized_street = street.lower().replace("ё", "е")
        for kind, settlement_key in settlement_candidates:
            coords = STREET_GAZETTEER.get((district_key, settlement_key, normalized_street))
            if coords is not None:
                label = (
                    garden_partnership
                    if kind == "garden" and garden_partnership
                    else f"{settlement_name}, ул. {street}"
                )
                return GazetteerLookup(
                    coordinates=coords,
                    street_specific=True,
                    label=label or normalized_street,
                )

    for kind, settlement_key in settlement_candidates:
        coords = SETTLEMENT_GAZETTEER.get((district_key, settlement_key))
        if coords is not None:
            label = garden_partnership if kind == "garden" and garden_partnership else settlement_name
            return GazetteerLookup(
                coordinates=coords,
                street_specific=False,
                label=label or settlement_key,
            )
    return None


def _match_district_key(normalized_district: str) -> str | None:
    for hint in DISTRICT_BOUNDS:
        if hint in normalized_district:
            return hint
    return None

