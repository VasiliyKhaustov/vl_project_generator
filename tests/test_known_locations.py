from __future__ import annotations

import unittest

from backend.core.cadastral_geocoder import Coordinates
from backend.core.known_locations import ensure_not_near_res, is_near_res


class KnownLocationsTests(unittest.TestCase):
    def test_gazetteer_lookup_dobrinka_novaya_street(self) -> None:
        from backend.core.known_locations import lookup_gazetteer

        result = lookup_gazetteer(
            district_hint="Добринский район",
            settlement_name="Добринка",
            street="Новая",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.street_specific)
        self.assertAlmostEqual(result.coordinates.lat, 52.189000, places=3)

    def test_gazetteer_lookup_dvurechki(self) -> None:
        from backend.core.known_locations import lookup_gazetteer_coordinates

        coords = lookup_gazetteer_coordinates(
            district_hint="Грязинский район",
            settlement_name="Двуречки",
        )
        self.assertIsNotNone(coords)
        self.assertAlmostEqual(coords.lat, 52.456365, places=3)

    def test_gryazi_settlement_fallback_is_not_on_res(self) -> None:
        res = Coordinates(lat=52.487222, lon=39.928056)
        fallback = Coordinates(lat=52.471000, lon=39.790000)
        self.assertFalse(is_near_res(fallback, res))

    def test_ensure_not_near_res_shifts_point(self) -> None:
        res = Coordinates(lat=52.487222, lon=39.928056)
        same_as_res = Coordinates(lat=52.487222, lon=39.928056)
        shifted = ensure_not_near_res(same_as_res, res)
        self.assertFalse(is_near_res(shifted, res))


if __name__ == "__main__":
    unittest.main()
