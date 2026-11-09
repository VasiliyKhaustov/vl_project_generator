from __future__ import annotations

import unittest
from pathlib import Path

from backend.core.dxf_reader import (
    _normalize_support_label,
    _resolve_support_type,
    analyze_dxf,
)


class DxfSupportRecognitionTests(unittest.TestCase):
    def test_normalizes_short_support_labels(self) -> None:
        self.assertEqual(_normalize_support_label("П"), "P23")
        self.assertEqual(_normalize_support_label("К"), "K21")
        self.assertEqual(_normalize_support_label("А"), "A23")
        self.assertEqual(_normalize_support_label("УА"), "YA23")
        self.assertEqual(_normalize_support_label("УП"), "P23")

    def test_resolves_support_type_by_label_catalog_and_block(self) -> None:
        self.assertEqual(_resolve_support_type("Пл_Опора", "П", ""), "P23")
        self.assertEqual(_resolve_support_type("Пл_Опора", "ПП23", "", "PP23"), "PP23")
        self.assertEqual(_resolve_support_type("Пл_ОпораП23", "П23", "", "PP23"), "PP23")
        self.assertEqual(_resolve_support_type("Пл_ОпораПП23", "", ""), "PP23")
        self.assertEqual(_resolve_support_type("Пл_Опора", "", "21.0112-04"), "K21")
        self.assertEqual(_resolve_support_type("Пл_ОпораНВ_А23", "", ""), "A23")
        self.assertEqual(_resolve_support_type("Пл_ОпораУА23", "УА23", ""), "YA23")
        self.assertEqual(
            _resolve_support_type("stolb NN", "", "", "04.1_ЛЭП_наземная_опоры", stolb_nn_total=1),
            "K21",
        )
        self.assertIsNone(
            _resolve_support_type("stolb NN", "", "", "04.1_ЛЭП_наземная_опоры", stolb_nn_total=10),
        )

    def test_does_not_count_a20_rlk_as_a23(self) -> None:
        # Динамический блок А20 РЛК раскрывается как Пл_ОпораНВ_А23.
        self.assertIsNone(
            _resolve_support_type(
                "Пл_ОпораНВ_А23",
                "А20-3Н+КР2",
                "",
                "Пл_А20-3Н_РЛК",
            )
        )
        self.assertIsNone(
            _resolve_support_type("Пл_ОпораНВ_А23", "А20-3Н", "", "Пл_А20-3Н")
        )
        self.assertIsNone(
            _resolve_support_type("Пл_Опора", "П20-3Н", "", "Пл_П20-3Н")
        )

    def test_plan_proverki_counts_p23_k21_without_a23(self) -> None:
        plan_path = Path(
            "output/sessions/7b3d78f67cf24d2fb0011488e8b97dae/uploads/detect_plan.dxf"
        )
        if not plan_path.exists():
            plan_path = Path("output/VsePro/ПСД_48_2026_002/план для проверки.dxf")
        if not plan_path.exists():
            self.skipTest("план для проверки.dxf недоступен")

        data, _warnings = analyze_dxf(plan_path)
        self.assertEqual(data["supports"]["P23"], 1)
        self.assertEqual(data["supports"]["K21"], 1)
        self.assertEqual(data["supports"]["A23"], 0)
        self.assertEqual(data["supports"]["YA23"], 0)

    def test_project_190_counts_p23_and_k21(self) -> None:
        plan_path = Path("output/VsePro/ПСД_48_2026_190/ПСД-48-2026-190 План.dxf")
        if not plan_path.exists():
            self.skipTest("project 190 plan is unavailable")

        data, warnings = analyze_dxf(plan_path)
        self.assertEqual(data["supports"]["P23"], 4)
        self.assertEqual(data["supports"]["K21"], 1)
        self.assertEqual(data["supports"]["A23"], 0)
        self.assertEqual(data["supports"]["YA23"], 0)

    def test_project_01_counts_local_design_supports(self) -> None:
        plan_path = Path("examples/projects/project_01/plan.dxf")
        if not plan_path.exists():
            self.skipTest("project_01 plan is unavailable")

        data, warnings = analyze_dxf(plan_path)
        self.assertEqual(data["supports"]["P23"], 1)
        self.assertEqual(data["supports"]["K21"], 1)
        self.assertEqual(data["supports"]["A23"], 0)
        self.assertEqual(sum(data["supports"].values()), 2)
        self.assertFalse(any("вне основной трассы" in warning for warning in warnings))

    def test_project_02_keeps_route_filtered_georef_supports(self) -> None:
        plan_path = Path("examples/projects/project_02/plan.dxf")
        if not plan_path.exists():
            self.skipTest("project_02 plan is unavailable")

        data, warnings = analyze_dxf(plan_path)
        self.assertEqual(data["supports"]["P23"], 5)
        self.assertEqual(data["supports"]["A23"], 5)
        self.assertEqual(sum(data["supports"].values()), 10)
        self.assertTrue(
            any("существующих опор" in warning or "вне основной трассы" in warning for warning in warnings)
        )

    def test_insert_at_origin_uses_block_geometry(self) -> None:
        import ezdxf

        from backend.core.dxf_reader import _insert_distance_to_polyline, _insert_plan_point

        document = ezdxf.new()
        block = document.blocks.new("Пл_ОпораП23")
        block.add_lwpolyline([(1000, 0), (1005, 0), (1005, 5), (1000, 5)], close=True)
        insert = document.modelspace().add_blockref("Пл_ОпораП23", (0, 0))
        x, y = _insert_plan_point(insert)
        self.assertGreater(x, 900)
        route = [(1000.0, 0.0, 0.0), (1100.0, 0.0, 0.0)]
        self.assertLess(_insert_distance_to_polyline(insert, route), 1.0)


if __name__ == "__main__":
    unittest.main()
