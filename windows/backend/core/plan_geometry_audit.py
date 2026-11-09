"""Геометрический аудит плана для AI Engineer (только чтение, без изменения проекта)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import ezdxf

from backend.core.dxf_reader import (
    _attribute_value,
    _collect_support_candidates,
    _effective_block_name,
    _find_main_polyline,
    _ground_block_signatures,
    _insert_distance_to_polyline,
    _insert_plan_point,
    _is_anonymous_grounding_insert,
    _is_direct_grounding_insert,
    _lwpolyline_points,
    _polyline_points_for_entity,
)
from backend.core.plan_reader_10kv import (
    LINE_04_BRANCH_LAYERS,
    LINE_04_BRANCH_MAX_LENGTH_M,
    _find_line_length_04kv,
    _layer_matches_04,
    _open_polyline_length,
)


GROUNDING_SPACING_04KV_M = 100.0
# «Касается» полилинии: insert практически на трассе (не «где-то рядом»).
TOUCH_TOLERANCE_M = 1.0
MAX_SUPPORT_GAP_04_M = 42.0
MAX_SUPPORT_GAP_10_M = 70.0
MAX_GROUNDING_GAP_M = 100.0
SUPPORTS_04 = frozenset({"P23", "PP23", "A23", "YA23", "K21"})
SUPPORTS_10 = frozenset({"P20", "A20", "UA", "UP", "ARLK"})
# П23 / А23 / К21 — только на прямолинейном участке (угол ≈ 0°).
# УА23* — на повороте до 90°. Небольшой допуск из‑за оцифровки CAD.
STRAIGHT_SUPPORTS_04 = frozenset({"P23", "PP23", "A23", "K21"})
STRAIGHT_ANGLE_MAX_DEG = 8.0
YA23_ANGLE_MAX_DEG = 90.0
VERTEX_SNAP_M = 2.0
MIN_SEGMENT_M = 0.05


def expected_groundings_04kv(line_length_m: float) -> int:
    """Норма: заземление примерно каждые 100 м на трассе 0,4 кВ."""
    length = float(line_length_m or 0)
    if length <= 0:
        return 0
    return max(1, int(math.ceil(length / GROUNDING_SPACING_04KV_M)))


def audit_plan_geometry(plan_path: Path | None) -> dict[str, Any]:
    """Читает DXF и возвращает факты для рекомендаций AI Engineer."""
    empty = {
        "available": False,
        "line_length_04_m": 0.0,
        "line_length_10_m": 0.0,
        "grounding_count": 0,
        "expected_groundings_04": 0,
        "supports_off_route": [],
        "groundings_off_route": [],
        "supports_on_route": 0,
        "groundings_on_route": 0,
        "support_gaps_04": [],
        "support_gaps_10": [],
        "grounding_gaps": [],
        "grounding_positions": [],
        "support_positions_04": [],
        "duplicate_supports": [],
        "wrong_angle_supports": [],
        "number_sequence_issues": [],
        "supports_04_count": 0,
        "supports_10_count": 0,
        "route_available": False,
        "touch_tolerance_m": TOUCH_TOLERANCE_M,
        "max_support_gap_04_m": MAX_SUPPORT_GAP_04_M,
        "max_support_gap_10_m": MAX_SUPPORT_GAP_10_M,
        "max_grounding_gap_m": MAX_GROUNDING_GAP_M,
        "straight_angle_max_deg": STRAIGHT_ANGLE_MAX_DEG,
        "ya23_angle_max_deg": YA23_ANGLE_MAX_DEG,
    }
    if plan_path is None:
        return empty
    path = Path(plan_path)
    if not path.exists() or path.suffix.lower() != ".dxf":
        return empty

    document = ezdxf.readfile(path)
    modelspace = document.modelspace()
    ground_sigs = _ground_block_signatures(document)

    support_candidates = _collect_support_candidates(modelspace, document)
    support_points = [candidate["point"] for candidate in support_candidates]
    main_polyline = _find_main_polyline(modelspace, support_points)
    main_route = _polyline_points_for_entity(modelspace, main_polyline) if main_polyline else []
    main_length = float(main_polyline["length"]) if main_polyline else 0.0

    route_04 = _best_route_points(modelspace, kind="04")
    route_10 = _best_route_points(modelspace, kind="10")
    length_04 = float(_find_line_length_04kv(modelspace) or 0)
    if length_04 <= 0:
        length_04 = main_length
    if not route_04:
        route_04 = main_route

    length_10 = 0.0
    if route_10:
        length_10 = _points_length_xy(route_10)

    # 0,4 кВ: только dedicated трасса 0,4 (слой 04 / короткая ветвь).
    # Длинную «основную» полилинию расчётчика (часто слой 0 на 10 кВ) не подмешиваем —
    # иначе опора рядом с чужой линией ложно считается «на трассе».
    routes_04: list[list[tuple[float, float, float]]] = []
    if route_04:
        routes_04.append(route_04)
    elif main_route:
        routes_04.append(main_route)

    collected_supports: list[dict[str, Any]] = []
    for candidate in support_candidates:
        if candidate.get("is_existing") or not candidate.get("support_type"):
            continue
        support_type = str(candidate["support_type"])
        insert = candidate["insert"]
        point = _insert_plan_point(insert)
        number = _attribute_value(insert, "SL_NUM").strip() or _guess_support_number(candidate)
        voltage = "10" if support_type in SUPPORTS_10 else "04"
        routes = [route_10] if voltage == "10" else routes_04
        if not routes:
            continue
        station, _ = _station_and_distance(point, routes[0])
        distance = _insert_distance_to_polyline(insert, routes[0])
        collected_supports.append(
            {
                "support_type": support_type,
                "number": number,
                "label": str(candidate.get("label") or "").strip(),
                "distance_m": round(distance, 2),
                "display_name": _support_display_name(support_type, number),
                "voltage": voltage,
                "station_m": round(station, 2),
                "point": point,
                "on_route": distance <= TOUCH_TOLERANCE_M,
            }
        )

    for item in _collect_10kv_support_points(modelspace, document):
        if not route_10:
            break
        if _near_existing_point(item["point"], [row["point"] for row in collected_supports]):
            continue
        station, _ = _station_and_distance(item["point"], route_10)
        insert = item.get("insert")
        distance = (
            _insert_distance_to_polyline(insert, route_10)
            if insert is not None
            else _station_and_distance(item["point"], route_10)[1]
        )
        collected_supports.append(
            {
                "support_type": item["support_type"],
                "number": item.get("number") or "",
                "label": item.get("label") or "",
                "distance_m": round(distance, 2),
                "display_name": item["display_name"],
                "voltage": "10",
                "station_m": round(station, 2),
                "point": item["point"],
                "on_route": distance <= TOUCH_TOLERANCE_M,
            }
        )

    supports_off_route = [
        {
            "support_type": row["support_type"],
            "number": row["number"],
            "label": row["label"],
            "distance_m": row["distance_m"],
            "display_name": row["display_name"],
            "voltage": row["voltage"],
        }
        for row in collected_supports
        if not row["on_route"]
    ]
    supports_on_route = sum(1 for row in collected_supports if row["on_route"])

    groundings = _collect_grounding_points(modelspace, document, ground_sigs)
    collected_grounds: list[dict[str, Any]] = []
    groundings_off_route: list[dict[str, Any]] = []
    groundings_on_route = 0
    route_for_ground = routes_04[0] if routes_04 else []
    for index, item in enumerate(groundings, start=1):
        if route_for_ground:
            station, _ = _station_and_distance(item["point"], route_for_ground)
            insert = item.get("insert")
            distance = (
                _insert_distance_to_polyline(insert, route_for_ground)
                if insert is not None
                else _station_and_distance(item["point"], route_for_ground)[1]
            )
        else:
            station, distance = 0.0, 9999.0
        touched = bool(route_for_ground) and distance <= TOUCH_TOLERANCE_M
        label = item.get("label") or f"Заземление #{index}"
        collected_grounds.append(
            {
                "index": index,
                "distance_m": round(distance, 2),
                "label": label,
                "station_m": round(station, 2),
                "on_route": touched,
            }
        )
        if touched:
            groundings_on_route += 1
            continue
        if route_for_ground:
            groundings_off_route.append(
                {
                    "index": index,
                    "distance_m": round(distance, 2),
                    "label": label,
                }
            )

    # Количество заземлений для нормы — как у расчётчика: все найденные блоки.
    # Если insert-ов меньше, чем ESMT (редкий случай), берём max.
    from backend.core.dxf_reader import _count_esmt_ground_elements

    esmt_count = _count_esmt_ground_elements(path)
    grounding_count = max(len(groundings), esmt_count)
    expected = expected_groundings_04kv(length_04)
    supports_04 = [row for row in collected_supports if row["voltage"] == "04"]
    supports_10 = [row for row in collected_supports if row["voltage"] == "10"]

    return {
        "available": True,
        "line_length_04_m": round(float(length_04 or 0), 1),
        "line_length_10_m": round(float(length_10 or 0), 1),
        "grounding_count": grounding_count,
        "expected_groundings_04": expected,
        "supports_off_route": _dedupe_off_items(supports_off_route),
        "groundings_off_route": groundings_off_route,
        "supports_on_route": supports_on_route,
        "groundings_on_route": groundings_on_route,
        "support_gaps_04": _consecutive_gaps(
            [row for row in supports_04 if row.get("on_route")],
            name_key="display_name",
            limit_m=MAX_SUPPORT_GAP_04_M,
        ),
        "support_gaps_10": _consecutive_gaps(
            [row for row in supports_10 if row.get("on_route")],
            name_key="display_name",
            limit_m=MAX_SUPPORT_GAP_10_M,
        ),
        "grounding_gaps": _gaps_along_route(
            [row for row in collected_grounds if row.get("on_route")],
            name_key="label",
            limit_m=MAX_GROUNDING_GAP_M,
            route_length_m=float(length_04 or 0),
        ),
        "grounding_positions": [
            {
                "label": row.get("label"),
                "station_m": row.get("station_m"),
                "distance_m": row.get("distance_m"),
                "on_route": bool(row.get("on_route")),
            }
            for row in collected_grounds[:20]
        ],
        "support_positions_04": [
            {
                "display_name": row.get("display_name"),
                "number": row.get("number"),
                "station_m": row.get("station_m"),
                "distance_m": row.get("distance_m"),
                "on_route": bool(row.get("on_route")),
            }
            for row in supports_04[:30]
        ],
        "duplicate_supports": _duplicate_support_numbers(collected_supports),
        "number_sequence_issues": [
            issue
            for issue in (
                _support_number_sequence(supports_04, voltage="04"),
                _support_number_sequence(supports_10, voltage="10"),
            )
            if issue
        ],
        "wrong_angle_supports": _wrong_angle_supports_04(
            [row for row in supports_04 if row.get("on_route")],
            routes_04[0] if routes_04 else [],
        ),
        "supports_04_count": len(supports_04),
        "supports_10_count": len(supports_10),
        "route_available": bool(routes_04 or route_10),
        "touch_tolerance_m": TOUCH_TOLERANCE_M,
        "max_support_gap_04_m": MAX_SUPPORT_GAP_04_M,
        "max_support_gap_10_m": MAX_SUPPORT_GAP_10_M,
        "max_grounding_gap_m": MAX_GROUNDING_GAP_M,
        "straight_angle_max_deg": STRAIGHT_ANGLE_MAX_DEG,
        "ya23_angle_max_deg": YA23_ANGLE_MAX_DEG,
    }


def _station_and_distance(
    point: tuple[float, float],
    route: list[tuple[float, float, float]],
) -> tuple[float, float]:
    if not route or len(route) < 2:
        return 0.0, 9999.0
    best_distance = math.inf
    best_station = 0.0
    travelled = 0.0
    px, py = point
    for index in range(1, len(route)):
        sx, sy, _ = route[index - 1]
        ex, ey, _ = route[index]
        dx = ex - sx
        dy = ey - sy
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            distance = math.hypot(px - sx, py - sy)
            station = travelled
            seg_len = 0.0
        else:
            t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_sq))
            nearest_x = sx + t * dx
            nearest_y = sy + t * dy
            distance = math.hypot(px - nearest_x, py - nearest_y)
            seg_len = math.sqrt(length_sq)
            station = travelled + t * seg_len
        if distance < best_distance:
            best_distance = distance
            best_station = station
        travelled += seg_len
    return best_station, best_distance


def _segment_length(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(bx - ax, by - ay)


def _turn_angle_deg(
    incoming: tuple[float, float],
    outgoing: tuple[float, float],
) -> float:
    ix, iy = incoming
    ox, oy = outgoing
    in_len = math.hypot(ix, iy)
    out_len = math.hypot(ox, oy)
    if in_len < MIN_SEGMENT_M or out_len < MIN_SEGMENT_M:
        return 0.0
    cosang = max(-1.0, min(1.0, (ix * ox + iy * oy) / (in_len * out_len)))
    return math.degrees(math.acos(cosang))


def _vertex_turn_angles(route: list[tuple[float, float, float]]) -> list[dict[str, Any]]:
    """Угол поворота трассы в каждой вершине (0° — прямо, 90° — прямой угол)."""
    if len(route) < 3:
        return []
    vertices: list[dict[str, Any]] = []
    station = 0.0
    for index in range(1, len(route)):
        px, py, _ = route[index - 1]
        qx, qy, _ = route[index]
        station += _segment_length(px, py, qx, qy)
        if index >= len(route) - 1:
            continue
        prev_i = index - 1
        next_i = index + 1
        while prev_i > 0 and _segment_length(route[prev_i][0], route[prev_i][1], route[index][0], route[index][1]) < MIN_SEGMENT_M:
            prev_i -= 1
        while next_i < len(route) - 1 and _segment_length(route[index][0], route[index][1], route[next_i][0], route[next_i][1]) < MIN_SEGMENT_M:
            next_i += 1
        incoming = (route[index][0] - route[prev_i][0], route[index][1] - route[prev_i][1])
        outgoing = (route[next_i][0] - route[index][0], route[next_i][1] - route[index][1])
        vertices.append(
            {
                "index": index,
                "station_m": station,
                "point": (route[index][0], route[index][1]),
                "angle_deg": round(_turn_angle_deg(incoming, outgoing), 1),
            }
        )
    return vertices


def turn_angle_at_point(
    route: list[tuple[float, float, float]],
    point: tuple[float, float],
) -> float:
    """Угол поворота полилинии у точки опоры: у вершины — угол вершины, иначе 0°."""
    if not route or len(route) < 3:
        return 0.0
    px, py = point
    best = None
    best_dist = math.inf
    for vertex in _vertex_turn_angles(route):
        vx, vy = vertex["point"]
        dist = math.hypot(px - vx, py - vy)
        if dist < best_dist:
            best_dist = dist
            best = vertex
    if best is None or best_dist > VERTEX_SNAP_M:
        return 0.0
    return float(best["angle_deg"])


def _suggested_04_support(angle_deg: float) -> str:
    if angle_deg <= STRAIGHT_ANGLE_MAX_DEG:
        return "П23, А23 или К21 (прямолинейный участок, угол ≈ 0°)"
    if angle_deg <= YA23_ANGLE_MAX_DEG:
        return "УА23* (поворот до 90°)"
    return "проверить геометрию трассы: угол больше 90°, УА23* не подходит"


def _wrong_angle_supports_04(
    supports: list[dict[str, Any]],
    route: list[tuple[float, float, float]],
) -> list[dict[str, Any]]:
    if not route or len(route) < 3:
        return []
    issues: list[dict[str, Any]] = []
    for row in supports:
        support_type = str(row.get("support_type") or "")
        if support_type not in SUPPORTS_04:
            continue
        angle = turn_angle_at_point(route, row["point"])
        suggested = _suggested_04_support(angle)
        allowed_max = STRAIGHT_ANGLE_MAX_DEG if support_type in STRAIGHT_SUPPORTS_04 else YA23_ANGLE_MAX_DEG
        if angle <= allowed_max:
            continue
        issues.append(
            {
                "support_type": support_type,
                "number": row.get("number") or "",
                "display_name": row.get("display_name") or _support_display_name(support_type, ""),
                "angle_deg": round(angle, 1),
                "allowed_max_deg": allowed_max,
                "suggested": suggested,
            }
        )
    return issues[:12]


def _near_existing_point(
    point: tuple[float, float],
    others: list[tuple[float, float]],
    *,
    tolerance_m: float = 0.8,
) -> bool:
    px, py = point
    return any(math.hypot(px - ox, py - oy) <= tolerance_m for ox, oy in others)


def _consecutive_gaps(
    items: list[dict[str, Any]],
    *,
    name_key: str,
    limit_m: float,
) -> list[dict[str, Any]]:
    ordered = sorted(items, key=lambda row: float(row.get("station_m") or 0))
    gaps: list[dict[str, Any]] = []
    for left, right in zip(ordered, ordered[1:]):
        distance = abs(float(right.get("station_m") or 0) - float(left.get("station_m") or 0))
        if distance <= limit_m:
            continue
        gaps.append(
            {
                "from_name": left.get(name_key) or "объект",
                "to_name": right.get(name_key) or "объект",
                "distance_m": round(distance, 1),
                "limit_m": limit_m,
            }
        )
    return gaps[:8]


def _gaps_along_route(
    items: list[dict[str, Any]],
    *,
    name_key: str,
    limit_m: float,
    route_length_m: float,
) -> list[dict[str, Any]]:
    """Шаг объектов вдоль трассы, включая участки от начала и до конца линии."""
    ordered = sorted(items, key=lambda row: float(row.get("station_m") or 0))
    length = max(0.0, float(route_length_m or 0))
    gaps: list[dict[str, Any]] = []
    if not ordered:
        return gaps
    first = ordered[0]
    start_gap = float(first.get("station_m") or 0)
    if start_gap > limit_m:
        gaps.append(
            {
                "from_name": "начало трассы",
                "to_name": first.get(name_key) or "объект",
                "distance_m": round(start_gap, 1),
                "limit_m": limit_m,
            }
        )
    gaps.extend(_consecutive_gaps(ordered, name_key=name_key, limit_m=limit_m))
    last = ordered[-1]
    end_gap = length - float(last.get("station_m") or 0)
    if end_gap > limit_m:
        gaps.append(
            {
                "from_name": last.get(name_key) or "объект",
                "to_name": "конец трассы",
                "distance_m": round(end_gap, 1),
                "limit_m": limit_m,
            }
        )
    return gaps[:8]


def _duplicate_support_numbers(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for item in items:
        number = _clean_support_number(str(item.get("number") or ""))
        if not number:
            continue
        voltage = str(item.get("voltage") or "04")
        grouped.setdefault((voltage, number), []).append(
            str(item.get("display_name") or f"опора №{number}")
        )
    result: list[dict[str, Any]] = []
    for (voltage, number), names in grouped.items():
        if len(names) < 2:
            continue
        result.append(
            {
                "number": number,
                "count": len(names),
                "names": names,
                "voltage": voltage,
            }
        )
    return result


def _support_number_int(number: Any) -> int | None:
    cleaned = _clean_support_number(str(number or ""))
    if not cleaned.isdigit():
        return None
    return int(cleaned)


def _support_number_sequence(items: list[dict[str, Any]], *, voltage: str) -> dict[str, Any] | None:
    """Номера вдоль трассы должны идти подряд: 1, 2, 3… или с другого конца 5, 4, 3…"""
    numbered: list[dict[str, Any]] = []
    for item in items:
        value = _support_number_int(item.get("number"))
        if value is None:
            continue
        numbered.append(
            {
                "n": value,
                "station_m": float(item.get("station_m") or 0),
                "display_name": item.get("display_name") or f"опора №{value}",
            }
        )
    if len(numbered) < 2:
        return None
    ordered = sorted(numbered, key=lambda row: (row["station_m"], row["n"]))
    nums = [row["n"] for row in ordered]
    inc_inversions = sum(1 for index, left in enumerate(nums) for right in nums[index + 1 :] if left > right)
    dec_inversions = sum(1 for index, left in enumerate(nums) for right in nums[index + 1 :] if left < right)
    increasing = inc_inversions <= dec_inversions
    start = nums[0]
    expected = [start + offset if increasing else start - offset for offset in range(len(nums))]
    if nums == expected:
        return None
    along = " → ".join(f"№{value}" for value in nums)
    expected_text = " → ".join(f"№{value}" for value in expected)
    breaks = []
    step = 1 if increasing else -1
    for left, right in zip(ordered, ordered[1:]):
        if right["n"] - left["n"] == step:
            continue
        breaks.append(
            {
                "from_name": left["display_name"],
                "to_name": right["display_name"],
                "from_number": left["n"],
                "to_number": right["n"],
                "expected_next": left["n"] + step,
            }
        )
    return {
        "voltage": voltage,
        "along": along,
        "expected": expected_text,
        "direction": "по возрастанию" if increasing else "по убыванию",
        "breaks": breaks[:6],
    }


def _dedupe_off_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = f"{item.get('display_name')}|{item.get('distance_m')}|{item.get('support_type')}"
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _support_display_name(support_type: str, number: str) -> str:
    type_label = {
        "P23": "П23",
        "PP23": "ПП23",
        "A23": "А23",
        "YA23": "УА23*",
        "K21": "К21",
        "P20": "П20",
        "A20": "А20",
        "UA": "УА20",
        "UP": "УП20",
        "ARLK": "А20 с РЛК",
    }.get(support_type, support_type)
    cleaned = _clean_support_number(number)
    if cleaned:
        return f"опора {type_label} №{cleaned}"
    return f"опора {type_label}"


def _clean_support_number(number: str) -> str:
    text = str(number or "").strip()
    text = text.lstrip("№#N ").strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits or text


def _guess_support_number(candidate: dict[str, Any]) -> str:
    label = str(candidate.get("label") or "")
    digits = "".join(ch for ch in label if ch.isdigit())
    return digits


def _collect_grounding_points(
    modelspace: Any,
    document: Any,
    ground_sigs: set[tuple[float, ...]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for insert in modelspace.query("INSERT"):
        label = _attribute_value(insert, "SL_NAME")
        if _is_direct_grounding_insert(insert, label) or _is_anonymous_grounding_insert(
            insert, document, ground_sigs
        ):
            items.append(
                {
                    "point": _insert_plan_point(insert),
                    "label": label.strip(),
                    "block_name": _effective_block_name(insert, document),
                    "insert": insert,
                }
            )
    return items


def _collect_10kv_support_points(modelspace: Any, document: Any) -> list[dict[str, Any]]:
    """Опоры 10 кВ по слоям/подписям (включая динамические блоки)."""
    from backend.core.plan_reader_10kv import (
        SUPPORT_04KV_BLOCKS,
        SUPPORT_10KV_LAYER_FALLBACK,
        classify_10kv_support_label,
        _read_support_label,
        _resolve_block_name,
        GROUND_BLOCKS as GROUND_BLOCKS_10,
    )

    items: list[dict[str, Any]] = []
    for insert in modelspace.query("INSERT"):
        layer_name = str(insert.dxf.layer or "")
        layer_type = SUPPORT_10KV_LAYER_FALLBACK.get(layer_name)
        block_name = _resolve_block_name(document, insert)
        if block_name in GROUND_BLOCKS_10:
            continue
        label = _read_support_label(insert)
        support_type = layer_type or classify_10kv_support_label(label, block_name=block_name)
        if not support_type:
            continue
        if not layer_type and block_name in SUPPORT_04KV_BLOCKS:
            continue
        number = _attribute_value(insert, "SL_NUM").strip()
        items.append(
            {
                "support_type": support_type,
                "number": number,
                "label": label,
                "point": _insert_plan_point(insert),
                "insert": insert,
                "display_name": _support_display_name(support_type, number),
            }
        )
    return items


def _best_route_points(modelspace: Any, *, kind: str) -> list[tuple[float, float, float]]:
    from backend.core.plan_reader_10kv import LINE_10KV_LAYERS

    best_points: list[tuple[float, float, float]] = []
    best_length = 0.0
    for polyline in modelspace.query("LWPOLYLINE"):
        layer_name = str(polyline.dxf.layer or "")
        if kind == "10":
            if layer_name not in LINE_10KV_LAYERS:
                continue
        else:
            # Только явная трасса 0,4 кВ; длинный слой «0» не подменяем.
            if not _layer_matches_04(layer_name):
                if layer_name not in LINE_04_BRANCH_LAYERS:
                    continue
        length = _open_polyline_length(modelspace, polyline)
        if kind == "04" and layer_name in LINE_04_BRANCH_LAYERS and length > LINE_04_BRANCH_MAX_LENGTH_M:
            continue
        if length <= best_length:
            continue
        points = _lwpolyline_points(polyline)
        if len(points) >= 2:
            best_points = points
            best_length = length
    return best_points


def _points_length_xy(points: list[tuple[float, float, float]]) -> float:
    total = 0.0
    for index in range(1, len(points)):
        x0, y0, _ = points[index - 1]
        x1, y1, _ = points[index]
        total += math.hypot(x1 - x0, y1 - y0)
    return total
