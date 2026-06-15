from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cadastral_geocoder import CadastralGeocoderError, CadastralGeocoderService, Coordinates
from .address_parser import parse_plot_address
from .known_locations import ensure_not_near_res, is_within_district_hint, is_within_lipetsk_oblast, lookup_gazetteer
from .plot_geocoder import (
    geocode_partial_address_fallback,
    geocode_plot_address,
    geocode_settlement_only_fallback,
)
from .res_resolver import resolve_settlement_fallback_coordinates
from .route_distance import straight_line_km


MIN_DISTANCE_TO_RES_KM = 1.0


@dataclass(frozen=True)
class PlotLocationResult:
    coordinates: Coordinates
    method: str
    confidence: str = "medium"


def resolve_location_confidence(method: str) -> str:
    if method == "pkk_public_map":
        return "high"
    if method == "tu_address_geocoder":
        return "high"
    if method.startswith("settlement_gazetteer:"):
        return "medium"
    if method in {"tu_partial_address_geocoder", "settlement_geocode_fallback"}:
        return "medium"
    if method == "district_settlement_fallback":
        return "low"
    return "unknown"


def resolve_plot_location(
    *,
    plot_address: str,
    cadastral_number: str,
    tu_text: str,
    res_coordinates: Coordinates,
    cadastral_geocoder: CadastralGeocoderService | None = None,
    logger: Any | None = None,
) -> PlotLocationResult:
    geocoder = cadastral_geocoder or CadastralGeocoderService()
    plot_address = plot_address.strip()

    if plot_address:
        gazetteer = _lookup_gazetteer(plot_address, res_coordinates)
        if gazetteer is not None:
            if logger:
                logger.info(
                    f"Координаты участка из справочника ({gazetteer.method}) "
                    f"по к/н {cadastral_number}: "
                    f"lat={gazetteer.coordinates.lat}, lon={gazetteer.coordinates.lon}"
                )
            return gazetteer

    pkk_result = _try_pkk_coordinates(
        geocoder,
        cadastral_number,
        plot_address=plot_address,
        tu_text=tu_text,
        res_coordinates=res_coordinates,
        logger=logger,
    )
    if pkk_result is not None:
        return pkk_result

    if plot_address:
        if logger:
            logger.warning(
                "Публичная кадастровая карта недоступна. "
                f"Пробую геокодирование адреса участка из ТУ: {plot_address}"
            )
        return _resolve_from_tu_address(
            plot_address,
            cadastral_number,
            tu_text,
            res_coordinates,
            logger=logger,
        )

    if logger:
        logger.warning("Адрес участка в ТУ отсутствует. Использую запасную точку района.")
    return _district_fallback(tu_text, res_coordinates)


def _try_pkk_coordinates(
    geocoder: CadastralGeocoderService,
    cadastral_number: str,
    *,
    plot_address: str,
    tu_text: str,
    res_coordinates: Coordinates,
    logger: Any | None,
) -> PlotLocationResult | None:
    try:
        coordinates = geocoder.get_coordinates_by_cadastral_number(cadastral_number)
    except CadastralGeocoderError:
        return None

    if _is_valid_pkk_coordinates(coordinates, plot_address, tu_text):
        return PlotLocationResult(
            coordinates=coordinates,
            method="pkk_public_map",
            confidence="high",
        )

    if logger:
        logger.warning(
            "Координаты с кадастровой карты вне ожидаемого района. "
            "Пробую геокодирование адреса из ТУ."
        )
    if plot_address:
        return _resolve_from_tu_address(
            plot_address,
            cadastral_number,
            "",
            res_coordinates,
            logger=logger,
        )
    return None


def _resolve_from_tu_address(
    plot_address: str,
    cadastral_number: str,
    tu_text: str,
    res_coordinates: Coordinates,
    *,
    logger: Any | None,
) -> PlotLocationResult:
    try:
        coordinates = geocode_plot_address(
            plot_address,
            cadastral_number,
            destination_coordinates=res_coordinates,
        )
        return PlotLocationResult(coordinates=coordinates, method="tu_address_geocoder", confidence="high")
    except Exception:
        pass

    gazetteer = _lookup_gazetteer(plot_address, res_coordinates)
    if gazetteer is not None:
        if logger:
            logger.warning(
                "Полный адрес участка не найден. "
                f"Использую справочник: {gazetteer.method}"
            )
        return gazetteer

    partial = geocode_partial_address_fallback(
        plot_address,
        destination_coordinates=res_coordinates,
        min_distance_km=MIN_DISTANCE_TO_RES_KM,
    )
    if partial is not None:
        if logger:
            logger.warning(
                "Полный адрес участка не найден. "
                f"Использую уточнённый адрес: {partial.query}"
            )
        return PlotLocationResult(
            coordinates=partial.coordinates,
            method=partial.method,
            confidence=resolve_location_confidence(partial.method),
        )

    partial = geocode_partial_address_fallback(plot_address)
    if partial is not None and _is_valid_plot_coordinates(
        partial.coordinates,
        res_coordinates,
        plot_address,
    ):
        if logger:
            logger.warning(
                "Использую частичный адрес участка: "
                f"{partial.query}"
            )
        return PlotLocationResult(
            coordinates=partial.coordinates,
            method=partial.method,
            confidence=resolve_location_confidence(partial.method),
        )

    settlement = geocode_settlement_only_fallback(
        plot_address,
        destination_coordinates=res_coordinates,
    )
    if settlement is not None:
        if logger:
            logger.warning(
                "Точный адрес не найден. "
                f"Использую населённый пункт: {settlement.query}"
            )
        return PlotLocationResult(
            coordinates=settlement.coordinates,
            method=settlement.method,
            confidence="medium",
        )

    if logger:
        logger.warning(
            "Адрес участка не удалось геокодировать. "
            "Использую запасную точку района."
        )
    return _district_fallback(tu_text, res_coordinates)


def _district_fallback(tu_text: str, res_coordinates: Coordinates) -> PlotLocationResult:
    coordinates = ensure_not_near_res(
        resolve_settlement_fallback_coordinates(tu_text),
        res_coordinates,
    )
    return PlotLocationResult(
        coordinates=coordinates,
        method="district_settlement_fallback",
        confidence="low",
    )


def _lookup_gazetteer(
    plot_address: str,
    res_coordinates: Coordinates,
) -> PlotLocationResult | None:
    parsed = parse_plot_address(plot_address)
    gazetteer = lookup_gazetteer(
        district_hint=parsed.district or plot_address,
        settlement_name=parsed.settlement_name,
        garden_partnership=parsed.garden_partnership,
        street=parsed.street,
    )
    if gazetteer is None:
        return None

    if not gazetteer.street_specific and not _is_valid_plot_coordinates(
        gazetteer.coordinates,
        res_coordinates,
        plot_address,
    ):
        return None

    return PlotLocationResult(
        coordinates=gazetteer.coordinates,
        method=f"settlement_gazetteer:{gazetteer.label}",
        confidence="medium",
    )


def _is_valid_pkk_coordinates(
    coordinates: Coordinates,
    plot_address: str,
    tu_text: str,
) -> bool:
    hint = plot_address.strip() or tu_text
    if hint and is_within_district_hint(hint, coordinates):
        return True
    return is_within_lipetsk_oblast(coordinates)


def _is_valid_plot_coordinates(
    coordinates: Coordinates,
    res_coordinates: Coordinates,
    plot_address: str,
) -> bool:
    if straight_line_km(coordinates, res_coordinates) >= MIN_DISTANCE_TO_RES_KM:
        return True
    return not plot_address.strip()
