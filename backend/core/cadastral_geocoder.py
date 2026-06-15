from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Protocol

from .cadastral_http import (
    PKK_HEADERS,
    coordinates_from_feature,
    normalize_cadastral_number,
    parse_pkk_features,
    request_json,
    web_mercator_to_wgs84,
)


@dataclass(frozen=True)
class Coordinates:
    lat: float
    lon: float


class CadastralProvider(Protocol):
    name: str

    def get_coordinates_by_cadastral_number(self, cadastral_number: str) -> Coordinates | None:
        ...


class CadastralGeocoderError(Exception):
    pass


class CadastralGeocoderService:
    def __init__(self, providers: list[CadastralProvider] | None = None) -> None:
        self._providers = providers or _default_cadastral_providers()

    def get_coordinates_by_cadastral_number(self, cadastral_number: str) -> Coordinates:
        normalized = normalize_cadastral_number(cadastral_number)
        errors: list[str] = []
        for provider in self._providers:
            try:
                coordinates = provider.get_coordinates_by_cadastral_number(normalized)
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                continue
            if coordinates is not None:
                return coordinates
            errors.append(f"{provider.name}: координаты не найдены")
        details = "; ".join(errors) if errors else "провайдеры не настроены"
        raise CadastralGeocoderError(
            f"Не удалось определить координаты кадастрового участка ({details})."
        )


class PkkPublicMapProvider:
    """Публичная кадастровая карта Росреестра (PKK / PKK5)."""

    name = "pkk_public_map"

    def __init__(self) -> None:
        self._hosts = ("https://pkk5.rosreestr.ru", "https://pkk.rosreestr.ru")
        self._layers = (5,)

    def get_coordinates_by_cadastral_number(self, cadastral_number: str) -> Coordinates | None:
        for host in self._hosts:
            for layer in self._layers:
                coordinates = self._fetch_from_layer(host, layer, cadastral_number)
                if coordinates is not None:
                    return coordinates
        return None

    def _fetch_from_layer(self, host: str, layer: int, cadastral_number: str) -> Coordinates | None:
        for attempt in range(2):
            try:
                payload = request_json(
                    f"{host}/api/features/{layer}",
                    params={"text": cadastral_number, "limit": 1},
                    headers={
                        **PKK_HEADERS,
                        "Referer": f"{host}/",
                        "Origin": host,
                    },
                    prefer_curl=True,
                )
            except Exception:
                if attempt == 0:
                    continue
                return None
            for feature in parse_pkk_features(payload):
                point = coordinates_from_feature(feature)
                if point is None:
                    continue
                lat, lon = web_mercator_to_wgs84(point[0], point[1])
                return Coordinates(lat=lat, lon=lon)
            return None
        return None


class RosreestrPkkProvider(PkkPublicMapProvider):
    name = "rosreestr_pkk"


class NspdProvider:
    name = "nspd"

    def get_coordinates_by_cadastral_number(self, cadastral_number: str) -> Coordinates | None:
        endpoints = (
            ("https://nspd.gov.ru/api/geoportal/v1/search", {"query": cadastral_number}),
            ("https://nspd.gov.ru/api/aigegrp/v1/search", {"text": cadastral_number}),
        )
        for url, params in endpoints:
            try:
                payload = request_json(
                    url,
                    params=params,
                    headers={
                        "User-Agent": PKK_HEADERS["User-Agent"],
                        "Accept": "application/json",
                        "Referer": "https://nspd.gov.ru/",
                    },
                )
            except Exception:
                continue
            coordinates = self._coordinates_from_payload(payload)
            if coordinates is not None:
                return coordinates
        return None

    def _coordinates_from_payload(self, payload: Any) -> Coordinates | None:
        items: list[Any]
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("data") or payload.get("results") or payload.get("items") or []
        else:
            return None

        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("lat") is not None and item.get("lon") is not None:
                return Coordinates(lat=float(item["lat"]), lon=float(item["lon"]))
            geometry = item.get("geometry") or {}
            if isinstance(geometry, dict) and geometry.get("type") == "Point":
                lon, lat = geometry.get("coordinates", [None, None])
                if lat is not None and lon is not None:
                    return Coordinates(lat=float(lat), lon=float(lon))
        return None


def _default_cadastral_providers() -> list[CadastralProvider]:
    return [PkkPublicMapProvider(), NspdProvider()]
