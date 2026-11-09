from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cable_format import format_cable_section_display


class WireSelectionError(ValueError):
    pass


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_wire_catalog(catalog_path: Path | None = None) -> dict[str, Any]:
    path = catalog_path or (_project_root() / "config" / "wire_catalog.json")
    if not path.exists():
        raise WireSelectionError(f"Справочник проводов не найден: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WireSelectionError(f"Справочник проводов повреждён: {path}") from exc
    if not isinstance(payload.get("wires"), dict):
        raise WireSelectionError("Справочник проводов не содержит раздел wires.")
    return payload


def normalize_wire_key(value: str) -> str:
    return str(value or "").strip().replace("x", "*").replace("х", "*").replace("Х", "*")


def resolve_final_wire(auto_wire: str, manual_wire: str | None, mode: str) -> str:
    if mode == "manual":
        if not manual_wire:
            raise WireSelectionError("Выбран ручной режим провода, но провод не указан.")
        return str(manual_wire).strip()
    return str(auto_wire or "").strip()


def _catalog_entry_by_key(catalog: dict[str, Any], wire_name: str) -> dict[str, Any] | None:
    wires = catalog.get("wires", {})
    key = normalize_wire_key(wire_name)
    if key in wires:
        return wires[key]

    for entry in wires.values():
        if normalize_wire_key(entry.get("label", "")) == key:
            return entry
        if normalize_wire_key(entry.get("sech_kabel", "")) == key:
            return entry
    return None


def _resolve_catalog_key(catalog: dict[str, Any], wire_name: str) -> str | None:
    wires = catalog.get("wires", {})
    key = normalize_wire_key(wire_name)
    if key in wires:
        return key

    for catalog_key, entry in wires.items():
        if normalize_wire_key(entry.get("sech_kabel", "")) == key:
            return catalog_key
    return None


def get_wire_weight(
    wire_name: str,
    *,
    catalog: dict[str, Any] | None = None,
    require_weight: bool = True,
) -> dict[str, Any]:
    catalog = catalog or load_wire_catalog()
    entry = _catalog_entry_by_key(catalog, wire_name)
    if entry is None:
        raise WireSelectionError("Выбранный провод отсутствует в справочнике проводов.")

    weight = entry.get("weight_kg_per_km")
    if weight is None:
        if require_weight:
            raise WireSelectionError(
                "Для выбранного провода не задан вес. Заполните вес в справочнике проводов."
            )
        return {
            "wire": wire_name,
            "weight_kg_per_km": None,
            "weight_source": None,
        }

    try:
        weight_value = float(weight)
    except (TypeError, ValueError) as exc:
        raise WireSelectionError(
            "Для выбранного провода не задан вес. Заполните вес в справочнике проводов."
        ) from exc

    return {
        "wire": wire_name,
        "weight_kg_per_km": weight_value,
        "weight_source": entry.get("weight_source") or "config/wire_catalog.json",
    }


def _placeholder_sech_kabel(
    *,
    entry: dict[str, Any] | None,
    fallback: str,
) -> str:
    if entry and entry.get("label"):
        return format_cable_section_display(str(entry["label"]).strip())
    return format_cable_section_display(fallback)


def apply_wire_selection(
    tu_data: dict[str, Any],
    *,
    wire_selection_mode: str,
    wire_manual_value: str | None,
    logger: Any | None = None,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog = catalog or load_wire_catalog()
    mode = (wire_selection_mode or "auto").strip().lower()
    if mode not in {"auto", "manual"}:
        raise WireSelectionError(f"Неизвестный режим выбора провода: {wire_selection_mode}")

    auto_wire = str(tu_data.get("SECH_KABEL", "") or "").strip()
    manual_wire = str(wire_manual_value or "").strip() or None
    if mode == "auto":
        manual_wire = None

    wire_final_label = resolve_final_wire(auto_wire, manual_wire, mode)
    catalog_key = _resolve_catalog_key(catalog, wire_final_label)

    if mode == "manual":
        if catalog_key is None:
            raise WireSelectionError("Выбранный провод отсутствует в справочнике проводов.")
        entry = catalog["wires"][catalog_key]
        weight_info = get_wire_weight(catalog_key, catalog=catalog, require_weight=True)
        sech_kabel = _placeholder_sech_kabel(entry=entry, fallback=wire_final_label)
    else:
        entry = None
        if catalog_key is not None:
            entry = catalog["wires"][catalog_key]
            sech_kabel = _placeholder_sech_kabel(entry=entry, fallback=auto_wire)
            weight_info = get_wire_weight(catalog_key, catalog=catalog, require_weight=False)
            if weight_info["weight_kg_per_km"] is None:
                weight_info = _legacy_auto_weight(auto_wire)
        else:
            sech_kabel = _placeholder_sech_kabel(entry=None, fallback=auto_wire)
            weight_info = _legacy_auto_weight(auto_wire)

    wire_weight_final = weight_info.get("weight_kg_per_km")
    if mode == "manual" and wire_weight_final is None:
        raise WireSelectionError(
            "Для выбранного провода не задан вес. Заполните вес в справочнике проводов."
        )

    wire_data = {
        "wire_selection_mode": mode,
        "wire_manual_value": manual_wire,
        "wire_auto_detected": auto_wire,
        "wire_final_value": catalog_key or wire_final_label,
        "wire_final_label": entry.get("label", wire_final_label) if catalog_key else wire_final_label,
        "wire_weight_final": wire_weight_final,
        "wire_weight_source": weight_info.get("weight_source"),
        "sech_kabel": sech_kabel,
    }

    tu_data["SECH_KABEL"] = sech_kabel
    tu_data["wire_selection_mode"] = mode
    tu_data["wire_manual_value"] = manual_wire
    tu_data["wire_auto_detected"] = auto_wire
    tu_data["wire_final_value"] = wire_data["wire_final_value"]
    tu_data["wire_weight_final"] = wire_weight_final

    if logger:
        logger.info(f"Автоматически определён провод: {auto_wire or 'не определён'}")
        logger.info(f"Режим выбора провода: {mode}")
        if manual_wire:
            logger.info(f"Провод выбран вручную: {manual_wire}")
        logger.info(f"Итоговый провод проекта: {wire_data['wire_final_label']} ({sech_kabel})")
        if wire_weight_final is not None:
            logger.info(
                f"Итоговый вес провода: {wire_weight_final} кг/км "
                f"(источник: {weight_info.get('weight_source')})"
            )
        else:
            logger.warning("Итоговый вес провода не определён.")

    return wire_data


def _legacy_auto_weight(auto_wire: str) -> dict[str, Any]:
    legacy = {
        "3x70+1x70": (1112.0, "calculator.py — legacy auto 3x70+1x70"),
        "3x50+1x50": (775.0, "calculator.py — legacy auto 3x50+1x50"),
    }
    weight = legacy.get(auto_wire)
    if weight is None:
        return {"weight_kg_per_km": None, "weight_source": None}
    return {"weight_kg_per_km": weight[0], "weight_source": weight[1]}
