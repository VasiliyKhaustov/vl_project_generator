from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedPlotAddress:
    raw: str
    normalized: str
    region: str | None = None
    district: str | None = None
    municipality: str | None = None
    settlement_type: str | None = None
    settlement_name: str | None = None
    garden_partnership: str | None = None
    street: str | None = None
    house_number: str | None = None
    plot_number: str | None = None


def parse_plot_address(address: str) -> ParsedPlotAddress:
    normalized = _normalize_plot_address(address)
    parts = [part.strip() for part in normalized.split(",") if part.strip()]

    region = _find_region(parts)
    district = _find_district(parts)
    municipality = _find_municipality(parts)
    garden_partnership = _find_garden_partnership(parts, normalized)
    settlement_type, settlement_name, house_number = _find_settlement(
        parts,
        garden_partnership is not None,
    )
    street = _find_street(normalized)
    if house_number is None:
        house_number = _find_house_number(normalized)
    plot_number = _find_plot_number(normalized)

    if settlement_name is None and district:
        city_match = re.search(r"(?:город|г\.)\s*(.+)", district, flags=re.IGNORECASE)
        if city_match:
            settlement_type = "город"
            settlement_name = city_match.group(1).strip()

    return ParsedPlotAddress(
        raw=address.strip(),
        normalized=normalized,
        region=region,
        district=district,
        municipality=municipality,
        settlement_type=settlement_type,
        settlement_name=settlement_name,
        garden_partnership=garden_partnership,
        street=street,
        house_number=house_number,
        plot_number=plot_number,
    )


def build_plot_geocode_queries(parsed: ParsedPlotAddress, cadastral_number: str) -> list[str]:
    specific: list[str] = []
    broad: list[str] = []
    region = parsed.region or "Липецкая область"
    district_label = parsed.district or ""
    municipality_label = parsed.municipality or ""

    def add_specific(query: str) -> None:
        cleaned = re.sub(r"\s+", " ", query.strip(" ,"))
        if cleaned:
            specific.append(cleaned)

    def add_broad(query: str) -> None:
        cleaned = re.sub(r"\s+", " ", query.strip(" ,"))
        if cleaned:
            broad.append(cleaned)

    if parsed.garden_partnership:
        settlement_label = _format_settlement_label(parsed.settlement_type, parsed.settlement_name)
        add_specific(f"СНТ {parsed.garden_partnership}, {settlement_label}, {region}, Россия")
        add_specific(f"садовое товарищество {parsed.garden_partnership}, {region}, Россия")
        if parsed.plot_number:
            add_specific(
                f"СНТ {parsed.garden_partnership}, участок {parsed.plot_number}, "
                f"{settlement_label}, {region}, Россия"
            )

    if parsed.settlement_name:
        for settlement_type in _settlement_type_variants(parsed.settlement_type):
            label = _format_settlement_label(settlement_type, parsed.settlement_name)
            add_specific(f"{label}, {district_label}, {region}, Россия")
            if parsed.house_number:
                add_specific(f"{label}, {parsed.house_number}, {region}, Россия")
                add_specific(
                    f"{region}, {district_label}, {label}, {parsed.house_number}, Россия"
                )

    if parsed.street and parsed.plot_number:
        settlement_label = _format_settlement_label(parsed.settlement_type, parsed.settlement_name)
        add_specific(
            f"{region}, {district_label}, {settlement_label}, улица {parsed.street}, "
            f"участок {parsed.plot_number}, Россия"
        )

    if parsed.street and parsed.settlement_name:
        settlement_label = _format_settlement_label(parsed.settlement_type, parsed.settlement_name)
        add_specific(f"улица {parsed.street}, {settlement_label}, {region}, Россия")
        add_specific(f"{region}, {district_label}, {settlement_label}, улица {parsed.street}, Россия")

    if parsed.settlement_name:
        add_broad(f"{parsed.settlement_name}, {district_label}, {region}, Россия")
        if municipality_label:
            add_broad(f"{parsed.settlement_name}, {municipality_label}, {region}, Россия")
        if parsed.house_number:
            add_broad(
                f"{parsed.settlement_name}, {parsed.house_number}, {district_label}, {region}, Россия"
            )

    add_broad(f"{parsed.normalized}, Россия")
    if district_label and not parsed.settlement_name and not parsed.garden_partnership:
        add_broad(f"{district_label}, {region}, Россия")
    if cadastral_number:
        add_broad(f"{parsed.normalized}, кадастровый номер {cadastral_number}")

    return _dedupe_queries(specific + broad)


def build_broad_geocode_queries(parsed: ParsedPlotAddress, cadastral_number: str) -> list[str]:
    region = parsed.region or "Липецкая область"
    district_label = parsed.district or ""
    queries: list[str] = [f"{parsed.normalized}, Россия"]
    if district_label:
        queries.append(f"{district_label}, {region}, Россия")
    if cadastral_number:
        queries.append(f"{parsed.normalized}, кадастровый номер {cadastral_number}")
    return _dedupe_queries(queries)


def build_settlement_only_queries(parsed: ParsedPlotAddress) -> list[str]:
    queries: list[str] = []
    region = parsed.region or "Липецкая область"
    district_label = parsed.district or ""

    if parsed.garden_partnership:
        settlement_label = _format_settlement_label(parsed.settlement_type, parsed.settlement_name)
        queries.append(f"СНТ {parsed.garden_partnership}, {settlement_label}, {region}, Россия")
        queries.append(f"садовое товарищество {parsed.garden_partnership}, {region}, Россия")
        queries.append(f"СНТ {parsed.garden_partnership}, {region}, Россия")

    if parsed.settlement_name:
        for settlement_type in _settlement_type_variants(parsed.settlement_type):
            label = _format_settlement_label(settlement_type, parsed.settlement_name)
            queries.append(f"{label}, {district_label}, {region}, Россия")
            queries.append(f"{label}, {region}, Россия")
        queries.append(f"{parsed.settlement_name}, {district_label}, {region}, Россия")
        queries.append(f"{parsed.settlement_name}, {region}, Россия")

    return _dedupe_queries(queries)


def build_partial_fallback_queries(parsed: ParsedPlotAddress) -> list[str]:
    queries: list[str] = []
    region = parsed.region or "Липецкая область"
    district_label = parsed.district or ""

    if parsed.garden_partnership:
        settlement_label = _format_settlement_label(parsed.settlement_type, parsed.settlement_name)
        queries.append(f"СНТ {parsed.garden_partnership}, {settlement_label}, {region}, Россия")
        queries.append(f"садовое товарищество {parsed.garden_partnership}, {region}, Россия")

    if parsed.street and parsed.settlement_name:
        settlement_label = _format_settlement_label(parsed.settlement_type, parsed.settlement_name)
        queries.append(f"улица {parsed.street}, {settlement_label}, {region}, Россия")

    if parsed.settlement_name:
        for settlement_type in _settlement_type_variants(parsed.settlement_type):
            label = _format_settlement_label(settlement_type, parsed.settlement_name)
            queries.append(f"{label}, {district_label}, {region}, Россия")
        if parsed.house_number:
            queries.append(
                f"село {parsed.settlement_name}, {parsed.house_number}, {region}, Россия"
            )

    return _dedupe_queries(queries)


def _normalize_plot_address(address: str) -> str:
    normalized = re.sub(r"\s+", " ", address.strip())
    normalized = normalized.replace("«", '"').replace("»", '"')
    normalized = re.sub(r"\bст\b", "снт", normalized, flags=re.IGNORECASE)
    normalized = normalized.replace("з.у.", "участок")
    normalized = re.sub(r"ул\.(?=\S)", "улица ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"г\.(?=\S)", "г. ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"с\.(?=\S)", "с. ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"пос\.(?=\S)", "пос. ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\s*"([^"]+)"', r" \1", normalized)
    return re.sub(r"\s+", " ", normalized).strip(" ,")


def _find_region(parts: list[str]) -> str | None:
    for part in parts:
        if re.search(r"область|край|республик", part, flags=re.IGNORECASE):
            return part
    return None


def _find_district(parts: list[str]) -> str | None:
    for part in parts:
        if re.search(r"район|округ", part, flags=re.IGNORECASE):
            return part
        if re.search(r"^(?:город|г\.)\s*", part, flags=re.IGNORECASE):
            return part
    return None


def _find_municipality(parts: list[str]) -> str | None:
    for part in parts:
        if re.search(r"(?:с/п|сельское\s+поселение)\b", part, flags=re.IGNORECASE):
            return part
    return None


def _find_garden_partnership(parts: list[str], normalized: str) -> str | None:
    for part in parts:
        match = re.search(
            r"(?:снт|стн|садовое\s+товарищество)\s+(.+)",
            part,
            flags=re.IGNORECASE,
        )
        if match:
            return _clean_name(match.group(1))
    match = re.search(r"(?:снт|стн)\s+([^,]+)", normalized, flags=re.IGNORECASE)
    if match:
        return _clean_name(match.group(1))
    return None


def _find_settlement(
    parts: list[str],
    has_garden_partnership: bool,
) -> tuple[str | None, str | None, str | None]:
    for part in parts:
        if re.search(r"(?:снт|стн|садовое\s+товарищество)\b", part, flags=re.IGNORECASE):
            continue
        if re.search(r"(?:с/п|сельское\s+поселение)\b", part, flags=re.IGNORECASE):
            continue
        if re.search(r"район|округ|область", part, flags=re.IGNORECASE):
            continue

        for pattern, settlement_type in (
            (r"(?:город|г\.)\s*(.+)", "город"),
            (r"(?:село|с\.)\s+(.+)", "село"),
            (r"(?:посёлок|поселок|пос\.|п\.)\s+(.+)", "посёлок"),
            (r"(?:деревня|дер\.)\s+(.+)", "деревня"),
            (r"(?:хутор|х\.)\s+(.+)", "хутор"),
            (r"(?:пгт|п\.г\.т\.)\s+(.+)", "посёлок"),
        ):
            match = re.search(pattern, part, flags=re.IGNORECASE)
            if match:
                name, house_number = _split_settlement_and_house(match.group(1))
                return settlement_type, name, house_number

        if not re.search(r"улица|участок", part, flags=re.IGNORECASE):
            settlement_name, house_number = _split_settlement_and_house(part)
            return "населённый пункт", settlement_name, house_number

    if has_garden_partnership:
        for part in parts:
            city_match = re.search(r"(?:город|г\.)\s*(.+)", part, flags=re.IGNORECASE)
            if city_match:
                return "город", _clean_name(city_match.group(1)), None
    return None, None, None


def _split_settlement_and_house(part: str) -> tuple[str, str | None]:
    house_match = re.match(
        r"^([А-Яа-яЁё][А-Яа-яЁё\-\s]*?)\s+(\d+\s*[а-яa-zА-Я]?)$",
        part.strip(),
        flags=re.IGNORECASE,
    )
    if house_match:
        return _clean_name(house_match.group(1)), _clean_name(house_match.group(2))
    return _clean_name(part), None


def _find_street(normalized: str) -> str | None:
    match = re.search(r"улица\s+([^,]+)", normalized, flags=re.IGNORECASE)
    if match:
        return _clean_name(match.group(1))
    return None


def _find_house_number(normalized: str) -> str | None:
    match = re.search(
        r"(?:дом|д\.)\s*(\d+\s*[а-яa-zА-Я]?)",
        normalized,
        flags=re.IGNORECASE,
    )
    if match:
        return _clean_name(match.group(1))
    return None


def _find_plot_number(normalized: str) -> str | None:
    match = re.search(r"участок\s*(?:№\s*)?(\d+)", normalized, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _settlement_type_variants(settlement_type: str | None) -> tuple[str, ...]:
    if settlement_type == "город":
        return ("город",)
    if settlement_type == "село":
        return ("село",)
    if settlement_type == "посёлок":
        return ("посёлок",)
    if settlement_type == "деревня":
        return ("деревня",)
    if settlement_type == "хутор":
        return ("хутор",)
    return ("село", "деревня", "посёлок")


def _format_settlement_label(settlement_type: str | None, settlement_name: str | None) -> str:
    if not settlement_name:
        return ""
    if settlement_type == "город":
        return f"город {settlement_name}"
    if settlement_type == "село":
        return f"село {settlement_name}"
    if settlement_type == "посёлок":
        return f"посёлок {settlement_name}"
    if settlement_type == "деревня":
        return f"деревня {settlement_name}"
    if settlement_type == "хутор":
        return f"хутор {settlement_name}"
    return settlement_name


def _clean_name(value: str) -> str:
    return value.strip().strip('"').strip("№").strip()


def _dedupe_queries(queries: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        key = query.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(query)
    return deduped
