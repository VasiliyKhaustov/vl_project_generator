from __future__ import annotations

SIP4_WEIGHT_KG_PER_KM = {
    "4х16": 269.0,
    "2х16": 134.0,
}
SIP4_SPEC_TABLE_KM = 0.002


def format_cable_section_display(value: str) -> str:
    """Формат сечения для записки: 3х70+1х70, 4х16."""
    text = str(value or "").strip()
    return (
        text.replace("*", "х")
        .replace("x", "х")
        .replace("X", "х")
        .replace("Х", "х")
    )


def normalize_sip4_section(value: str) -> str:
    return format_cable_section_display(value).lower()


def sip4_weight_per_km(sech_sip4: str) -> float | None:
    return SIP4_WEIGHT_KG_PER_KM.get(normalize_sip4_section(sech_sip4))


def calculate_sip4_kg(sech_sip4: str, line_length_km: float) -> float | None:
    factor = sip4_weight_per_km(sech_sip4)
    if factor is None:
        return None
    return line_length_km * factor


def calculate_sip4_spec_table_kg(sech_sip4: str) -> float | None:
    factor = sip4_weight_per_km(sech_sip4)
    if factor is None:
        return None
    return round(SIP4_SPEC_TABLE_KM * factor, 1)


def format_sip4_spec_table_kg(sech_sip4: str) -> str:
    value = calculate_sip4_spec_table_kg(sech_sip4)
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return f"{float(value):.1f}"
