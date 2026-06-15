from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from typing import Any
from urllib.parse import urlencode

import httpx


DEFAULT_TIMEOUT = 8.0
PKK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://pkk.rosreestr.ru/",
    "Origin": "https://pkk.rosreestr.ru",
}


def request_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    prefer_curl: bool = False,
) -> Any:
    errors: list[str] = []
    attempts: list[str] = ["curl", "httpx"] if prefer_curl and shutil.which("curl") else ["httpx", "curl"]

    for method in attempts:
        if method == "curl" and not shutil.which("curl"):
            continue
        try:
            if method == "curl":
                return _request_json_curl(url, params=params, headers=headers, timeout=timeout)
            return _request_json_httpx(url, params=params, headers=headers, timeout=timeout)
        except Exception as exc:
            errors.append(f"{method}: {exc}")

    raise RuntimeError("; ".join(errors))


def _request_json_httpx(
    url: str,
    *,
    params: dict[str, Any] | None,
    headers: dict[str, str] | None,
    timeout: float,
) -> Any:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=headers or PKK_HEADERS,
    ) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def _request_json_curl(
    url: str,
    *,
    params: dict[str, Any] | None,
    headers: dict[str, str] | None,
    timeout: float,
) -> Any:
    if params:
        query = urlencode(params)
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{query}"

    command = [
        "curl",
        "-sS",
        "--max-time",
        str(int(timeout)),
        "--tlsv1.2",
        "--compressed",
        url,
    ]
    for key, value in (headers or PKK_HEADERS).items():
        command.extend(["-H", f"{key}: {value}"])

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"curl exit code {completed.returncode}")
    return json.loads(completed.stdout)


def parse_pkk_features(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        features = payload.get("feature") or payload.get("features") or []
        if isinstance(features, list):
            return [feature for feature in features if isinstance(feature, dict)]
    return []


def coordinates_from_feature(feature: dict[str, Any]) -> tuple[float, float] | None:
    center = feature.get("center") or {}
    if isinstance(center, dict) and center.get("x") is not None and center.get("y") is not None:
        return float(center["x"]), float(center["y"])

    geometry = feature.get("geometry") or {}
    if isinstance(geometry, dict):
        point = _coordinates_from_geometry(geometry)
        if point is not None:
            return point

    attrs = feature.get("attrs") or {}
    if isinstance(attrs, dict):
        for key_x, key_y in (("xc", "yc"), ("x", "y"), ("lon", "lat")):
            if attrs.get(key_x) is not None and attrs.get(key_y) is not None:
                return float(attrs[key_x]), float(attrs[key_y])
    return None


def _coordinates_from_geometry(geometry: dict[str, Any]) -> tuple[float, float] | None:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return None

    if geometry_type == "Point":
        x, y = coordinates[:2]
        return float(x), float(y)

    points = _flatten_coordinates(coordinates)
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0


def _flatten_coordinates(data: Any) -> list[tuple[float, float]]:
    if isinstance(data, (list, tuple)):
        if len(data) >= 2 and isinstance(data[0], (int, float)) and isinstance(data[1], (int, float)):
            return [(float(data[0]), float(data[1]))]
        points: list[tuple[float, float]] = []
        for item in data:
            points.extend(_flatten_coordinates(item))
        return points
    return []


def normalize_cadastral_number(cadastral_number: str) -> str:
    return re.sub(r"\s+", "", cadastral_number.strip())


def web_mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    if abs(x) <= 180 and abs(y) <= 90:
        return y, x
    lon = x * 180.0 / 20037508.34
    lat = y * 180.0 / 20037508.34
    lat = 180.0 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
    return lat, lon
