from __future__ import annotations

import unittest

from backend.core.address_parser import (
    build_plot_geocode_queries,
    build_settlement_only_queries,
    parse_plot_address,
)


class AddressParserTests(unittest.TestCase):
    def test_parse_dankov_snt(self) -> None:
        parsed = parse_plot_address('Липецкая область, г.Данков, снт "Дружба", участок № 614')
        self.assertEqual(parsed.region, "Липецкая область")
        self.assertEqual(parsed.settlement_type, "город")
        self.assertEqual(parsed.settlement_name, "Данков")
        self.assertEqual(parsed.garden_partnership, "Дружба")
        self.assertEqual(parsed.plot_number, "614")

    def test_parse_khomutets_village(self) -> None:
        parsed = parse_plot_address(
            "Липецкая область, Добровский район, с/п Больше-Хомутецкий сельсовет, "
            "с.Большой Хомутец, ул.Лужанская"
        )
        self.assertEqual(parsed.district, "Добровский район")
        self.assertEqual(parsed.municipality, "с/п Больше-Хомутецкий сельсовет")
        self.assertEqual(parsed.settlement_type, "село")
        self.assertEqual(parsed.settlement_name, "Большой Хомутец")
        self.assertEqual(parsed.street, "Лужанская")

    def test_parse_dobrinka_plot(self) -> None:
        parsed = parse_plot_address("Липецкая область, Добринский район, Добринка, ул.Новая, з.у. 9")
        self.assertEqual(parsed.district, "Добринский район")
        self.assertEqual(parsed.settlement_name, "Добринка")
        self.assertEqual(parsed.street, "Новая")
        self.assertEqual(parsed.plot_number, "9")

    def test_build_queries_for_snt(self) -> None:
        parsed = parse_plot_address('Липецкая область, г.Данков, ст "Дружба"')
        queries = build_plot_geocode_queries(parsed, "48:03:0690601:1211")
        self.assertTrue(any("СНТ Дружба" in query for query in queries))
        self.assertTrue(any("город Данков" in query for query in queries))

    def test_parse_dvurechki_house(self) -> None:
        parsed = parse_plot_address("Липецкая область, Грязинский район, Двуречки 1а")
        self.assertEqual(parsed.settlement_name, "Двуречки")
        self.assertEqual(parsed.house_number, "1а")
        queries = build_plot_geocode_queries(parsed, "48:02:0101010:123")
        self.assertTrue(any("село Двуречки" in query for query in queries))
        self.assertTrue(any("1а" in query for query in queries))

    def test_parse_khutor(self) -> None:
        parsed = parse_plot_address("Липецкая область, Добровский район, х. Пятницкий")
        self.assertEqual(parsed.settlement_type, "хутор")
        self.assertEqual(parsed.settlement_name, "Пятницкий")

    def test_build_settlement_only_queries(self) -> None:
        parsed = parse_plot_address("Липецкая область, Лебедянский район, село Мачехино")
        queries = build_settlement_only_queries(parsed)
        self.assertTrue(any("село Мачехино" in query for query in queries))
        self.assertTrue(any("Мачехино, Лебедянский район" in query for query in queries))


if __name__ == "__main__":
    unittest.main()
