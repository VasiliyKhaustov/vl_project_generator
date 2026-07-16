from __future__ import annotations

from typing import Any

from backend.cad.oda_dwg_adapter import canonical_placeholder_key

IGNORED_UNRESOLVED_10KV = frozenset(
    {
        "{{OTKUDASTROIT}}",
        "{{OTUDASTROIT}}",
        "{{TP_NAME}}",
        "{{TO_NAME}}",
        "{{вертикальный}}",
        "{{горизонтальный}}",
    }
)

IGNORED_TU_WARNING_FIELDS = frozenset({"OTKUDASTROIT", "TP_NAME"})


def filter_unresolved_placeholders_10kv(placeholders: list[str]) -> list[str]:
    return [item for item in placeholders if item not in IGNORED_UNRESOLVED_10KV]


def filter_tu_warnings_10kv(warnings: list[str]) -> list[str]:
    filtered: list[str] = []
    for warning in warnings:
        if any(field in warning for field in IGNORED_TU_WARNING_FIELDS):
            continue
        filtered.append(warning)
    return filtered


def template_placeholder_warning_10kv(
    template_path: Any,
    plan_data: dict[str, Any],
    template_placeholders: list[str],
) -> str | None:
    supports = plan_data.get("supports", {})
    expected: set[str] = set()
    if int(supports.get("P23") or 0) > 0:
        expected.update({"{{P23}}", "{{P23_1}}", "{{ES15}}"})
    if int(supports.get("A23") or 0) > 0:
        expected.update({"{{A23}}", "{{A231}}", "{{Y4}}"})
    if int(supports.get("YA23") or 0) > 0:
        expected.update({"{{YA23}}", "{{YA231}}", "{{X89}}"})
    if int(supports.get("K21") or 0) > 0:
        expected.update({"{{K21}}", "{{K21_1}}"})

    missing = sorted(expected - _normalized_placeholder_set(template_placeholders))
    if not missing:
        return None
    return (
        f"Шаблон {template_path.name} не содержит placeholders: {', '.join(missing)}. "
        "Проверьте эталонный DWG."
    )


def _normalized_placeholder_set(placeholders: list[str]) -> set[str]:
    normalized: set[str] = set()
    for placeholder in placeholders:
        if placeholder.startswith("{{") and placeholder.endswith("}}"):
            key = canonical_placeholder_key(placeholder[2:-2])
            if key:
                normalized.add(key)
                continue
        normalized.add(placeholder)
    return normalized
