#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.cad.oda_dwg_adapter import (  # noqa: E402
    convert_dwg_plan_to_dxf_with_oda,
    replace_placeholders_in_dwg_with_oda,
)
from backend.core.calculator import calculate_materials  # noqa: E402
from backend.core.calculator_10kv import calculate_materials_10kv  # noqa: E402
from backend.core.dxf_reader import analyze_dxf  # noqa: E402
from backend.core.output_manager import OutputManager  # noqa: E402
from backend.core.plan_reader_10kv import read_plan_10kv_data  # noqa: E402
from backend.core.project_type import is_10kv_project, resolve_project_is_10kv  # noqa: E402
from backend.core.replacement_builder_10kv import build_replacement_map_10kv, filter_cad_result_10kv  # noqa: E402
from backend.core.template_selector_10kv import select_template_note_path_10kv  # noqa: E402
from backend.core.tu_parser import parse_tu, read_tu_text  # noqa: E402
from backend.core.tu_parser_10kv import enrich_tu_data_10kv  # noqa: E402
from backend.core.wire_resolver import apply_wire_selection  # noqa: E402


def main() -> int:
    tu_path = Path(sys.argv[1]).resolve()
    plan_path = Path(sys.argv[2]).resolve()
    project_number = sys.argv[3] if len(sys.argv) > 3 else "ПСД/48/2026/001"
    branch_pole_type = sys.argv[4] if len(sys.argv) > 4 else "intermediate"

    output = OutputManager(PROJECT_ROOT)
    output.prepare()
    logger = output.logger()
    output.cleanup_stale_10kv_artifacts()

    logger.info(f"ТУ: {tu_path}")
    logger.info(f"План: {plan_path}")
    logger.info(f"Номер проекта: {project_number}")
    logger.info(f"Тип ответвления: {branch_pole_type}")

    tu_data, tu_warnings = parse_tu(tu_path)
    is_10kv = is_10kv_project(read_tu_text(tu_path))
    logger.info(f"Проект 10 кВ: {is_10kv}")
    if not is_10kv:
        logger.error("ТУ не определено как проект 10 кВ.")
        return 1

    tu_data, tu_10kv_warnings = enrich_tu_data_10kv(tu_path, tu_data)
    wire_data = apply_wire_selection(tu_data, wire_selection_mode="auto", wire_manual_value=None, logger=logger)

    plan_dxf_path = convert_dwg_plan_to_dxf_with_oda(
        plan_path,
        output.temp_dir / "uploaded_plan_converted.dxf",
        output.output_root,
        logger=logger,
    )
    plan_data, plan_warnings = analyze_dxf(plan_dxf_path)
    plan_10kv_data, plan_10kv_warnings = read_plan_10kv_data(plan_dxf_path)
    plan_data = {**plan_data, **plan_10kv_data}

    materials_data = calculate_materials(tu_data, plan_data)
    materials_10kv = calculate_materials_10kv(
        tu_data,
        plan_data,
        branch_pole_type=branch_pole_type,
    )
    template_path, template_warning = select_template_note_path_10kv(
        PROJECT_ROOT / "examples" / "templates",
        plan_data,
        logger,
    )
    replacement_map = build_replacement_map_10kv(
        project_number,
        tu_data,
        materials_data,
        materials_10kv,
    )

    output.write_json("tu_data.json", tu_data)
    output.write_json("plan_data.json", plan_data)
    output.write_json("materials_data.json", materials_data)
    output.write_json("materials_10kv_data.json", materials_10kv)
    output.write_json("replacement_map.json", replacement_map)
    output.write_json(
        "project_data.json",
        {
            "project_number": project_number,
            "project_type": "10kv",
            "branch_pole_type": branch_pole_type,
            "template_note": template_path.name,
        },
    )

    note_path = output.dwg_dir / "note_result.dwg"
    for stale_name in ("note_result.dxf", "note_result_filled.dxf"):
        stale_path = output.dwg_dir / stale_name
        if stale_path.exists():
            stale_path.unlink()
    cad_result = replace_placeholders_in_dwg_with_oda(
        template_path,
        note_path,
        replacement_map,
        output.output_root,
        logger=logger,
        use_10kv_strict_dxf=True,
    )
    cad_result = filter_cad_result_10kv(cad_result)
    named_outputs = output.copy_note_result_for_project(project_number)
    for label, path in named_outputs.items():
        if path is not None:
            logger.info(f"10 кВ: {label}: {path.name}")

    summary = {
        "project_number": project_number,
        "branch_pole_type": branch_pole_type,
        "template": str(template_path),
        "note_result": str(note_path),
        "note_result_named": {
            key: str(value) for key, value in named_outputs.items() if value is not None
        },
        "note_result_dxf": None,
        "cad_warnings": cad_result.get("warnings", []),
        "tu_warnings": tu_warnings + tu_10kv_warnings,
        "plan_warnings": plan_warnings + plan_10kv_warnings,
        "template_warning": template_warning,
        "wire": wire_data,
        "supports_04": plan_data.get("supports"),
        "supports_10kv": plan_data.get("supports_10kv"),
        "line_length_10kv_m": plan_data.get("line_length_10kv_m"),
        "tu_10kv_fields": {
            key: tu_data.get(key)
            for key in (
                "PS_NAME",
                "6-10",
                "OTKUDASTROIT_10kV",
                "OTKUDA_STROIT_10kV",
                "SECH_KABEL_10kV",
                "MOSH",
            )
        },
        "materials_10kv_sample": {
            key: materials_10kv.get(key)
            for key in ("YOPK", "P20", "A20", "ARLK", "UA", "UP", "KM_10", "SQUARE_10kV", "NOM", "MOSH")
        },
        "unresolved_placeholders": cad_result.get("unresolved_placeholders", []),
        "output_dir": str(output.output_root),
    }
    summary_path = output.write_json("run_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nSummary: {summary_path}")
    print(f"Note DWG: {note_path}")
    for label, path in named_outputs.items():
        if path is not None:
            print(f"Копия ({label}): {path}")
    if cad_result.get("warnings"):
        for warning in cad_result["warnings"]:
            print(f"Warning: {warning}")
    print(f"Log: {output.logs_dir / 'log.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
