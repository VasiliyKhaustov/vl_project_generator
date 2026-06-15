from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Protocol

from .cadastral_geocoder import Coordinates


class GeocodingProvider(Protocol):
    name: str

    def geocode_address(self, address: str) -> Coordinates | None:
        ...


class RoutingProvider(Protocol):
    name: str

    def get_driving_distance_meters(
        self,
        source: Coordinates,
        destination: Coordinates,
    ) -> int | None:
        ...


class RouteDistanceError(Exception):
    pass


@dataclass(frozen=True)
class RouteDistanceResult:
    distance_km: int
    distance_meters: int
    provider: str
    route_type: str
    destination_coordinates: Coordinates
    straight_line_km: float | None = None


class AddressGeocoderService:
    def __init__(self, providers: list[GeocodingProvider] | None = None) -> None:
        self._providers = providers or _default_geocoding_providers()

    def geocode_address(self, address: str) -> Coordinates:
        errors: list[str] = []
        for provider in self._providers:
            try:
                coordinates = provider.geocode_address(address)
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                continue
            if coordinates is not None:
                return coordinates
            errors.append(f"{provider.name}: адрес не найден")
        details = "; ".join(errors) if errors else "провайдеры не настроены"
        raise RouteDistanceError(f"Не удалось геокодировать адрес РЭС ({details}).")


class RouteDistanceService:
    def __init__(
        self,
        geocoder: AddressGeocoderService | None = None,
        routing_providers: list[RoutingProvider] | None = None,
    ) -> None:
        self._geocoder = geocoder or AddressGeocoderService()
        self._routing_providers = routing_providers or _default_routing_providers()

    def get_driving_distance_km(
        self,
        from_coordinates: Coordinates,
        to_address: str,
    ) -> RouteDistanceResult:
        destination = self._geocoder.geocode_address(to_address)
        return self.get_driving_distance_km_between(from_coordinates, destination)

    def get_driving_distance_km_between(
        self,
        from_coordinates: Coordinates,
        to_coordinates: Coordinates,
    ) -> RouteDistanceResult:
        straight_km = straight_line_km(from_coordinates, to_coordinates)
        if straight_km < 0.5:
            return RouteDistanceResult(
                distance_km=1,
                distance_meters=1000,
                provider="nearby_minimum",
                route_type="driving",
                destination_coordinates=to_coordinates,
                straight_line_km=straight_km,
            )

        errors: list[str] = []
        for provider in self._routing_providers:
            try:
                meters = provider.get_driving_distance_meters(from_coordinates, to_coordinates)
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                continue
            if meters is None or meters <= 0:
                errors.append(f"{provider.name}: пустой маршрут")
                continue
            return RouteDistanceResult(
                distance_km=_ceil_km(meters),
                distance_meters=meters,
                provider=provider.name,
                route_type="driving",
                destination_coordinates=to_coordinates,
                straight_line_km=straight_km,
            )

        if straight_km >= 0.5:
            estimated_meters = int(straight_km * 1000 * 1.35)
            return RouteDistanceResult(
                distance_km=_ceil_km(estimated_meters),
                distance_meters=estimated_meters,
                provider="straight_line_estimate",
                route_type="driving",
                destination_coordinates=to_coordinates,
                straight_line_km=straight_km,
            )

        details = "; ".join(errors) if errors else "routing API недоступен"
        raise RouteDistanceError(f"Не удалось построить автомобильный маршрут ({details}).")


class YandexGeocoderProvider:
    name = "yandex_geocoder"

    def geocode_address(self, address: str) -> Coordinates | None:
        api_key = os.environ.get("YANDEX_MAPS_API_KEY", "").strip()
        if not api_key:
            return None
        import httpx

        try:
            response = httpx.get(
                "https://geocode-maps.yandex.ru/1.x/",
                params={"apikey": api_key, "geocode": address, "format": "json", "results": 1},
                timeout=20.0,
            )
            response.raise_for_status()
        except Exception:
            return None
        members = (
            response.json()
            .get("response", {})
            .get("GeoObjectCollection", {})
            .get("featureMember", [])
        )
        if not members:
            return None
        pos = members[0]["GeoObject"]["Point"]["pos"]
        lon, lat = map(float, pos.split())
        return Coordinates(lat=lat, lon=lon)


class NominatimGeocoderProvider:
    name = "nominatim"

    def geocode_address(self, address: str) -> Coordinates | None:
        import httpx

        response = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": address,
                "format": "json",
                "limit": 1,
                "countrycodes": "ru",
                "viewbox": "37.5,53.6,41.0,51.8",
                "bounded": 0,
            },
            timeout=20.0,
            headers={"User-Agent": "vl-project-generator/1.0"},
        )
        response.raise_for_status()
        items = response.json()
        if not items:
            return None
        return Coordinates(lat=float(items[0]["lat"]), lon=float(items[0]["lon"]))


class PhotonGeocoderProvider:
    name = "photon"

    def geocode_address(self, address: str) -> Coordinates | None:
        import httpx

        try:
            response = httpx.get(
                "https://photon.komoot.io/api/",
                params={"q": address, "limit": 1, "lang": "ru"},
                timeout=20.0,
            )
            response.raise_for_status()
            features = response.json().get("features") or []
            if not features:
                return None
            lon, lat = features[0]["geometry"]["coordinates"][:2]
            return Coordinates(lat=float(lat), lon=float(lon))
        except Exception:
            return None


class YandexRoutingProvider:
    name = "yandex"

    def get_driving_distance_meters(
        self,
        source: Coordinates,
        destination: Coordinates,
    ) -> int | None:
        api_key = os.environ.get("YANDEX_MAPS_API_KEY", "").strip()
        if not api_key:
            return None
        import httpx

        waypoints = f"{source.lat},{source.lon}|{destination.lat},{destination.lon}"
        response = httpx.get(
            "https://api.routing.yandex.net/v2/route",
            params={"apikey": api_key, "waypoints": waypoints, "mode": "driving"},
            timeout=30.0,
        )
        response.raise_for_status()
        route = response.json().get("route", {})
        legs = route.get("legs") or []
        if not legs:
            return None
        return int(sum(leg.get("length", 0) for leg in legs))


class TwoGisRoutingProvider:
    name = "twogis"

    def get_driving_distance_meters(
        self,
        source: Coordinates,
        destination: Coordinates,
    ) -> int | None:
        api_key = os.environ.get("TWOGIS_API_KEY", "").strip()
        if not api_key:
            return None
        import httpx

        response = httpx.post(
            "https://routing.api.2gis.com/routing/7.0.0/global",
            params={"key": api_key},
            json={
                "points": [
                    {"type": "stop", "lon": source.lon, "lat": source.lat},
                    {"type": "stop", "lon": destination.lon, "lat": destination.lat},
                ],
                "transport": "driving",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if not result:
            return None
        total = result[0].get("total_distance")
        return int(total) if total else None


class GraphHopperRoutingProvider:
    name = "graphhopper"

    def get_driving_distance_meters(
        self,
        source: Coordinates,
        destination: Coordinates,
    ) -> int | None:
        api_key = os.environ.get("GRAPHHOPPER_API_KEY", "").strip()
        if not api_key:
            return None
        import httpx

        response = httpx.get(
            "https://graphhopper.com/api/1/route",
            params={
                "key": api_key,
                "point": [f"{source.lat},{source.lon}", f"{destination.lat},{destination.lon}"],
                "profile": "car",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        paths = response.json().get("paths") or []
        if not paths:
            return None
        distance = paths[0].get("distance")
        return int(distance) if distance else None


class OpenRouteServiceProvider:
    name = "openrouteservice"

    def get_driving_distance_meters(
        self,
        source: Coordinates,
        destination: Coordinates,
    ) -> int | None:
        api_key = os.environ.get("OPENROUTESERVICE_API_KEY", "").strip()
        if not api_key:
            return None
        import httpx

        response = httpx.post(
            "https://api.openrouteservice.org/v2/directions/driving-car",
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            json={
                "coordinates": [
                    [source.lon, source.lat],
                    [destination.lon, destination.lat],
                ]
            },
            timeout=30.0,
        )
        response.raise_for_status()
        routes = response.json().get("routes") or []
        if not routes:
            return None
        summary = routes[0].get("summary") or {}
        distance = summary.get("distance")
        return int(distance) if distance else None


class OsrmRoutingProvider:
    name = "osrm"

    def get_driving_distance_meters(
        self,
        source: Coordinates,
        destination: Coordinates,
    ) -> int | None:
        import httpx

        base_url = os.environ.get("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
        path = (
            f"{base_url}/route/v1/driving/"
            f"{source.lon},{source.lat};{destination.lon},{destination.lat}"
        )
        response = httpx.get(path, params={"overview": "false"}, timeout=30.0)
        response.raise_for_status()
        routes = response.json().get("routes") or []
        if not routes:
            return None
        distance = routes[0].get("distance")
        return int(distance) if distance else None


def _ceil_km(distance_meters: int) -> int:
    return int(math.ceil(distance_meters / 1000.0))


def straight_line_km(source: Coordinates, destination: Coordinates) -> float:
    radius = 6371000.0
    lat1 = math.radians(source.lat)
    lat2 = math.radians(destination.lat)
    delta_lat = math.radians(destination.lat - source.lat)
    delta_lon = math.radians(destination.lon - source.lon)
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    meters = 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(meters / 1000.0, 3)


def _default_geocoding_providers() -> list[GeocodingProvider]:
    return [YandexGeocoderProvider(), NominatimGeocoderProvider()]


def _default_routing_providers() -> list[RoutingProvider]:
    return [
        YandexRoutingProvider(),
        TwoGisRoutingProvider(),
        GraphHopperRoutingProvider(),
        OpenRouteServiceProvider(),
        OsrmRoutingProvider(),
    ]
