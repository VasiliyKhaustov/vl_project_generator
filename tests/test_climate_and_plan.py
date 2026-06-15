from __future__ import annotations

import unittest
from pathlib import Path

from backend.core.calculator import (
    _climate_values,
    _detect_ice_district,
    _detect_wind_district,
)
from backend.core.dxf_reader import analyze_dxf


class ClimateDistrictTests(unittest.TestCase):
    def test_kazinka_wind_one_ice_two(self) -> None:
        tu_data = {"ADRESS": "Липецкая область, с. Казинка"}
        self.assertEqual(_detect_wind_district(tu_data), "I")
        self.assertEqual(_detect_ice_district(tu_data), "II")
        climate = _climate_values(tu_data)
        self.assertEqual(climate["wind_district"], "I")
        self.assertEqual(climate["ice_district"], "II")
        self.assertEqual(climate["wind_speed"], 25)
        self.assertEqual(climate["ice_thickness"], 15)

    def test_lenino_wind_three_ice_two(self) -> None:
        tu_data = {"ADRESS": "Липецкая область, с. Ленино"}
        self.assertEqual(_detect_wind_district(tu_data), "III")
        self.assertEqual(_detect_ice_district(tu_data), "II")
        climate = _climate_values(tu_data)
        self.assertEqual(climate["wind_speed"], 32)
        self.assertEqual(climate["ice_thickness"], 15)

    def test_lipetsk_wind_and_ice_two(self) -> None:
        tu_data = {"ADRESS": "Липецкая область, г.Липецк"}
        self.assertEqual(_detect_wind_district(tu_data), "II")
        self.assertEqual(_detect_ice_district(tu_data), "II")
        climate = _climate_values(tu_data)
        self.assertEqual(climate["wind_speed"], 29)
        self.assertEqual(climate["ice_thickness"], 15)

    def test_address_has_priority_over_other_tu_fields(self) -> None:
        tu_data = {
            "ADRESS": "Липецкая область, г.Липецк",
            "OTKUDASTROIT": "от опоры в с. Казинка",
        }
        self.assertEqual(_detect_wind_district(tu_data), "II")
        self.assertEqual(_detect_ice_district(tu_data), "II")

    def test_dankov_is_wind_zone_two(self) -> None:
        tu_data = {"ADRESS": "Липецкая область, г. Данков"}
        self.assertEqual(_detect_wind_district(tu_data), "II")
        self.assertEqual(_detect_ice_district(tu_data), "")
        self.assertEqual(_climate_values(tu_data)["ice_district"], "III")

    def test_yasnaya_polyana_is_zone_four_for_both(self) -> None:
        tu_data = {"ADRESS": "Липецкая область, п. Ясная Поляна"}
        self.assertEqual(_detect_wind_district(tu_data), "IV")
        self.assertEqual(_detect_ice_district(tu_data), "IV")

    def test_korenevshino_ice_two_wind_default_three(self) -> None:
        tu_data = {"ADRESS": "Липецкая область, Добровский район, с.Кореневщино"}
        self.assertEqual(_detect_ice_district(tu_data), "II")
        self.assertEqual(_detect_wind_district(tu_data), "")
        climate = _climate_values(tu_data)
        self.assertEqual(climate["ice_district"], "II")
        self.assertEqual(climate["wind_district"], "III")
        self.assertEqual(climate["ice_thickness"], 15)
        self.assertEqual(climate["wind_speed"], 32)

    def test_elets_wind_one_ice_one(self) -> None:
        tu_data = {"ADRESS": "Липецкая область, г. Елец"}
        self.assertEqual(_detect_wind_district(tu_data), "I")
        self.assertEqual(_detect_ice_district(tu_data), "I")
        climate = _climate_values(tu_data)
        self.assertEqual(climate["wind_speed"], 25)
        self.assertEqual(climate["ice_thickness"], 10)


class PlanSupportCountTests(unittest.TestCase):
    def test_project_178_excludes_existing_branch_support_off_route(self) -> None:
        plan_path = Path("output/VsePro/ПСД_48_2026_178/ПСД-48-2026-178 План.dxf")
        if not plan_path.exists():
            self.skipTest("Пример плана 178 недоступен в рабочей копии.")
        data, warnings = analyze_dxf(plan_path)
        self.assertEqual(data["supports"]["P23"], 4)
        self.assertEqual(data["supports"]["K21"], 1)
        self.assertTrue(any("вне основной трассы" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
