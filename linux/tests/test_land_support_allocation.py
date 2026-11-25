from __future__ import annotations

import unittest

import ezdxf
from ezdxf.lldxf.types import DXFTag

from backend.cad.oda_dwg_adapter import (
    _fill_land_support_block,
    _fill_land_support_native_cells,
    _land_support_allocation,
    _plain_table_cell_text,
)


class _Tags:
    def __init__(self, tags: list[DXFTag]) -> None:
        self.subclasses = [(), (), (), tags]


class _Table:
    def __init__(self, tags: list[DXFTag]) -> None:
        self.xtags = _Tags(tags)


def _cell(tags: list[DXFTag], text: str) -> None:
    tags.append(DXFTag(1, text))
    tags.append(DXFTag(302, text))


class LandSupportAllocationTests(unittest.TestCase):
    def test_anchor_count_includes_disconnector(self) -> None:
        allocation = _land_support_allocation(
            {
                "{{P20}}": "4",
                "{{A20}}": "1",
                "{{ARLK}}": "1",
                "{{UA}}": "2",
                "{{PS}}": "0.204",
                "{{AS}}": "0.204",
                "{{US}}": "0.306",
                "{{SU}}": "0.714",
            }
        )
        self.assertEqual(allocation["intermediate_count"], "4")
        self.assertEqual(allocation["anchor_count"], "2")
        self.assertEqual(allocation["angle_count"], "2")
        self.assertEqual(allocation["intermediate_area"], "0.204")
        self.assertEqual(allocation["anchor_area"], "0.204")
        self.assertEqual(allocation["angle_area"], "0.306")
        self.assertEqual(allocation["total_area"], "0.714")

    def test_zero_supports_stay_zero(self) -> None:
        allocation = _land_support_allocation(
            {
                "{{P20}}": "0",
                "{{A20}}": "1",
                "{{ARLK}}": "1",
                "{{UA}}": "0",
                "{{PS}}": "0",
                "{{AS}}": "0.204",
                "{{US}}": "0",
                "{{SU}}": "0.204",
            }
        )
        self.assertEqual(allocation["intermediate_count"], "0")
        self.assertEqual(allocation["anchor_count"], "2")
        self.assertEqual(allocation["angle_count"], "0")
        self.assertEqual(allocation["anchor_area"], "0.204")

    def test_block_and_native_cells_get_type_counts(self) -> None:
        document = ezdxf.new()
        block = document.blocks.new("LAND")

        def add(x: float, y: float, text: str) -> None:
            entity = block.add_mtext(text)
            entity.set_location((x, y))

        add(40, -8, "0")
        add(80, -8, "0,051")
        add(170, -8, "0")
        add(50, -16, "1")
        add(100, -16, "0,102")
        add(170, -16, "0.204")
        add(70, -24, "0")
        add(110, -24, "0,153")
        add(170, -24, "0")
        add(80, -32, "Итого, м²")
        add(170, -32, "0.204")

        tags: list[DXFTag] = []
        for text in (
            "0",
            "0,051",
            "0",
            "1",
            "0,102",
            "0.204",
            r"{\T0.95;0}",
            "0,153",
            "0",
            r"{\H1.1667x;\C256;Итого, м²}",
            "0.204",
        ):
            _cell(tags, text)
        table = _Table(tags)
        allocation = _land_support_allocation(
            {
                "{{P20}}": "3",
                "{{A20}}": "1",
                "{{ARLK}}": "2",
                "{{UA}}": "1",
                "{{PS}}": "0.153",
                "{{AS}}": "0.306",
                "{{US}}": "0.153",
                "{{SU}}": "0.612",
            }
        )
        self.assertGreater(_fill_land_support_block(block, allocation), 0)
        self.assertGreater(_fill_land_support_native_cells(table, allocation), 0)

        by_point = {
            (round(entity.dxf.insert.x), round(entity.dxf.insert.y)): _plain_table_cell_text(entity.text)
            for entity in block
            if entity.dxftype() == "MTEXT"
        }
        self.assertEqual(by_point[(40, -8)], "3")
        self.assertEqual(by_point[(170, -8)], "0.153")
        self.assertEqual(by_point[(50, -16)], "3")
        self.assertEqual(by_point[(170, -16)], "0.306")
        self.assertEqual(by_point[(70, -24)], "1")
        self.assertEqual(by_point[(170, -24)], "0.153")
        self.assertEqual(by_point[(170, -32)], "0.612")
        self.assertEqual(by_point[(80, -8)], "0,051")

        native = [str(tag.value) for tag in tags if tag.code == 302]
        self.assertEqual(
            native,
            [
                "3",
                "0,051",
                "0.153",
                "3",
                "0,102",
                "0.306",
                r"{\T0.95;1}",
                "0,153",
                "0.153",
                r"{\H1.1667x;\C256;Итого, м²}",
                "0.612",
            ],
        )


if __name__ == "__main__":
    unittest.main()
