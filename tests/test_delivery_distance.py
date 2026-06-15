from __future__ import annotations

import unittest

from unittest.mock import patch

from backend.cad.oda_dwg_adapter import _replace_route_distance_km_hardcode
from backend.core.cadastral_extractor import extract_cadastral_numbers
from backend.core.cadastral_geocoder import CadastralGeocoderService, Coordinates
from backend.core.delivery_distance import DeliveryDistanceError, calculate_delivery_distance_from_tu
from backend.core.res_resolver import ResResolutionError, resolve_res_address
from backend.core.route_distance import AddressGeocoderService, RouteDistanceService


class MockCadastralProvider:
    name = "mock_cadastral"

    def __init__(self, coordinates: Coordinates | None) -> None:
        self._coordinates = coordinates

    def get_coordinates_by_cadastral_number(self, cadastral_number: str) -> Coordinates | None:
        return self._coordinates


class MockGeocoderProvider:
    name = "mock_geocoder"

    def __init__(self, coordinates: Coordinates | None) -> None:
        self._coordinates = coordinates

    def geocode_address(self, address: str) -> Coordinates | None:
        return self._coordinates


class MockRoutingProvider:
    name = "mock_routing"

    def __init__(self, distance_meters: int | None) -> None:
        self._distance_meters = distance_meters

    def get_driving_distance_meters(
        self,
        source: Coordinates,
        destination: Coordinates,
    ) -> int | None:
        return self._distance_meters


class ResResolverTests(unittest.TestCase):
    def test_lipetsk_city(self) -> None:
        result = resolve_res_address("Заявитель в г. Липецк, к/н 48:20:0000000:123")
        self.assertEqual(result["address"], "Липецкая область, Липецк, улица Механизаторов, 16")

    def test_lipetsk_district(self) -> None:
        result = resolve_res_address("Объект в Липецкий район Липецкой области")
        self.assertEqual(result["address"], "Липецкая область, Липецк, улица Механизаторов, 16")

    def test_dankov_district(self) -> None:
        result = resolve_res_address("Липецкая область, Данковский район")
        self.assertEqual(result["address"], "Липецкая область, Данков, Коммунальная улица, 23")

    def test_chaplygin_district(self) -> None:
        result = resolve_res_address("Чаплыгинский район")
        self.assertEqual(result["address"], "Липецкая область, село Доброе, Советская улица, 58А")
        self.assertEqual(result["resName"], "Чаплыгинский РЭС")

    def test_dobrovsky_district(self) -> None:
        result = resolve_res_address("Добровский район")
        self.assertEqual(result["address"], "Липецкая область, село Доброе, Советская улица, 58А")
        self.assertEqual(result["resName"], "Добровский РЭС")

    def test_gryazi_district(self) -> None:
        result = resolve_res_address("Грязинский район")
        self.assertEqual(result["address"], "Липецкая область, Грязи, Песковатская улица, 7")

    def test_gruzinsky_typo(self) -> None:
        result = resolve_res_address("Грузинский район")
        self.assertEqual(result["address"], "Липецкая область, Грязи, Песковатская улица, 7")

    def test_dobrinka_district(self) -> None:
        result = resolve_res_address("Добринский район")
        self.assertEqual(result["address"], "Липецкая область, Добринский район, посёлок Добринка, Профсоюзная улица, 8")

    def test_only_lipetsk_region_is_error(self) -> None:
        with self.assertRaises(ResResolutionError):
            resolve_res_address("Липецкая область, сельское поселение")


class DeliveryDistanceTests(unittest.TestCase):
    def _build_services(self, distance_meters: int) -> tuple[CadastralGeocoderService, RouteDistanceService]:
        source = Coordinates(lat=52.60, lon=39.57)
        destination = Coordinates(lat=52.61, lon=39.60)
        cadastral = CadastralGeocoderService([MockCadastralProvider(source)])
        routing = RouteDistanceService(
            geocoder=AddressGeocoderService([MockGeocoderProvider(destination)]),
            routing_providers=[MockRoutingProvider(distance_meters)],
        )
        return cadastral, routing

    def test_calculate_delivery_distance(self) -> None:
        cadastral, routing = self._build_services(46_500)
        tu_text = "г. Липецк, кадастровый номер 48:20:0000000:123"
        result = calculate_delivery_distance_from_tu(
            tu_text,
            cadastral_geocoder=cadastral,
            route_distance_service=routing,
        )
        self.assertEqual(result["cadastralNumber"], "48:20:0000000:123")
        self.assertEqual(result["distanceKm"], 47)
        self.assertEqual(result["provider"], "mock_routing")
        self.assertEqual(result["routeType"], "driving")

    def test_missing_cadastral_number(self) -> None:
        cadastral, routing = self._build_services(10_000)
        with self.assertRaises(DeliveryDistanceError):
            calculate_delivery_distance_from_tu(
                "г. Липецк без кадастрового номера",
                cadastral_geocoder=cadastral,
                route_distance_service=routing,
            )

    def test_fallback_to_tu_address_when_pkk_unavailable(self) -> None:
        from backend.core.cadastral_geocoder import CadastralGeocoderError, CadastralGeocoderService

        class FailingCadastralProvider:
            name = "failing"

            def get_coordinates_by_cadastral_number(self, cadastral_number: str):
                raise CadastralGeocoderError("pkk unavailable")

        cadastral = CadastralGeocoderService([FailingCadastralProvider()])
        routing = RouteDistanceService(
            routing_providers=[MockRoutingProvider(5_000)],
        )
        tu_text = "Добринский район, кадастровый номер 48:04:0600204:168"
        result = calculate_delivery_distance_from_tu(
            tu_text,
            fallback_address="",
            cadastral_geocoder=cadastral,
            route_distance_service=routing,
        )
        self.assertEqual(result["sourceMethod"], "district_settlement_fallback")
        self.assertGreaterEqual(result["distanceKm"], 2)

    def test_dobrinka_tu_address_is_about_4_km_to_res(self) -> None:
        from backend.core.cadastral_geocoder import CadastralGeocoderError, CadastralGeocoderService

        class FailingCadastralProvider:
            name = "failing"

            def get_coordinates_by_cadastral_number(self, cadastral_number: str):
                raise CadastralGeocoderError("pkk unavailable")

        cadastral = CadastralGeocoderService([FailingCadastralProvider()])
        routing = RouteDistanceService(routing_providers=[MockRoutingProvider(3200)])
        tu_text = "Добринский район, кадастровый номер 48:04:0600204:168"
        with patch(
            "backend.core.plot_location.geocode_plot_address",
            return_value=Coordinates(lat=52.189000, lon=40.486000),
        ):
            result = calculate_delivery_distance_from_tu(
                tu_text,
                fallback_address="Липецкая область, Добринский район, Добринка, ул.Новая, з.у. 9",
                cadastral_geocoder=cadastral,
                route_distance_service=routing,
            )
        self.assertEqual(result["sourceMethod"], "tu_address_geocoder")
        self.assertEqual(result["distanceKm"], 4)
        self.assertEqual(result["resName"], "Добринский РЭС")

    def test_dobrinka_uses_street_gazetteer_when_geocoder_fails(self) -> None:
        from backend.core.cadastral_geocoder import CadastralGeocoderError, CadastralGeocoderService

        class FailingCadastralProvider:
            name = "failing"

            def get_coordinates_by_cadastral_number(self, cadastral_number: str):
                raise CadastralGeocoderError("pkk unavailable")

        cadastral = CadastralGeocoderService([FailingCadastralProvider()])
        routing = RouteDistanceService(routing_providers=[MockRoutingProvider(3200)])
        tu_text = "Добринский район, кадастровый номер 48:04:0600204:168"
        with patch(
            "backend.core.plot_location.geocode_plot_address",
            side_effect=RuntimeError("geocoder unavailable"),
        ), patch(
            "backend.core.plot_location.geocode_partial_address_fallback",
            return_value=None,
        ):
            result = calculate_delivery_distance_from_tu(
                tu_text,
                fallback_address="Липецкая область, Добринский район, Добринка, ул.Новая, з.у. 9",
                cadastral_geocoder=cadastral,
                route_distance_service=routing,
            )
        self.assertEqual(result["sourceMethod"], "settlement_gazetteer:Добринка, ул. Новая")
        self.assertEqual(result["distanceKm"], 4)

    def test_pkk_coordinates_trusted_even_near_res(self) -> None:
        cadastral = CadastralGeocoderService(
            [MockCadastralProvider(Coordinates(lat=52.189000, lon=40.486000))]
        )
        routing = RouteDistanceService(routing_providers=[MockRoutingProvider(3200)])
        tu_text = "Добринский район, кадастровый номер 48:04:0600204:168"
        result = calculate_delivery_distance_from_tu(
            tu_text,
            fallback_address="Липецкая область, Добринский район, Добринка, ул.Новая, з.у. 9",
            cadastral_geocoder=cadastral,
            route_distance_service=routing,
        )
        self.assertEqual(result["sourceMethod"], "pkk_public_map")
        self.assertEqual(result["locationConfidence"], "high")
        self.assertEqual(result["distanceKm"], 4)

    def test_unknown_settlement_uses_settlement_geocode_fallback(self) -> None:
        from backend.core.cadastral_geocoder import CadastralGeocoderError, CadastralGeocoderService

        class FailingCadastralProvider:
            name = "failing"

            def get_coordinates_by_cadastral_number(self, cadastral_number: str):
                raise CadastralGeocoderError("pkk unavailable")

        cadastral = CadastralGeocoderService([FailingCadastralProvider()])
        routing = RouteDistanceService(routing_providers=[MockRoutingProvider(18_000)])
        tu_text = "Липецкий район, кадастровый номер 48:20:0000000:999"
        unknown_coords = Coordinates(lat=52.62, lon=39.48)
        with patch(
            "backend.core.plot_location.geocode_plot_address",
            side_effect=RuntimeError("not found"),
        ), patch(
            "backend.core.plot_location.geocode_partial_address_fallback",
            return_value=None,
        ), patch(
            "backend.core.plot_location.geocode_settlement_only_fallback",
            return_value=__import__(
                "backend.core.plot_geocoder", fromlist=["PlotGeocodeResult"]
            ).PlotGeocodeResult(
                coordinates=unknown_coords,
                method="settlement_geocode_fallback",
                query="село Новое, Липецкий район, Липецкая область, Россия",
            ),
        ):
            result = calculate_delivery_distance_from_tu(
                tu_text,
                fallback_address="Липецкая область, Липецкий район, село Новое, ул. Центральная",
                cadastral_geocoder=cadastral,
                route_distance_service=routing,
            )
        self.assertEqual(result["sourceMethod"], "settlement_geocode_fallback")
        self.assertEqual(result["locationConfidence"], "medium")

    def test_khomutets_tu_address_is_about_10_km_to_res(self) -> None:
        from backend.core.cadastral_geocoder import CadastralGeocoderError, CadastralGeocoderService

        class FailingCadastralProvider:
            name = "failing"

            def get_coordinates_by_cadastral_number(self, cadastral_number: str):
                raise CadastralGeocoderError("pkk unavailable")

        cadastral = CadastralGeocoderService([FailingCadastralProvider()])
        routing = RouteDistanceService(routing_providers=[MockRoutingProvider(9800)])
        tu_text = "Добровский район, кадастровый номер 48:12:0101010:123"
        with patch(
            "backend.core.plot_location.geocode_plot_address",
            return_value=Coordinates(lat=52.783138, lon=39.850802),
        ):
            result = calculate_delivery_distance_from_tu(
                tu_text,
                fallback_address=(
                    "Липецкая область, Добровский район, с/п Больше-Хомутецкий сельсовет, "
                    "с.Большой Хомутец, ул.Лужанская"
                ),
                cadastral_geocoder=cadastral,
                route_distance_service=routing,
            )
        self.assertEqual(result["sourceMethod"], "tu_address_geocoder")
        self.assertEqual(result["distanceKm"], 10)
        self.assertEqual(result["resName"], "Добровский РЭС")

    def test_dankov_snt_druzhba_is_about_4_km_to_res(self) -> None:
        from backend.core.cadastral_geocoder import CadastralGeocoderError, CadastralGeocoderService

        class FailingCadastralProvider:
            name = "failing"

            def get_coordinates_by_cadastral_number(self, cadastral_number: str):
                raise CadastralGeocoderError("pkk unavailable")

        cadastral = CadastralGeocoderService([FailingCadastralProvider()])
        routing = RouteDistanceService(routing_providers=[MockRoutingProvider(3160)])
        tu_text = "Данковский район, кадастровый номер 48:03:0690601:1211"
        with patch(
            "backend.core.plot_location.geocode_plot_address",
            return_value=Coordinates(lat=53.238023, lon=39.130602),
        ):
            result = calculate_delivery_distance_from_tu(
                tu_text,
                fallback_address='Липецкая область, г.Данков, снт "Дружба", участок № 614',
                cadastral_geocoder=cadastral,
                route_distance_service=routing,
            )
        self.assertEqual(result["sourceMethod"], "tu_address_geocoder")
        self.assertEqual(result["distanceKm"], 4)
        self.assertEqual(result["resName"], "Данковский РЭС")

    def test_dvurechki_is_about_26_km_to_gryazi_res(self) -> None:
        from backend.core.cadastral_geocoder import CadastralGeocoderError, CadastralGeocoderService

        class FailingCadastralProvider:
            name = "failing"

            def get_coordinates_by_cadastral_number(self, cadastral_number: str):
                raise CadastralGeocoderError("pkk unavailable")

        cadastral = CadastralGeocoderService([FailingCadastralProvider()])
        routing = RouteDistanceService(routing_providers=[MockRoutingProvider(25_800)])
        tu_text = "Грязинский район, кадастровый номер 48:02:0101010:123"
        with patch(
            "backend.core.plot_location.geocode_plot_address",
            return_value=Coordinates(lat=52.456365, lon=39.6516635),
        ):
            result = calculate_delivery_distance_from_tu(
                tu_text,
                fallback_address="Липецкая область, Грязинский район, Двуречки 1а",
                cadastral_geocoder=cadastral,
                route_distance_service=routing,
            )
        self.assertEqual(result["sourceMethod"], "tu_address_geocoder")
        self.assertEqual(result["distanceKm"], 26)
        self.assertEqual(result["resName"], "Грязинский РЭС")


class CadastralExtractorTests(unittest.TestCase):
    def test_extract_multiple_numbers(self) -> None:
        numbers = extract_cadastral_numbers(
            "к/н 48:20:0000001:10 и 48:21:0000002:20"
        )
        self.assertEqual(numbers, ["48:20:0000001:10", "48:21:0000002:20"])


class RouteDistanceHardcodeTests(unittest.TestCase):
    def test_replace_only_delivery_distance(self) -> None:
        text = (
            "расстояние от которой до объекта строительства составляет 23 км. "
            "Опора П23 и значение 23 без км не меняются."
        )
        replacement_map = {"{{ROUTE_DISTANCE_KM}}": "47"}
        updated, count = _replace_route_distance_km_hardcode(text, replacement_map)
        self.assertEqual(count, 1)
        self.assertIn("составляет 47 км", updated)
        self.assertIn("П23", updated)
        self.assertIn("значение 23 без", updated)

    def test_replace_split_mtext_fragment(self) -> None:
        text = r"объекта строительства составляет }{\A1;23 км."
        replacement_map = {"{{ROUTE_DISTANCE_KM}}": "47"}
        updated, count = _replace_route_distance_km_hardcode(text, replacement_map)
        self.assertEqual(count, 1)
        self.assertIn(r"составляет }{\A1;47 км.", updated)


if __name__ == "__main__":
    unittest.main()
