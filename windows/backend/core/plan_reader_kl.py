"""Чтение трассы кабельной линии. Чтение полилинии 0,4 кВ и 10 кВ не меняет."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import ezdxf

from backend.core.cable_line import fold_text
from backend.core.dxf_reader import _lwpolyline_length, iter_lwpolylines_for_mark


ROUTE_KL_MARK = "Электрика_КЛ"


def read_plan_kl_data(path: Path) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if path.suffix.lower() != ".dxf":
        return {"line_length_kl_m": 0.0, "plan_has_pzk": False}, warnings

    document = ezdxf.readfile(path)
    modelspace = document.modelspace()
    length_m = _cable_polyline_length_m(modelspace)
    if length_m <= 0:
        warnings.append(
            "Полилиния кабельной линии не найдена: в слое или в имени нет Электрика_КЛ."
        )
    has_pzk = _plan_mentions_pzk(modelspace)
    return {
        "line_length_kl_m": length_m,
        "plan_has_pzk": has_pzk,
    }, warnings


def _cable_polyline_length_m(modelspace: Any) -> float:
    lengths = [
        _lwpolyline_length(polyline)
        for polyline in iter_lwpolylines_for_mark(modelspace, ROUTE_KL_MARK)
        if not polyline.closed and _lwpolyline_length(polyline) > 0
    ]
    if not lengths:
        return 0.0
    return max(lengths)


def _plan_mentions_pzk(modelspace: Any) -> bool:
    for entity in modelspace:
        for text in _entity_texts(entity):
            if "пзк" in fold_text(text):
                return True
    return False


def _entity_texts(entity: Any) -> list[str]:
    texts: list[str] = []
    dxf = getattr(entity, "dxf", None)
    if dxf is not None:
        for attr in ("text", "contents"):
            value = getattr(dxf, attr, None)
            if value:
                texts.append(str(value))
    if entity.dxftype() == "INSERT":
        try:
            for attrib in entity.attribs:
                value = getattr(attrib.dxf, "text", None)
                if value:
                    texts.append(str(value))
        except Exception:
            pass
    if entity.dxftype() == "MULTILEADER":
        try:
            mtext = entity.context.mtext
            value = getattr(mtext, "default_content", None) if mtext is not None else None
            if value:
                texts.append(str(value))
        except Exception:
            pass
    return texts
