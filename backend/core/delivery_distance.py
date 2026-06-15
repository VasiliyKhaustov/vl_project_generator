from __future__ import annotations

from typing import Any

from .cadastral_extractor import extract_cadastral_numbers
from .cadastral_geocoder import CadastralGeocoderService
from .plot_location import resolve_plot_location
from .res_resolver import (
    ResResolutionError,
    resolve_res_address,
    resolve_res_coordinates,
)
from .route_distance import RouteDistanceError, RouteDistanceService


class DeliveryDistanceError(Exception):
    pass


def calculate_delivery_distance_from_tu(
    tu_text: str,
    *,
    fallback_address: str = "",
    cadastral_geocoder: CadastralGeocoderService | None = None,
    route_distance_service: RouteDistanceService | None = None,
    logger: Any | None = None,
) -> dict[str, Any]:
    cadastral_numbers = extract_cadastral_numbers(tu_text)
    if logger:
        logger.info(f"Найденные кадастровые номера: {cadastral_numbers or 'нет'}")
    if not cadastral_numbers:
        raise DeliveryDistanceError("Кадастровый номер не найден в тексте ТУ.")

    cadastral_number = cadastral_numbers[0]
    if len(cadastral_numbers) > 1 and logger:
        logger.warning(
            "В ТУ найдено несколько кадастровых номеров. "
            f"Используется первый: {cadastral_number}. Все номера: {', '.join(cadastral_numbers)}"
        )

    try:
        res_info = resolve_res_address(tu_text)
    except ResResolutionError as exc:
        raise DeliveryDistanceError(str(exc)) from exc

    if logger:
        logger.info(f"Выбран РЭС: {res_info['resName']} ({res_info['matchedRule']})")
        logger.info(f"Адрес РЭС: {res_info['address']}")
        logger.info(
            "Координаты РЭС: "
            f"lat={res_info['coordinates']['lat']}, lon={res_info['coordinates']['lon']}"
        )

    geocoder = cadastral_geocoder or CadastralGeocoderService()
    router = route_distance_service or RouteDistanceService()
    destination_coordinates = resolve_res_coordinates(tu_text)

    plot_location = resolve_plot_location(
        plot_address=fallback_address,
        cadastral_number=cadastral_number,
        tu_text=tu_text,
        res_coordinates=destination_coordinates,
        cadastral_geocoder=geocoder,
        logger=logger,
    )
    source_coordinates = plot_location.coordinates
    source_method = plot_location.method

    if logger:
        logger.info(
            f"Координаты участка ({source_method}) по к/н {cadastral_number}: "
            f"lat={source_coordinates.lat}, lon={source_coordinates.lon}"
        )

    try:
        route_result = router.get_driving_distance_km_between(
            source_coordinates,
            destination_coordinates,
        )
    except RouteDistanceError as exc:
        raise DeliveryDistanceError(str(exc)) from exc

    if logger:
        logger.info(f"Расстояние по маршруту: {route_result.distance_meters} м")
        logger.info(f"Расстояние по маршруту: {route_result.distance_km} км")
        if route_result.straight_line_km is not None:
            logger.info(
                f"Расстояние по прямой (debug): {route_result.straight_line_km} км"
            )
        logger.info(f"Провайдер маршрутизации: {route_result.provider}")

    return {
        "cadastralNumber": cadastral_number,
        "cadastralNumbers": cadastral_numbers,
        "sourceMethod": source_method,
        "locationConfidence": plot_location.confidence,
        "resName": res_info["resName"],
        "matchedRule": res_info["matchedRule"],
        "destinationAddress": res_info["address"],
        "sourceCoordinates": {
            "lat": source_coordinates.lat,
            "lon": source_coordinates.lon,
        },
        "destinationCoordinates": {
            "lat": route_result.destination_coordinates.lat,
            "lon": route_result.destination_coordinates.lon,
        },
        "distanceMeters": route_result.distance_meters,
        "distanceKm": route_result.distance_km,
        "provider": route_result.provider,
        "routeType": route_result.route_type,
        "straightLineKm": route_result.straight_line_km,
    }
