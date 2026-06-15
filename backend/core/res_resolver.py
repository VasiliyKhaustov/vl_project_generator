from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .cadastral_geocoder import Coordinates
from .known_locations import get_res_coordinates, get_settlement_coordinates
from .text_normalize import normalize_tu_text


class ResResolutionError(Exception):
    pass


@dataclass(frozen=True)
class ResRule:
    res_name: str
    address: str
    coordinates: Coordinates
    settlement_coordinates: Coordinates
    matched_rule: str
    priority: int
    patterns: tuple[str, ...]


RES_RULES: tuple[ResRule, ...] = (
    ResRule(
        res_name="Добринский РЭС",
        address="Липецкая область, Добринский район, посёлок Добринка, Профсоюзная улица, 8",
        coordinates=get_res_coordinates(
            "Липецкая область, Добринский район, посёлок Добринка, Профсоюзная улица, 8"
        )
        or Coordinates(lat=52.170900, lon=40.466800),
        settlement_coordinates=get_settlement_coordinates("Добринский район / Добринка")
        or Coordinates(lat=52.170456, lon=40.467195),
        matched_rule="Добринский район / Добринка",
        priority=1,
        patterns=(
            r"\bдобринка\b",
            r"\bдобринский\s+район\b",
            r"\bдобринского\s+района\b",
        ),
    ),
    ResRule(
        res_name="Грязинский РЭС",
        address="Липецкая область, Грязи, Песковатская улица, 7",
        coordinates=get_res_coordinates("Липецкая область, Грязи, Песковатская улица, 7")
        or Coordinates(lat=52.487222, lon=39.928056),
        settlement_coordinates=get_settlement_coordinates("Грязи / Грязинский район")
        or Coordinates(lat=52.471000, lon=39.790000),
        matched_rule="Грязи / Грязинский район",
        priority=2,
        patterns=(
            r"\bгрязи\b",
            r"\bгрязинский\s+район\b",
            r"\bгрязинского\s+района\b",
            r"\bгрузинский\s+район\b",
            r"\bгрузинского\s+района\b",
        ),
    ),
    ResRule(
        res_name="Данковский РЭС",
        address="Липецкая область, Данков, Коммунальная улица, 23",
        coordinates=get_res_coordinates("Липецкая область, Данков, Коммунальная улица, 23")
        or Coordinates(lat=53.247913, lon=39.110207),
        settlement_coordinates=get_settlement_coordinates("Данков / Данковский район")
        or Coordinates(lat=53.244472, lon=39.141798),
        matched_rule="Данков / Данковский район",
        priority=3,
        patterns=(
            r"\bданков\b",
            r"\bданковский\s+район\b",
            r"\bданковского\s+района\b",
        ),
    ),
    ResRule(
        res_name="Добровский РЭС",
        address="Липецкая область, село Доброе, Советская улица, 58А",
        coordinates=get_res_coordinates("Липецкая область, село Доброе, Советская улица, 58А")
        or Coordinates(lat=52.864888, lon=39.803317),
        settlement_coordinates=get_settlement_coordinates("Доброе / Добровский район")
        or Coordinates(lat=52.786024, lon=39.854840),
        matched_rule="Доброе / Добровский район",
        priority=4,
        patterns=(
            r"\bдоброе\b",
            r"\bдобровский\s+район\b",
            r"\bдобровского\s+района\b",
        ),
    ),
    ResRule(
        res_name="Чаплыгинский РЭС",
        address="Липецкая область, село Доброе, Советская улица, 58А",
        coordinates=get_res_coordinates("Липецкая область, село Доброе, Советская улица, 58А")
        or Coordinates(lat=52.864888, lon=39.803317),
        settlement_coordinates=get_settlement_coordinates("Чаплыгин / Чаплыгинский район")
        or Coordinates(lat=53.243000, lon=39.967000),
        matched_rule="Чаплыгин / Чаплыгинский район",
        priority=4,
        patterns=(
            r"\bчаплыгин\b",
            r"\bчаплыгинский\s+район\b",
            r"\bчаплыгинского\s+района\b",
        ),
    ),
    ResRule(
        res_name="Липецкий РЭС",
        address="Липецкая область, Липецк, улица Механизаторов, 16",
        coordinates=get_res_coordinates("Липецкая область, Липецк, улица Механизаторов, 16")
        or Coordinates(lat=52.583727, lon=39.565908),
        settlement_coordinates=get_settlement_coordinates("Липецк / Липецкий район")
        or Coordinates(lat=52.610278, lon=39.594167),
        matched_rule="Липецк / Липецкий район",
        priority=5,
        patterns=(
            r"\bгород\s+липецк\b",
            r"\bг\.?\s*липецк\b",
            r"\bлипецкий\s+район\b",
        ),
    ),
)


def resolve_res_address(tu_text: str) -> dict[str, Any]:
    selected = _select_res_rule(tu_text)
    return {
        "resName": selected.res_name,
        "address": selected.address,
        "matchedRule": selected.matched_rule,
        "coordinates": {
            "lat": selected.coordinates.lat,
            "lon": selected.coordinates.lon,
        },
    }


def resolve_res_coordinates(tu_text: str) -> Coordinates:
    rule = _select_res_rule(tu_text)
    return get_res_coordinates(rule.address) or rule.coordinates


def resolve_settlement_fallback_coordinates(tu_text: str) -> Coordinates:
    rule = _select_res_rule(tu_text)
    return get_settlement_coordinates(rule.matched_rule) or rule.settlement_coordinates


def _select_res_rule(tu_text: str) -> ResRule:
    normalized = normalize_tu_text(tu_text)
    matched_rules: list[ResRule] = []

    for rule in RES_RULES:
        if any(re.search(pattern, normalized) for pattern in rule.patterns):
            matched_rules.append(rule)

    if not matched_rules:
        raise ResResolutionError("Не удалось определить РЭС")

    return min(matched_rules, key=lambda rule: rule.priority)
