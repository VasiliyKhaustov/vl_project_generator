from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf import bbox


SUPPORT_BY_BLOCK = {
    "Пл_ОпораП23": "P23",
    "Пл_ОпораНВ_А23": "A23",
    "Пл_ОпораУА23": "YA23",
    "Пл_ОпораНВ_УА23": "YA23",
    "Пл_ОпораК21": "K21",
}

SUPPORT_BY_LABEL = {
    "П23": "P23",
    "А23": "A23",
    "УА23*": "YA23",
    "УА23": "YA23",
    "К21": "K21",
    "УП23": "P23",
    "UP23": "P23",
    "YA23": "YA23",
    "P23": "P23",
    "A23": "A23",
    "K21": "K21",
}

SUPPORT_SHORT_LABELS = {
    "П": "P23",
    "К": "K21",
    "А": "A23",
    "УА": "YA23",
    "УП": "P23",
    "P": "P23",
    "K": "K21",
    "A": "A23",
}

SUPPORT_BY_CATALOG = {
    "25.0017-02": "P23",
    "25.0017-06": "P23",
    "25.0017-08": "A23",
    "21.0112-09": "YA23",
    "21.0112-04": "K21",
}

CATALOG_CODE_RE = re.compile(r"(?:21\.0112|25\.0017)-\d{2}")
LOCAL_COORDINATE_CLUSTER_MAX = 5000.0
GEOREF_COORDINATE_CLUSTER_MIN = 100000.0

GROUND_BLOCKS = {"Пл_Заземление"}

GENERIC_SUPPORT_BLOCKS = {
    "stolb NN": "K21",
}

LEP_SUPPORT_LAYER_MARKERS = ("лэп", "электрика")

SUPPORT_BLOCK_ALIASES: dict[str, frozenset[str]] = {
    "P23": frozenset({"Пл_ОпораП23", "Пл_Опора"}),
    "A23": frozenset({"Пл_ОпораНВ_А23"}),
    "YA23": frozenset({"Пл_ОпораУА23", "Пл_ОпораНВ_УА23"}),
    "K21": frozenset({"Пл_ОпораК21"}),
}

SUPPORT_MAX_DISTANCE_FROM_LINE_M = 50.0


def analyze_dxf(path: Path) -> tuple[dict[str, Any], list[str]]:
    if path.suffix.lower() != ".dxf":
        raise ValueError("На macOS MVP анализируется DXF. DWG будет поддержан на Windows-этапе через AutoCAD.")

    document = ezdxf.readfile(path)
    modelspace = document.modelspace()
    warnings: list[str] = []

    supports = Counter({"P23": 0, "A23": 0, "YA23": 0, "K21": 0})
    grounding_count = 0
    anonymous_grounding_count = 0
    ground_block_signatures = _ground_block_signatures(document)

    for insert in modelspace.query("INSERT"):
        block_name = _effective_block_name(insert, document)
        label = _attribute_value(insert, "SL_NAME")
        if _is_direct_grounding_insert(insert, label):
            grounding_count += 1
        elif _is_anonymous_grounding_insert(insert, document, ground_block_signatures):
            anonymous_grounding_count += 1

    support_candidates = _collect_support_candidates(modelspace, document)
    support_points = [candidate["point"] for candidate in support_candidates]

    main_polyline = _find_main_polyline(modelspace, support_points)
    route_points = _polyline_points_for_entity(modelspace, main_polyline) if main_polyline else []
    route_length_m = float(main_polyline["length"]) if main_polyline else 0.0
    counting_cluster = _select_support_counting_cluster(support_candidates, route_points)
    filtered_candidates = [
        candidate
        for candidate in support_candidates
        if _coordinate_cluster_key(candidate["point"]) == counting_cluster
    ]
    route_cluster = None
    if route_points:
        centroid = (
            sum(point[0] for point in route_points) / len(route_points),
            sum(point[1] for point in route_points) / len(route_points),
        )
        route_cluster = _coordinate_cluster_key(centroid)
    mismatch_points = _catalog_support_points(filtered_candidates)
    if not mismatch_points:
        mismatch_points = [candidate["point"] for candidate in filtered_candidates]
    enforce_route_proximity = (
        bool(route_points)
        and counting_cluster == route_cluster
        and not _route_support_coordinate_mismatch(
            route_points,
            mismatch_points,
            route_length_m,
        )
    )

    skipped_mismatched_support = 0
    skipped_off_route_support = 0
    skipped_existing_support = 0
    skipped_start_anchor_support = 0
    route_start = (route_points[0][0], route_points[0][1]) if route_points else None
    p23_candidates = [
        candidate
        for candidate in filtered_candidates
        if candidate["support_type"] == "P23" and not candidate["is_existing"]
    ]
    k21_candidates = [
        candidate
        for candidate in filtered_candidates
        if candidate["support_type"] == "K21" and not candidate["is_existing"]
    ]
    has_route_end_k21 = _has_route_end_k21(route_points, filtered_candidates)
    skip_start_anchor_p23 = (
        bool(route_start)
        and has_route_end_k21
        and len(p23_candidates) >= 2
    )
    skip_start_anchor_k21 = (
        bool(route_start)
        and has_route_end_k21
        and len(k21_candidates) >= 2
    )
    start_anchor_tolerance = 2.0

    catalog_k21_candidates = [
        candidate
        for candidate in filtered_candidates
        if candidate["block_name"] == "Пл_ОпораК21" and not candidate["is_existing"]
    ]
    skip_generic_k21_when_catalog_present = len(catalog_k21_candidates) >= 2

    for candidate in filtered_candidates:
        insert = candidate["insert"]
        block_name = candidate["block_name"]
        label = candidate["label"]
        catalog_code = candidate["catalog_code"]
        support_type = candidate["support_type"]

        if candidate["is_existing"]:
            skipped_existing_support += 1
            continue

        if not support_type:
            continue

        if (
            skip_generic_k21_when_catalog_present
            and block_name in GENERIC_SUPPORT_BLOCKS
            and support_type == "K21"
        ):
            continue

        allowed_blocks = SUPPORT_BLOCK_ALIASES.get(support_type, frozenset())
        generic_blocks = frozenset(
            block_name for block_name, mapped_type in GENERIC_SUPPORT_BLOCKS.items() if mapped_type == support_type
        )
        if (
            allowed_blocks
            and block_name not in allowed_blocks
            and block_name not in generic_blocks
            and label not in SUPPORT_BY_LABEL
            and not catalog_code
        ):
            skipped_mismatched_support += 1
            continue
        if enforce_route_proximity and not _is_support_on_route(insert, route_points, route_length_m):
            skipped_off_route_support += 1
            continue
        if (
            skip_start_anchor_p23
            and support_type == "P23"
            and _is_near_route_point(candidate["point"], route_start, start_anchor_tolerance)
        ):
            skipped_start_anchor_support += 1
            continue
        if (
            skip_start_anchor_k21
            and support_type == "K21"
            and _is_near_route_point(candidate["point"], route_start, start_anchor_tolerance)
        ):
            skipped_start_anchor_support += 1
            continue
        supports[support_type] += 1

    if skipped_mismatched_support:
        warnings.append(
            f"Найдено {skipped_mismatched_support} блоков опор с несовпадающей подписью SL_NAME и типом блока. Они не учтены."
        )
    if skipped_off_route_support:
        warnings.append(
            f"Найдено {skipped_off_route_support} блоков опор вне основной трассы ВЛ. Они не учтены."
        )
    if skipped_existing_support:
        warnings.append(
            f"Найдено {skipped_existing_support} существующих опор на плане. Они не учтены."
        )
    if skipped_start_anchor_support:
        warnings.append(
            f"Найдено {skipped_start_anchor_support} опор у начала трассы (точка присоединения). "
            "Они не учтены, так как концевая опора К21 стоит на другом конце трассы."
        )
    if filtered_candidates and route_points and not enforce_route_proximity:
        warnings.append(
            "Опоры и основная полилиния находятся в разных системах координат. "
            "Количество опор посчитано по всем блокам на плане без фильтра по трассе."
        )

    if grounding_count == 0 and anonymous_grounding_count:
        grounding_count = anonymous_grounding_count
        warnings.append(
            f"Заземления найдены как анонимные динамические вставки блока Пл_Заземление: {anonymous_grounding_count}."
        )

    if grounding_count == 0:
        esmt_grounding_count = _count_esmt_ground_elements(path)
        if esmt_grounding_count:
            grounding_count = esmt_grounding_count
            warnings.append(
                f"Заземления найдены в служебных ESMT-данных DXF: {esmt_grounding_count}."
            )

    if main_polyline is None:
        line_length_m = 0.0
        warnings.append("Основная полилиния ВЛ не найдена.")
    else:
        line_length_m = main_polyline["length"]
        if main_polyline["candidates"] > 1:
            warnings.append(
                "В плане найдено несколько полилиний. Для MVP выбрана полилиния на слое Электрика "
                "с наибольшим числом опор рядом с трассой."
            )

    line_length_km = line_length_m / 1000
    a3_sheet_count = count_a3_route_sheets(path)
    data = {
        "line_length_m": line_length_m,
        "line_length_km": line_length_km,
        "supports": dict(supports),
        "grounding_count": grounding_count,
        "main_polyline": main_polyline,
        "source_file": path.name,
        "a3_sheet_count": a3_sheet_count,
    }
    if a3_sheet_count == 0:
        warnings.append("В плане не найдены листы формата А3. Для расчёта количества листов записки принято значение 1.")
        data["a3_sheet_count"] = 1
    return data, warnings


def count_a3_route_sheets(path: Path) -> int:
    document = ezdxf.readfile(path)
    total = 0
    for layout in document.layouts:
        if layout.name.lower() == "model":
            continue
        insert_count = 0
        polyline_count = 0
        for entity in layout:
            if entity.dxftype() not in {"LWPOLYLINE", "POLYLINE", "INSERT"}:
                continue
            try:
                extents = bbox.extents([entity])
            except Exception:
                continue
            width = abs(float(extents.size.x))
            height = abs(float(extents.size.y))
            if not _is_a3_sheet_size(width, height):
                continue
            if entity.dxftype() == "INSERT":
                insert_count += 1
            else:
                polyline_count += 1
        layout_count = max(insert_count, polyline_count)
        if layout_count:
            total += layout_count
    return total


def _is_a3_sheet_size(width: float, height: float) -> bool:
    return (abs(width - 420.0) < 2.0 and abs(height - 297.0) < 2.0) or (
        abs(width - 297.0) < 2.0 and abs(height - 420.0) < 2.0
    )


def _polyline_points_for_entity(modelspace: Any, main_polyline: dict[str, Any] | None) -> list[tuple[float, float, float]]:
    if main_polyline is None:
        return []
    handle = main_polyline.get("handle")
    if not handle:
        return []
    for polyline in modelspace.query("LWPOLYLINE"):
        if polyline.dxf.handle == handle:
            return _lwpolyline_points(polyline)
    return []


def _support_distance_tolerance(line_length_m: float) -> float:
    return max(15.0, min(SUPPORT_MAX_DISTANCE_FROM_LINE_M, line_length_m * 0.5))


def _is_near_route_point(
    point: tuple[float, float],
    route_point: tuple[float, float] | None,
    tolerance: float,
) -> bool:
    if route_point is None:
        return False
    return math.hypot(point[0] - route_point[0], point[1] - route_point[1]) <= tolerance


def _has_route_end_k21(
    route_points: list[tuple[float, float, float]],
    candidates: list[dict[str, Any]],
) -> bool:
    if len(route_points) < 2:
        return False

    start = (route_points[0][0], route_points[0][1])
    end = (route_points[-1][0], route_points[-1][1])
    for candidate in candidates:
        if candidate["is_existing"] or candidate["support_type"] != "K21":
            continue
        point = candidate["point"]
        dist_to_start = math.hypot(point[0] - start[0], point[1] - start[1])
        dist_to_end = math.hypot(point[0] - end[0], point[1] - end[1])
        if dist_to_end + 1.0 < dist_to_start:
            return True
    return False


def _is_support_on_route(
    insert: Any,
    route_points: list[tuple[float, float, float]],
    line_length_m: float,
) -> bool:
    if not route_points:
        return True
    point = (float(insert.dxf.insert.x), float(insert.dxf.insert.y))
    return _distance_to_polyline(point, route_points) <= _support_distance_tolerance(line_length_m)


def _attribute_catalog_code(insert: Any) -> str:
    for attrib in insert.attribs:
        match = CATALOG_CODE_RE.search(attrib.dxf.text)
        if match:
            return match.group(0)
    return ""


def _normalize_support_label(label: str) -> str:
    normalized = label.strip()
    if not normalized:
        return ""
    if normalized in SUPPORT_BY_LABEL:
        return normalized
    compact = re.sub(r"\s+", "", normalized)
    if compact in SUPPORT_BY_LABEL:
        return compact
    return SUPPORT_SHORT_LABELS.get(normalized, SUPPORT_SHORT_LABELS.get(compact, normalized))


def _resolve_support_type(
    block_name: str,
    label: str,
    catalog_code: str,
    layer: str = "",
    *,
    stolb_nn_total: int = 0,
) -> str | None:
    normalized_label = _normalize_support_label(label)
    if normalized_label in SUPPORT_BY_LABEL:
        return SUPPORT_BY_LABEL[normalized_label]
    if catalog_code in SUPPORT_BY_CATALOG:
        return SUPPORT_BY_CATALOG[catalog_code]
    if block_name in SUPPORT_BY_BLOCK:
        return SUPPORT_BY_BLOCK[block_name]
    if (
        block_name == "stolb NN"
        and stolb_nn_total <= 3
        and _is_lep_support_layer(layer)
    ):
        return GENERIC_SUPPORT_BLOCKS[block_name]
    return None


def _is_lep_support_layer(layer: str) -> bool:
    normalized = layer.strip().lower().replace("ё", "е")
    return any(marker in normalized for marker in LEP_SUPPORT_LAYER_MARKERS)


def _is_existing_support_marker(label: str, insert: Any) -> bool:
    if re.fullmatch(r"№[\w/-]+", label.strip()):
        return True
    existing_number = _attribute_value(insert, "SL_NUM").strip().lower()
    return existing_number.startswith("сущ")


def _coordinate_cluster_key(point: tuple[float, float]) -> str:
    magnitude = max(abs(point[0]), abs(point[1]))
    if magnitude < LOCAL_COORDINATE_CLUSTER_MAX:
        return "local"
    if magnitude >= GEOREF_COORDINATE_CLUSTER_MIN:
        return "georef"
    return "mid"


def _select_support_counting_cluster(
    candidates: list[dict[str, Any]],
    route_points: list[tuple[float, float, float]],
) -> str:
    if not candidates:
        return "local"

    grouped: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        cluster = _coordinate_cluster_key(candidate["point"])
        grouped.setdefault(cluster, []).append(candidate)

    if len(grouped) == 1:
        return next(iter(grouped))

    route_cluster = None
    if route_points:
        centroid = (
            sum(point[0] for point in route_points) / len(route_points),
            sum(point[1] for point in route_points) / len(route_points),
        )
        route_cluster = _coordinate_cluster_key(centroid)

    counts = {cluster: len(items) for cluster, items in grouped.items()}
    max_count = max(counts.values())
    leaders = [cluster for cluster, count in counts.items() if count == max_count]
    if len(leaders) == 1:
        return leaders[0]

    if "local" in leaders and "georef" in grouped:
        local_specific_blocks = {
            "Пл_ОпораП23",
            "Пл_ОпораК21",
            "Пл_ОпораУА23",
            "Пл_ОпораНВ_УА23",
        }
        if any(candidate["block_name"] in local_specific_blocks for candidate in grouped["local"]):
            return "local"

    if route_cluster in leaders:
        return route_cluster
    if "local" in leaders:
        return "local"
    return leaders[0]


def _attribute_value(insert: Any, tag: str) -> str:
    for attrib in insert.attribs:
        if attrib.dxf.tag == tag:
            return attrib.dxf.text.strip()
    prefix = f"{tag}_"
    for attrib in insert.attribs:
        attrib_tag = attrib.dxf.tag
        if attrib_tag.startswith(prefix):
            return attrib.dxf.text.strip()
    return ""


def _effective_block_name(insert: Any, document: Any) -> str:
    block_name = insert.dxf.name
    if not block_name.startswith("*") or block_name not in document.blocks:
        return block_name

    block_record = document.blocks[block_name].block_record
    try:
        tags = block_record.get_xdata("AcDbBlockRepBTag")
    except Exception:
        return block_name

    for tag in tags:
        if tag.code != 1005:
            continue
        source_record = document.entitydb.get(tag.value)
        source_name = getattr(getattr(source_record, "dxf", None), "name", "")
        if source_name:
            return source_name
    return block_name


def _is_direct_grounding_insert(insert: Any, label: str) -> bool:
    values = (
        insert.dxf.name,
        insert.dxf.layer,
        label,
    )
    return any(value in GROUND_BLOCKS or "зазем" in value.lower() for value in values if value)


def _is_anonymous_grounding_insert(
    insert: Any,
    document: Any,
    ground_block_signatures: set[tuple[float, ...]],
) -> bool:
    block_name = insert.dxf.name
    if not block_name.startswith("*"):
        return False

    return _block_line_length_signature(document, block_name) in ground_block_signatures


def _ground_block_signatures(document: Any) -> set[tuple[float, ...]]:
    signatures: set[tuple[float, ...]] = set()
    for block_name in GROUND_BLOCKS:
        signature = _block_line_length_signature(document, block_name)
        if signature:
            signatures.add(signature)
    return signatures


def _block_line_length_signature(document: Any, block_name: str) -> tuple[float, ...]:
    if block_name not in document.blocks:
        return ()

    lengths: list[float] = []
    other_entities = 0
    for entity in document.blocks[block_name]:
        if entity.dxftype() == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            lengths.append(round(math.dist((start.x, start.y, start.z), (end.x, end.y, end.z)), 3))
        else:
            other_entities += 1

    if not lengths or other_entities:
        return ()
    return tuple(sorted(lengths))


def _count_esmt_ground_elements(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r'<Element\s+type="ground"(?=\s|>)', text, flags=re.IGNORECASE))


def _collect_support_candidates(modelspace: Any, document: Any) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    ground_block_signatures = _ground_block_signatures(document)
    inserts = list(modelspace.query("INSERT"))
    stolb_nn_total = sum(
        1
        for insert in inserts
        if _effective_block_name(insert, document) == "stolb NN"
        and _is_lep_support_layer(str(insert.dxf.layer or ""))
    )

    for insert in inserts:
        block_name = _effective_block_name(insert, document)
        label = _attribute_value(insert, "SL_NAME")
        catalog_code = _attribute_catalog_code(insert)
        layer = str(insert.dxf.layer or "")
        support_type = _resolve_support_type(
            block_name,
            label,
            catalog_code,
            layer,
            stolb_nn_total=stolb_nn_total,
        )
        is_existing = _is_existing_support_marker(label, insert)

        if _is_direct_grounding_insert(insert, label):
            continue
        if _is_anonymous_grounding_insert(insert, document, ground_block_signatures):
            continue

        if support_type is None and block_name not in SUPPORT_BY_BLOCK and not is_existing:
            continue

        candidates.append(
            {
                "insert": insert,
                "block_name": block_name,
                "label": label,
                "catalog_code": catalog_code,
                "support_type": support_type,
                "is_existing": is_existing,
                "point": (float(insert.dxf.insert.x), float(insert.dxf.insert.y)),
            }
        )
    return candidates


def _catalog_support_points(candidates: list[dict[str, Any]]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for candidate in candidates:
        block_name = candidate["block_name"]
        if block_name in GENERIC_SUPPORT_BLOCKS:
            continue
        if block_name in SUPPORT_BY_BLOCK:
            points.append(candidate["point"])
    return points


def _route_support_coordinate_mismatch(
    route_points: list[tuple[float, float, float]],
    support_points: list[tuple[float, float]],
    line_length_m: float,
) -> bool:
    if not route_points or not support_points:
        return False

    tolerance = _support_distance_tolerance(line_length_m)
    near_count = sum(
        1 for point in support_points if _distance_to_polyline(point, route_points) <= tolerance
    )
    if near_count:
        return False

    centroid = (
        sum(point[0] for point in support_points) / len(support_points),
        sum(point[1] for point in support_points) / len(support_points),
    )
    centroid_distance = _distance_to_polyline(centroid, route_points)
    mismatch_threshold = max(200.0, min(2000.0, line_length_m * 5))
    return centroid_distance > mismatch_threshold


def _find_main_polyline(
    modelspace: Any,
    support_points: list[tuple[float, float]] | None = None,
) -> dict[str, Any] | None:
    candidates = []
    for polyline in modelspace.query("LWPOLYLINE"):
        if polyline.closed:
            continue
        points = _lwpolyline_points(polyline)
        if _is_geometrically_closed(points):
            continue
        geometry_length = _points_length(points)
        if geometry_length <= 0:
            continue
        dimension_length = _dimension_chain_length_for_polyline(modelspace, points, polyline.dxf.layer, geometry_length)
        length = dimension_length["length"] if dimension_length else geometry_length
        nearby_supports = 0
        if support_points:
            tolerance = _support_distance_tolerance(length)
            nearby_supports = sum(
                1
                for point in support_points
                if _distance_to_polyline(point, points) <= tolerance
            )
        candidates.append(
            {
                "length": length,
                "geometry_length": geometry_length,
                "dimension_length": dimension_length["length"] if dimension_length else None,
                "dimension_count": dimension_length["count"] if dimension_length else 0,
                "layer": polyline.dxf.layer,
                "handle": polyline.dxf.handle,
                "vertices": len(polyline),
                "nearby_supports": nearby_supports,
            }
        )

    if not candidates:
        return None

    electrical = [candidate for candidate in candidates if candidate["layer"] == "Электрика"]
    pool = electrical or candidates
    selected = max(pool, key=lambda item: (item["nearby_supports"], item["length"]))
    selected["candidates"] = len(pool)
    if selected.get("dimension_length") is not None:
        selected["selection_rule"] = "dimension_chain_on_electrical_polyline" if electrical else "dimension_chain_on_polyline"
    else:
        selected["selection_rule"] = "longest_open_lwpolyline_on_electrical_layer" if electrical else "longest_open_lwpolyline"
    return selected


def _lwpolyline_length(polyline: Any) -> float:
    return _points_length(_lwpolyline_points(polyline))


def _lwpolyline_points(polyline: Any) -> list[tuple[float, float, float]]:
    return [(float(x), float(y), float(bulge or 0)) for x, y, bulge in polyline.get_points("xyb")]


def _points_length(points: list[tuple[float, float, float]]) -> float:
    if len(points) < 2:
        return 0.0

    total = 0.0
    for current, next_point in zip(points, points[1:]):
        total += _segment_length((current[0], current[1]), (next_point[0], next_point[1]), current[2])
    return total


def _segment_length(start: tuple[float, float], end: tuple[float, float], bulge: float) -> float:
    chord = math.hypot(end[0] - start[0], end[1] - start[1])
    if chord == 0 or not bulge:
        return chord

    theta = 4 * math.atan(abs(bulge))
    if theta == 0:
        return chord

    radius = chord / (2 * math.sin(theta / 2))
    return abs(radius * theta)


def _is_geometrically_closed(points: list[tuple[float, float, float]], tolerance: float = 0.05) -> bool:
    if len(points) < 3:
        return False
    start = points[0]
    end = points[-1]
    return math.hypot(end[0] - start[0], end[1] - start[1]) <= tolerance


def _dimension_chain_length_for_polyline(
    modelspace: Any,
    points: list[tuple[float, float, float]],
    layer: str,
    geometry_length: float,
) -> dict[str, Any] | None:
    display_values: list[float] = []
    actual_values: list[float] = []
    tolerance = max(2.0, min(6.0, geometry_length * 0.04))

    for dimension in modelspace.query("DIMENSION"):
        if dimension.dxf.layer != layer:
            continue
        defpoint2 = getattr(dimension.dxf, "defpoint2", None)
        defpoint3 = getattr(dimension.dxf, "defpoint3", None)
        actual = float(getattr(dimension.dxf, "actual_measurement", 0) or 0)
        if defpoint2 is None or defpoint3 is None or actual <= 0:
            continue
        p2 = (float(defpoint2.x), float(defpoint2.y))
        p3 = (float(defpoint3.x), float(defpoint3.y))
        if max(_distance_to_polyline(p2, points), _distance_to_polyline(p3, points)) > tolerance:
            continue
        display_value = _display_dimension_value(dimension, actual)
        if display_value <= 0:
            continue
        display_values.append(display_value)
        actual_values.append(actual)

    if not display_values:
        return None

    actual_sum = sum(actual_values)
    if not (geometry_length * 0.65 <= actual_sum <= geometry_length * 1.35):
        return None

    display_sum = sum(display_values)
    return {
        "length": _snap_dimension_chain_total(display_sum),
        "count": len(display_values),
    }


def _snap_dimension_chain_total(value: float) -> float:
    """Snap tiny rounding drift in manual dimension chains without changing normal geometry."""
    if value <= 0:
        return value
    nearest_ten = round(value / 10) * 10
    if abs(value - nearest_ten) <= 1.25:
        return float(nearest_ten)
    return value


def _display_dimension_value(dimension: Any, actual: float) -> float:
    text = str(getattr(dimension.dxf, "text", "") or "").strip()
    if text and text not in {"<>", " "}:
        match = re.search(r"\d+(?:[,.]\d+)?", text)
        if match:
            return float(match.group(0).replace(",", "."))
    return float(round(actual))


def _distance_to_polyline(point: tuple[float, float], points: list[tuple[float, float, float]]) -> float:
    distances = [
        _distance_to_segment(point, (start[0], start[1]), (end[0], end[1]))
        for start, end in zip(points, points[1:])
    ]
    return min(distances) if distances else math.inf


def _distance_to_segment(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    px, py = point
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - sx, py - sy)
    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_sq))
    nearest_x = sx + t * dx
    nearest_y = sy + t * dy
    return math.hypot(px - nearest_x, py - nearest_y)
