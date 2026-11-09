from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.core.cadastral_geocoder import CadastralGeocoderError, CadastralGeocoderService, Coordinates
from backend.core.delivery_distance import calculate_delivery_distance_from_tu
from backend.core.route_distance import RouteDistanceService


class FailingCadastralProvider:
    name = "failing"

    def get_coordinates_by_cadastral_number(self, cadastral_number: str):
        raise CadastralGeocoderError("pkk unavailable")


# Проверенные кейсы из реальных ТУ.
KNOWN_TU_CASES = (
    {
        "name": "dobrinka",
        "tu_text": "Добринский район, кадастровый номер 48:04:0600204:168",
        "address": "Липецкая область, Добринский район, Добринка, ул.Новая, з.у. 9",
        "plot_coords": Coordinates(lat=52.189000, lon=40.486000),
        "route_meters": 3_200,
        "expected_km": 4,
        "res_name": "Добринский РЭС",
    },
    {
        "name": "khomutets",
        "tu_text": "Добровский район, кадастровый номер 48:12:0101010:123",
        "address": (
            "Липецкая область, Добровский район, с/п Больше-Хомутецкий сельсовет, "
            "с.Большой Хомутец, ул.Лужанская"
        ),
        "plot_coords": Coordinates(lat=52.783138, lon=39.850802),
        "route_meters": 9_800,
        "expected_km": 10,
        "res_name": "Добровский РЭС",
    },
    {
        "name": "dankov_druzhba",
        "tu_text": "Данковский район, кадастровый номер 48:03:0690601:1211",
        "address": 'Липецкая область, г.Данков, снт "Дружба", участок № 614',
        "plot_coords": Coordinates(lat=53.238023, lon=39.130602),
        "route_meters": 3_160,
        "expected_km": 4,
        "res_name": "Данковский РЭС",
    },
    {
        "name": "dvurechki",
        "tu_text": "Грязинский район, кадастровый номер 48:02:0101010:123",
        "address": "Липецкая область, Грязинский район, Двуречки 1а",
        "plot_coords": Coordinates(lat=52.456365, lon=39.6516635),
        "route_meters": 25_800,
        "expected_km": 26,
        "res_name": "Грязинский РЭС",
    },
)


class KnownTuCasesTests(unittest.TestCase):
    def test_all_known_tu_cases(self) -> None:
        cadastral = CadastralGeocoderService([FailingCadastralProvider()])
        for case in KNOWN_TU_CASES:
            with self.subTest(case=case["name"]):
                routing = RouteDistanceService(
                    routing_providers=[_MockRoutingProvider(case["route_meters"])]
                )
                with patch(
                    "backend.core.plot_location.geocode_plot_address",
                    return_value=case["plot_coords"],
                ):
                    result = calculate_delivery_distance_from_tu(
                        case["tu_text"],
                        fallback_address=case["address"],
                        cadastral_geocoder=cadastral,
                        route_distance_service=routing,
                    )
                self.assertEqual(result["sourceMethod"], "tu_address_geocoder")
                self.assertEqual(result["distanceKm"], case["expected_km"])
                self.assertEqual(result["resName"], case["res_name"])


class _MockRoutingProvider:
    name = "mock_routing"

    def __init__(self, distance_meters: int) -> None:
        self._distance_meters = distance_meters

    def get_driving_distance_meters(
        self,
        source: Coordinates,
        destination: Coordinates,
    ) -> int | None:
        return self._distance_meters


if __name__ == "__main__":
    unittest.main()
