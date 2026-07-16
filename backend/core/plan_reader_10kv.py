from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

import ezdxf

from .dxf_reader import _dimension_chain_length_for_polyline, _is_geometrically_closed, _lwpolyline_points, _points_length


SUPPORT_10KV_BLOCKS = {
    "Пл_П20-3Н": "P20",
    "Пл_А20-3Н": "A20",
    "Пл_УП20-3Н": "UP",
    "Пл_УА20-3Н": "UA",
    "Пл_А20-3Н_РЛК": "ARLK",
}

SUPPORT_10KV_LAYER_FALLBACK = SUPPORT_10KV_BLOCKS

GROUND_BLOCKS = {"Пл_Заземление"}

# Блоки опор 0,4 кВ: на 10 кВ-слоях их не считаем как А20/АРЛК.
SUPPORT_04KV_BLOCKS = {
    "Пл_ОпораНВ_А23",
    "Пл_ОпораП23",
    "Пл_ОпораУА23",
    "Пл_ОпораНВ_УА23",
    "Пл_ОпораК21",
}

SUPPORT_LABEL_ATTR_TAGS = ("SL_NAME_001", "SL_NAME", "Название", "NAME")

LINE_10KV_LAYERS = ("10", "Электрика_10")
LINE_04_LAYERS = ("04", "Электрика_04")
LINE_04_LAYER_PREFIXES = ("04",)
LINE_04_BRANCH_LAYERS = ("0",)
LINE_04_BRANCH_MAX_LENGTH_M = 100.0


def read_plan_10kv_data(path: Path) -> tuple[dict[str, Any], list[str]]:
    if path.suffix.lower() != ".dxf":
        raise ValueError("Анализ 10 кВ поддерживается только для DXF.")

    document = ezdxf.readfile(path)
    modelspace = document.modelspace()
    warnings: list[str] = []

    supports = _count_10kv_supports(document, modelspace)

    line_length_10_m = _find_line_length_on_layers(modelspace, LINE_10KV_LAYERS)
    line_length_04_m = _find_line_length_04kv(modelspace)
    if line_length_10_m <= 0:
        warnings.append(
            f"Полилиния 10 кВ не найдена на слоях: {', '.join(LINE_10KV_LAYERS)}."
        )
    if line_length_04_m <= 0:
        warnings.append(
            "Полилиния 0,4 кВ не найдена на слоях "
            f"{', '.join(LINE_04_LAYERS)} и короткой ветви на слое 0."
        )

    line_length_km = line_length_10_m / 1000 if line_length_10_m > 0 else 0.0
    line_length_04_km = line_length_04_m / 1000 if line_length_04_m > 0 else 0.0
    power_10 = _format_km(line_length_km)
    data = {
        "supports_10kv": dict(supports),
        "line_length_10kv_m": line_length_10_m,
        "line_length_10kv_km": line_length_km,
        "line_length_04kv_m": line_length_04_m,
        "line_length_04kv_km": line_length_04_km,
        "KM_10": power_10,
        "KM_04": _format_km(line_length_04_km),
        "POWER_10": power_10,
        "POWER_LENGT_M": _format_m(line_length_04_m),
    }
    return data, warnings


def classify_10kv_support_label(label: str, *, block_name: str = "") -> str | None:
    normalized = _normalize_support_label(label)
    if not normalized:
        return None
    if normalized in {"А23", "A23", "П23", "P23", "УА23", "YA23", "К21", "K21"}:
        return None
    if _is_arlk_support_label(normalized):
        return "ARLK"
    if re.fullmatch(r"П20[- ]?3Н", normalized, re.IGNORECASE):
        return "P20"
    if re.fullmatch(r"УП20[- ]?3Н", normalized, re.IGNORECASE):
        return "UP"
    if re.fullmatch(r"УА20[- ]?3Н", normalized, re.IGNORECASE):
        return "UA"
    if re.fullmatch(r"А20[- ]?3Н", normalized, re.IGNORECASE):
        if block_name in SUPPORT_04KV_BLOCKS:
            return None
        return "A20"
    return None


def _count_10kv_supports(document: Any, modelspace: Any) -> Counter[str]:
    supports = Counter({key: 0 for key in ("P20", "A20", "UP", "UA", "ARLK")})
    for insert in modelspace.query("INSERT"):
        # Для планов 10 кВ точный слой является главным источником типа опоры.
        # Динамический блок А20-3Н с РЛК может раскрываться как старый блок А23,
        # поэтому проверка имени блока до слоя ошибочно исключала такую опору.
        layer_name = str(insert.dxf.layer or "")
        layer_type = SUPPORT_10KV_LAYER_FALLBACK.get(layer_name)
        if layer_type:
            supports[layer_type] += 1
            continue

        block_name = _resolve_block_name(document, insert)
        if block_name in GROUND_BLOCKS:
            continue

        label = _read_support_label(insert)
        support_type = classify_10kv_support_label(label, block_name=block_name)
        if support_type:
            supports[support_type] += 1
            continue

        if block_name in SUPPORT_04KV_BLOCKS:
            continue
    return supports


def _resolve_block_name(document: Any, insert: Any) -> str:
    block_name = str(insert.dxf.name or "")
    if block_name.startswith("*") and block_name in document.blocks:
        block_record = document.blocks[block_name].block_record
        try:
            tags = block_record.get_xdata("AcDbBlockRepBTag")
        except Exception:
            tags = None
        if tags:
            for tag in tags:
                if tag.code != 1005:
                    continue
                source_record = document.entitydb.get(tag.value)
                source_name = getattr(getattr(source_record, "dxf", None), "name", "")
                if source_name:
                    return str(source_name)
    return block_name


def _read_support_label(insert: Any) -> str:
    attribs = list(getattr(insert, "attribs", []) or [])
    if not attribs:
        return ""
    by_tag: dict[str, str] = {}
    for attrib in attribs:
        tag = str(attrib.dxf.tag or "").strip()
        text = str(attrib.dxf.text or "").strip()
        if tag and text:
            by_tag[tag] = text
    for tag in SUPPORT_LABEL_ATTR_TAGS:
        if by_tag.get(tag):
            return by_tag[tag]
    for tag, text in by_tag.items():
        if tag.endswith("NAME_001") or tag in {"Название", "NAME"}:
            return text
    return ""


def _normalize_support_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.replace("–", "-").replace("—", "-")).strip()


def _is_arlk_support_label(label: str) -> bool:
    upper = label.upper()
    return any(marker in upper for marker in ("+КР2", "+KR2", "РЛК", "RLK"))


def _layer_matches_04(line_layer: str) -> bool:
    if line_layer in LINE_04_LAYERS:
        return True
    return any(line_layer.startswith(prefix) for prefix in LINE_04_LAYER_PREFIXES)


def _find_line_length_04kv(modelspace: Any) -> float:
    candidates: list[float] = []
    for polyline in modelspace.query("LWPOLYLINE"):
        layer_name = str(polyline.dxf.layer or "")
        if not _layer_matches_04(layer_name):
            continue
        length = _open_polyline_length(modelspace, polyline)
        if length > 0:
            candidates.append(length)
    if candidates:
        return max(candidates)

    branch_candidates: list[float] = []
    for polyline in modelspace.query("LWPOLYLINE"):
        layer_name = str(polyline.dxf.layer or "")
        if layer_name not in LINE_04_BRANCH_LAYERS:
            continue
        length = _open_polyline_length(modelspace, polyline)
        if 0 < length <= LINE_04_BRANCH_MAX_LENGTH_M:
            branch_candidates.append(length)
    return min(branch_candidates) if branch_candidates else 0.0


def _open_polyline_length(modelspace: Any, polyline: Any) -> float:
    if polyline.closed:
        return 0.0
    points = _lwpolyline_points(polyline)
    if _is_geometrically_closed(points):
        return 0.0
    geometry_length = _points_length(points)
    if geometry_length <= 0:
        return 0.0
    dimension_length = _dimension_chain_length_for_polyline(
        modelspace,
        points,
        polyline.dxf.layer,
        geometry_length,
    )
    return float(dimension_length["length"] if dimension_length else geometry_length)


def _find_line_length_on_layers(modelspace: Any, layer_names: tuple[str, ...]) -> float:
    allowed = set(layer_names)
    candidates: list[float] = []
    for polyline in modelspace.query("LWPOLYLINE"):
        if polyline.dxf.layer not in allowed:
            continue
        length = _open_polyline_length(modelspace, polyline)
        if length > 0:
            candidates.append(length)
    return max(candidates) if candidates else 0.0


def _format_m(value: float) -> str:
    if value <= 0:
        return ""
    if value < 100:
        rounded = round(value)
        return str(int(rounded))
    rounded = round(value, 3)
    if rounded.is_integer():
        return str(int(rounded))
    text = f"{rounded:.3f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _format_km(value: float) -> str:
    if value <= 0:
        return ""
    rounded = round(value, 3)
    text = f"{rounded:.3f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")
