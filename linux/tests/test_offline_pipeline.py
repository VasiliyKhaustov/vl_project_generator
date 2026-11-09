from __future__ import annotations

import time
import unittest
from unittest.mock import patch

from backend.core.cadastral_geocoder import CadastralGeocoderError, CadastralGeocoderService, Coordinates
from backend.core.delivery_distance import calculate_delivery_distance_from_tu
from backend.core.network import internet_reachable, run_with_timeout
from backend.core.route_distance import RouteDistanceService


class OfflinePipelineTests(unittest.TestCase):
    def test_empty_cadastral_providers_do_not_use_defaults(self) -> None:
        service = CadastralGeocoderService(providers=[])
        with self.assertRaises(CadastralGeocoderError):
            service.get_coordinates_by_cadastral_number("48:20:0000000:123")

    def test_empty_routing_providers_use_straight_line(self) -> None:
        router = RouteDistanceService(routing_providers=[])
        result = router.get_driving_distance_km_between(
            Coordinates(lat=52.6, lon=39.6),
            Coordinates(lat=52.7, lon=39.7),
        )
        self.assertEqual(result.provider, "straight_line_estimate")
        self.assertGreater(result.distance_km, 0)

    def test_run_with_timeout_does_not_wait_for_hung_task(self) -> None:
        def hang() -> None:
            time.sleep(30)

        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            run_with_timeout(hang, 0.2)
        self.assertLess(time.monotonic() - started, 2.0)

    def test_internet_probe_returns_quickly_when_blocked(self) -> None:
        started = time.monotonic()
        with patch("backend.core.network.socket.create_connection", side_effect=OSError("offline")):
            self.assertFalse(internet_reachable(timeout_s=0.2))
        self.assertLess(time.monotonic() - started, 2.0)

    def test_offline_delivery_does_not_call_maps(self) -> None:
        with patch("backend.core.delivery_distance.internet_reachable", return_value=False):
            with patch("backend.core.cadastral_http.request_json") as request_json:
                result = calculate_delivery_distance_from_tu(
                    "г. Липецк, кадастровый номер 48:20:0000000:123",
                    fallback_address="Липецкая область, г. Липецк",
                )
        request_json.assert_not_called()
        self.assertGreater(result["distanceKm"], 0)
        self.assertIn(result["provider"], {"straight_line_estimate", "nearby_minimum"})
