from __future__ import annotations

import time
from dataclasses import dataclass

from .address_parser import (
    ParsedPlotAddress,
    build_broad_geocode_queries,
    build_partial_fallback_queries,
    build_plot_geocode_queries,
    build_settlement_only_queries,
    parse_plot_address,
)
from .cadastral_geocoder import Coordinates
from .known_locations import is_near_res, is_within_district_hint, is_within_lipetsk_oblast
from .route_distance import (
    AddressGeocoderService,
    NominatimGeocoderProvider,
    PhotonGeocoderProvider,
    YandexGeocoderProvider,
)

MAX_GEOCODE_QUERIES = 12


NOMINATIM_DELAY_SECONDS = 1.1


@dataclass(frozen=True)
class PlotGeocodeResult:
    coordinates: Coordinates
    method: str
    query: str


@dataclass(frozen=True)
class _GeocodeCandidate:
    coordinates: Coordinates
    query: str
    in_district: bool
    query_rank: int


def geocode_plot_address(
    address: str,
    cadastral_number: str,
    *,
    destination_coordinates: Coordinates | None = None,
) -> Coordinates:
    return geocode_plot_address_detailed(
        address,
        cadastral_number,
        destination_coordinates=destination_coordinates,
    ).coordinates


def geocode_plot_address_detailed(
    address: str,
    cadastral_number: str,
    *,
    destination_coordinates: Coordinates | None = None,
) -> PlotGeocodeResult:
    parsed = parse_plot_address(address)
    geocoder = _build_plot_geocoder()
    specific_queries = build_plot_geocode_queries(parsed, cadastral_number)
    specific_queries.extend(build_partial_fallback_queries(parsed))

    result = _geocode_best_match(
        geocoder,
        parsed,
        address,
        specific_queries,
        method="tu_address_geocoder",
        destination_coordinates=destination_coordinates,
    )
    if result is not None:
        return result

    relaxed = _geocode_best_match(
        geocoder,
        parsed,
        address,
        specific_queries[:MAX_GEOCODE_QUERIES],
        method="tu_address_geocoder",
        destination_coordinates=destination_coordinates,
        require_district_match=False,
    )
    if relaxed is not None:
        return relaxed

    if _address_has_specific_location(parsed):
        raise RuntimeError(_format_geocode_errors(parsed, specific_queries))

    broad_queries = build_broad_geocode_queries(parsed, cadastral_number)
    result = _geocode_best_match(
        geocoder,
        parsed,
        address,
        broad_queries,
        method="tu_address_geocoder",
        destination_coordinates=destination_coordinates,
    )
    if result is not None:
        return result
    raise RuntimeError(_format_geocode_errors(parsed, specific_queries + broad_queries))


def geocode_partial_address_fallback(
    address: str,
    *,
    destination_coordinates: Coordinates | None = None,
    min_distance_km: float = 1.0,
) -> PlotGeocodeResult | None:
    parsed = parse_plot_address(address)
    geocoder = _build_plot_geocoder()
    queries = build_partial_fallback_queries(parsed)
    return _geocode_best_match(
        geocoder,
        parsed,
        address,
        queries,
        method="tu_partial_address_geocoder",
        destination_coordinates=destination_coordinates,
        min_distance_km=min_distance_km,
    )


def geocode_settlement_only_fallback(
    address: str,
    *,
    destination_coordinates: Coordinates | None = None,
) -> PlotGeocodeResult | None:
    parsed = parse_plot_address(address)
    if not parsed.settlement_name and not parsed.garden_partnership:
        return None

    geocoder = _build_plot_geocoder()
    queries = build_settlement_only_queries(parsed)
    return _geocode_best_match(
        geocoder,
        parsed,
        address,
        queries,
        method="settlement_geocode_fallback",
        destination_coordinates=destination_coordinates,
        require_district_match=False,
        match_settlement_only=True,
    )


def _build_plot_geocoder() -> AddressGeocoderService:
    return AddressGeocoderService(
        [YandexGeocoderProvider(), NominatimGeocoderProvider(), PhotonGeocoderProvider()]
    )


def _geocode_best_match(
    geocoder: AddressGeocoderService,
    parsed: ParsedPlotAddress,
    address: str,
    queries: list[str],
    *,
    method: str,
    destination_coordinates: Coordinates | None = None,
    min_distance_km: float = 0.0,
    require_district_match: bool = True,
    match_settlement_only: bool = False,
) -> PlotGeocodeResult | None:
    candidates: list[_GeocodeCandidate] = []
    seen_coords: set[tuple[float, float]] = set()
    last_nominatim_at = 0.0

    for index, query in enumerate(queries[:MAX_GEOCODE_QUERIES]):
        try:
            coordinates = _geocode_query(geocoder, query, last_nominatim_at)
            last_nominatim_at = time.monotonic()
        except Exception:
            continue

        key = (round(coordinates.lat, 5), round(coordinates.lon, 5))
        if key in seen_coords:
            continue
        seen_coords.add(key)

        if not is_within_lipetsk_oblast(coordinates):
            continue
        if not _query_matches_address(parsed, query, settlement_only=match_settlement_only):
            continue
        if destination_coordinates is not None:
            if is_near_res(
                coordinates,
                destination_coordinates,
                min_distance_km=max(min_distance_km, 1.0)
                if _address_has_precise_location(parsed)
                else min_distance_km,
            ):
                continue

        in_district = is_within_district_hint(address, coordinates)
        if require_district_match and parsed.settlement_name and not in_district:
            continue

        candidates.append(
            _GeocodeCandidate(
                coordinates=coordinates,
                query=query,
                in_district=in_district,
                query_rank=index,
            )
        )

    if not candidates:
        return None

    prefer_near_destination = (
        destination_coordinates is not None and not _address_has_precise_location(parsed)
    )
    if prefer_near_destination:
        from .route_distance import straight_line_km

        candidates.sort(
            key=lambda candidate: (
                -int(candidate.in_district),
                straight_line_km(candidate.coordinates, destination_coordinates),
                candidate.query_rank,
            )
        )
    else:
        candidates.sort(key=_candidate_score)
    best = candidates[0]
    return PlotGeocodeResult(coordinates=best.coordinates, method=method, query=best.query)


def _geocode_query(
    geocoder: AddressGeocoderService,
    query: str,
    last_nominatim_at: float,
) -> Coordinates:
    elapsed = time.monotonic() - last_nominatim_at
    if elapsed < NOMINATIM_DELAY_SECONDS:
        time.sleep(NOMINATIM_DELAY_SECONDS - elapsed)
    return geocoder.geocode_address(query)


def _address_has_specific_location(parsed: ParsedPlotAddress) -> bool:
    return bool(
        parsed.garden_partnership
        or parsed.settlement_name
        or parsed.street
        or parsed.plot_number
        or parsed.house_number
    )


def _address_has_precise_location(parsed: ParsedPlotAddress) -> bool:
    return bool(
        parsed.garden_partnership
        or parsed.street
        or parsed.plot_number
        or parsed.house_number
    )


def _query_matches_address(
    parsed: ParsedPlotAddress,
    query: str,
    *,
    settlement_only: bool = False,
) -> bool:
    normalized_query = query.casefold().replace("ё", "е")

    if parsed.garden_partnership:
        garden = parsed.garden_partnership.casefold().replace("ё", "е")
        if garden not in normalized_query and "снт" not in normalized_query:
            return False

    if parsed.settlement_name:
        settlement = parsed.settlement_name.casefold().replace("ё", "е")
        if settlement not in normalized_query:
            return False

    if settlement_only:
        return True

    if parsed.street:
        street = parsed.street.casefold().replace("ё", "е")
        if street not in normalized_query:
            return False

    return True


def _candidate_score(candidate: _GeocodeCandidate) -> tuple[int, int]:
    return (-candidate.query_rank, -int(candidate.in_district))


def _format_geocode_errors(parsed: ParsedPlotAddress, queries: list[str]) -> str:
    return (
        f"Не удалось геокодировать адрес участка ({parsed.normalized}). "
        f"Пробовано запросов: {len(queries)}"
    )
