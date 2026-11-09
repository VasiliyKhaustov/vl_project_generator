from __future__ import annotations

import unittest

from backend.core.address_parser import parse_plot_address
from backend.core.cadastral_geocoder import Coordinates
from backend.core.plot_geocoder import _address_has_precise_location, _geocode_best_match, _build_plot_geocoder


class PlotGeocoderNearResTests(unittest.TestCase):
    def test_city_only_address_is_not_precise(self) -> None:
        parsed = parse_plot_address("Липецкая область, г.Липецк")
        self.assertFalse(_address_has_precise_location(parsed))

    def test_street_address_is_precise(self) -> None:
        parsed = parse_plot_address(
            "Липецкая область, Добринский район, Добринка, ул.Новая, з.у. 9"
        )
        self.assertTrue(_address_has_precise_location(parsed))

    def test_city_only_geocode_prefers_point_closer_to_res(self) -> None:
        parsed = parse_plot_address("Липецкая область, г.Липецк")
        res = Coordinates(lat=52.583727, lon=39.565908)
        near_res = Coordinates(lat=52.6051488, lon=39.5963775)
        far_point = Coordinates(lat=52.5931145, lon=39.511147)
        calls: list[str] = []

        class SequenceGeocoder:
            def geocode_address(self, address: str) -> Coordinates:
                calls.append(address)
                if "город Липецк" in address or address.startswith("Липецк,"):
                    return near_res
                return far_point

        result = _geocode_best_match(
            SequenceGeocoder(),
            parsed,
            "Липецкая область, г.Липецк",
            [
                "город Липецк, г. Липецк, Липецкая область, Россия",
                "Липецкая область, г. Липецк, Россия",
            ],
            method="tu_address_geocoder",
            destination_coordinates=res,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertAlmostEqual(result.coordinates.lat, near_res.lat, places=4)
        self.assertAlmostEqual(result.coordinates.lon, near_res.lon, places=4)


if __name__ == "__main__":
    unittest.main()
