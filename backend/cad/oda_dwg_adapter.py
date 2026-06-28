from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import ezdxf

from backend.core.cable_format import format_sip4_spec_table_kg
from backend.core.file_utils import copy_file_with_retry
from backend.core.tu_parser import abbreviate_address_display_terms

from .oda_converter import OdaConverter


PLACEHOLDER_RE = re.compile(r"\{{1,2}[A-Z0-9_]+\}{1,2}")

LEFT_ALIGNED_BODY_MARKERS = (
    "1.   Исходные данные",
    "ОБЩИЕ УКАЗАНИЯ",
    "Проектом технологического присоединения",
    "2.   Электротехнические",
    "3.   Строительные решения",
    "4.   Охрана окружающей",
)

CENTERED_BODY_MARKERS = (
    "1.   Исходные данные",
    "ОБЩИЕ УКАЗАНИЯ",
)

CENTERED_SECTION_HEADINGS = (
    "Исходные данные",
    "ОБЩИЕ УКАЗАНИЯ",
    "Электротехнические решения",
    "Строительные решения",
    "Охрана окружающей",
)

BODY_PARAGRAPH_LEFT_ALIGN_MARKERS = (
    "Проектом технологического присоединения предусматривается",
    "Построить ВЛИ",
    "установить однофазный",
    "установить трехфазный",
    "установить трёхфазный",
    "Принятые марки",
    "По степени надежности",
    "Воздушные линии",
    "Ответвление к коробке",
    "Для защиты ВЛИ",
    "Грозозащитное заземление",
    "Общее сопротивление",
    "В проекте выполнены",
    "В проекте  выполнены",
    "выбор сечения",
    "проверка по условиям",
    "Выполненные расчеты",
    "Расстояние от ВЛИ",
    "На основании уточненных",
    "Температура воздуха",
    "Грунты -",
    "Типы и места установки",
    "Расстановка промежуточных опор",
    "Длины пролетов",
    "Заземляющие устройства",
    "Технические  характеристики",
    "Технические характеристики",
    "Проектируемый объект",
    "Указанный технологический процесс",
    "Производственный шум",
    "В связи с этим",
    "Размеры обособленных земельных участков",
    "При выборе оптимального варианта",
    "Трасса выбрана",
    "Затраты на покрытие убытков",
    "Район прохождения трассы",
    "Проектируемый объект находится",
    "Земельная площадь",
)

CLIMATE_TABLE_SHIFT_Y = -34.0
CLIMATE_TABLE_FINE_SHIFT_Y = -8.0
TITLE_PAGE_YEAR_PARAGRAPH_GAPS = 2
REFERENCE_DOCS_TABLE_SHIFT_Y = -4.0
BODY_TEXT_HEIGHT = 3.0
BREAKER_TEXT_HEIGHT = 2.0
STAMP_TITLE_TEXT_HEIGHT = 2.1
CELL_TEXT_HEIGHT_OVERRIDE_BIT = 0x40000
LONG_SPEC_TEXT_HEIGHT = 3.0
MIN_WORK_TABLE_ROW_HEIGHT = 8.0
BODY_LINE_SPACING = 1.5
GENERAL_NOTES_LINE_SPACING = 1.0
BODY_EMPTY_PARAGRAPH_NEXT_MARKERS = (
    "Доставка материалов",
    "При выборе оптимального",
)
TOC_ELECTRO_ITEM_PLAIN = "2. Электротехнические решения"
TOC_ALIGNMENT_REFERENCE_ITEMS = (
    "1. Исходные данные",
    "3. Строительные решения",
)

CENTERED_HEADING_PLAIN_MARKERS = (
    "ОБЩИЕ УКАЗАНИЯ",
    "1.   Исходные данные",
    "Исходные данные",
    "2.   Электротехнические",
    "Электротехнические  решения",
    "Электротехнические решения",
    "3.   Строительные решения",
    "Строительные решения",
    "4.   Охрана окружающей среды",
    "Охрана окружающей среды",
    "Противопожарные мероприятия и пожарная защита",
    "Организация строительства",
)

ROUTE_PLAN_SHEET_LABEL = "План трассы ВЛИ-0,4 кВ"
STAMP_BLOCK_NAMES = frozenset({"Штамп б"})
STAMP_TOTAL_SHEETS_OFFSET = (194.0, 18.5)
STAMP_FIELD_TOLERANCE = (6.0, 1.5)
ZP6_TABLE_LABEL = "ЗП6"
SIP4_TABLE_ROW_MARKERS = ("31946", "СИП4")
SIP4_SPEC_TABLE_KM_DISPLAY = "0,002"
SIP4_NUMERIC_WIDTH_FACTOR = 0.9
SPEC_CERTIFICATE_TEXT_HEIGHT = 2.0
SPEC_CERTIFICATE_TEXT_PATTERN = re.compile(r"[IИ][ЗZ]-\d+/\d+", re.IGNORECASE)
SPEC_CERTIFICATE_PPD_PATTERN = re.compile(r"(?:ППД|IIПД)-\d+/\d+", re.IGNORECASE)
SPEC_CERTIFICATE_DATE_PATTERN = re.compile(r"\d{2}\.\d{2}\.\d{4}")
EQUIPMENT_FOOTNOTE_MARKER = "Все применяемое оборудование"

TITLE_PAGE_MARKERS = (
    "ПРОЕКТНАЯ ДОКУМЕНТАЦИЯ",
    "УПРАВЛЕНИЕ ТЕХНОЛОГИЧЕСКОГО",
    "Раздел 3 «",
    "Раздел 1 «",
    "Раздел 2 «",
)

LEFT_ALIGNED_INTRO_MARKERS = (
    'Проект "',
    "{\\A1;Проект }",
    "{\\A1;Проект}{",
    "Технические решения, принятые в комплекте",
    "Технические решения принятые в данном",
    "{\\A1;Технические решения}",
    "Проектом технологического присоединения предусматривается",
)
SPEC_TABLE_MARKERS = (
    "Спец.ВЛ-0.4кВ",
    "П23",
    "К21",
    "СВ110-5",
    "CD35",
    "E778",
    "Сталь круглая",
    "Прокат стальной",
    "Электрооборудование",
    "Заземление",
    "ГОСТ 31946-2012",
)
NUMERIC_RESULT_TEXT_FIELDS = (
    "LINE_LENGTH_KM",
    "P23",
    "A23",
    "YA23",
    "K21",
    "GROUND",
    "P23_1",
    "A231",
    "YA231",
    "K21_1",
    "S1",
    "SECH_KM",
    "SECH_KG",
    "SIP4_KG",
    "CD35",
    "GR",
)
STAMP_SIGNATURE_TARGET_Y = {
    "Разработал": -1.0,
    "Проверил": -6.2,
    "Н.контроль": -15.5,
    "Хаустов": -1.0,
}
STAMP_SURINOV_TOP_Y_THRESHOLD = -12.0
STAMP_SURINOV_TOP_TARGET_Y = -6.2
STAMP_SURINOV_BOTTOM_TARGET_Y = -15.5

CLIMATE_TABLE_LABELS = (
    "Район по гололеду",
    "Нормативная толщина стенки гололеда",
    "Район по ветру",
    "Нормативная скорость ветра",
    "Ветровое давление",
    "Среднегодовая продолжительность гроз",
)
CLIMATE_TABLE_ROW_REPLACEMENTS = (
    ("Район по гололеду", "roman", "ice_district"),
    ("Нормативная толщина стенки гололеда", "number", "ice_thickness"),
    ("Район по ветру", "roman", "wind_district"),
    ("Нормативная скорость ветра", "number", "wind_speed"),
    ("Ветровое давление", "number", "wind_pressure"),
)

WORK_TABLE_SUPPORT_MARKERS = {
    "П23": "{{P23}}",
    "П 23": "{{P23}}",
    "УП23": "{{P23}}",
    "А23": "{{A23}}",
    "А 23": "{{A23}}",
    "К21": "{{K21}}",
    "К 21": "{{K21}}",
    "УА23": "{{YA23}}",
    "УА23*": "{{YA23}}",
    "УА 23": "{{YA23}}",
}
WORK_TABLE_SUPPORT_NAME_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"промежуточн|25\.0017-02", re.IGNORECASE), "P23"),
    (re.compile(r"угловая\s+анкерная|21\.0112-09", re.IGNORECASE), "YA23"),
    (re.compile(r"концевая|21\.0112-04", re.IGNORECASE), "K21"),
    (re.compile(r"(?<!\w)анкерная|25\.0017-08", re.IGNORECASE), "A23"),
    (re.compile(r"угловая|25\.0017-06", re.IGNORECASE), "P23"),
)
WORK_TABLE_SUPPORT_TYPE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"УА23\*?|YA23", re.IGNORECASE), "YA23"),
    (re.compile(r"УП23|UP23", re.IGNORECASE), "P23"),
    (re.compile(r"К21|K21", re.IGNORECASE), "K21"),
    (re.compile(r"А23|A23", re.IGNORECASE), "A23"),
    (re.compile(r"П23|P23", re.IGNORECASE), "P23"),
)
WORK_TABLE_QUANTITY_COLUMN_INDEX = 4
WORK_TABLE_MARKERS = (
    "Строительная длина линии",
    "Установка ж.б.опоры",
    "Монтаж ответвительной",
    "Монтаж самонесущего",
    "Монтаж заземляющего",
    "Монтаж счетчика",
    "Монтаж выключателя",
    "Монтаж щита",
    "Монтаж проката",
    "Состав электротехнических измерений",
    "Автоматизированная система управления II категории",
    "Опора железобетонная",
    "Провода и кабели",
    "Стальные конструкции",
    "Линейная арматура",
)


def replace_placeholders_in_dwg_with_oda(
    template_dwg_path: Path,
    output_dwg_path: Path,
    replacement_map: dict[str, str],
    work_dir: Path,
    logger: Any | None = None,
) -> dict[str, Any]:
    template_dwg_path = Path(template_dwg_path)
    output_dwg_path = Path(output_dwg_path)
    work_dir = Path(work_dir)
    temp_dir = work_dir / "temp"
    oda_temp_dir = temp_dir / "oda_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dwg_path.parent.mkdir(parents=True, exist_ok=True)

    converter = OdaConverter(project_root=_project_root(), logger=logger)
    temp_dwg = temp_dir / "template_temp.dwg"
    template_dxf = temp_dir / "template_temp.dxf"
    filled_dxf = temp_dir / "filled_temp.dxf"

    if logger:
        logger.info("Начинаю заполнение DWG-записки через ODA...")
    copy_file_with_retry(template_dwg_path, temp_dwg, logger=logger)
    if logger:
        logger.info("Копия шаблона DWG подготовлена. Конвертирую в DXF через ODA...")
    converter.convert_file(
        temp_dwg,
        template_dxf,
        output_format="DXF",
        work_dir=oda_temp_dir / "template_to_dxf",
        output_version="ACAD2013",
    )
    template_placeholders = _find_placeholders_in_dxf(template_dxf)

    replaced_count = _replace_placeholders_in_dxf(template_dxf, filled_dxf, replacement_map, logger)
    if logger:
        logger.info("DXF обработан. Конвертирую обратно в DWG через ODA...")
    converter.convert_file(
        filled_dxf,
        output_dwg_path,
        output_format="DWG",
        work_dir=oda_temp_dir / "filled_to_dwg",
        output_version="ACAD2018",
    )

    unresolved = _find_placeholders_in_dxf(filled_dxf)

    warnings: list[str] = []
    if unresolved:
        warning = "Часть placeholders не заменена: " + ", ".join(unresolved)
        warnings.append(warning)
        if logger:
            logger.warning(warning)

    return {
        "success": True,
        "mode": "oda",
        "output_dwg_path": str(output_dwg_path),
        "replaced_count": replaced_count,
        "template_placeholders": template_placeholders,
        "unresolved_placeholders": unresolved,
        "warnings": warnings,
    }


def convert_dwg_plan_to_dxf_with_oda(
    plan_dwg_path: Path,
    output_dxf_path: Path,
    work_dir: Path,
    logger: Any | None = None,
) -> Path:
    return convert_dwg_to_dxf_with_oda(plan_dwg_path, output_dxf_path, work_dir, logger)


def convert_dwg_to_dxf_with_oda(
    source_dwg_path: Path,
    output_dxf_path: Path,
    work_dir: Path,
    logger: Any | None = None,
) -> Path:
    converter = OdaConverter(project_root=_project_root(), logger=logger)
    return converter.convert_file(
        Path(source_dwg_path),
        Path(output_dxf_path),
        output_format="DXF",
        work_dir=Path(work_dir) / "temp" / f"oda_{Path(source_dwg_path).stem}_to_dxf",
        output_version="ACAD2013",
    )


def find_placeholders_in_dwg_file(
    source_path: Path,
    work_dir: Path,
    logger: Any | None = None,
) -> list[str]:
    source_path = Path(source_path)
    work_dir = Path(work_dir)
    if source_path.suffix.lower() == ".dxf":
        return _find_placeholders_in_dxf(source_path)
    dxf_path = work_dir / "temp" / f"{source_path.stem}_placeholders.dxf"
    dxf_path.parent.mkdir(parents=True, exist_ok=True)
    convert_dwg_to_dxf_with_oda(source_path, dxf_path, work_dir, logger=logger)
    return _find_placeholders_in_dxf(dxf_path)


def extract_text_from_dwg_file(
    source_path: Path,
    work_dir: Path,
    logger: Any | None = None,
) -> str:
    from backend.core.note_validator import collect_plain_corpus, load_note_document

    document = load_note_document(Path(source_path), Path(work_dir))
    return collect_plain_corpus(document)


def _replace_placeholders_in_dxf(
    source_dxf: Path,
    output_dxf: Path,
    replacement_map: dict[str, str],
    logger: Any | None = None,
) -> int:
    document = ezdxf.readfile(source_dxf)
    replaced_count = 0

    for entity in _iter_text_entities(document):
        text = _get_text(entity)
        if not text:
            continue
        replaced_text, count = _replace_text(text, replacement_map)
        cleaned_text = _cleanup_generated_text(replaced_text, replacement_map)
        if entity.dxftype() == "MTEXT":
            cleaned_text = _repair_mtext_format_garbage(cleaned_text)
            formatted_text = _format_mtext_alignment(cleaned_text)
            if formatted_text != cleaned_text:
                cleaned_text = formatted_text
            if _is_title_page_mtext(cleaned_text):
                cleaned_text = _position_title_page_year_text(cleaned_text)
            if _is_body_note_mtext(cleaned_text):
                _fit_body_note_mtext(entity, cleaned_text)
                cleaned_text = _normalize_body_note_inline_heights(cleaned_text)
            _fit_long_table_mtext(entity, cleaned_text)
            _fit_volume_table_mtext(entity, cleaned_text)
            if entity.dxftype() == "MTEXT" and _is_stamp_title_mtext(entity.plain_text()):
                cleaned_text = _fit_stamp_title_mtext(entity, cleaned_text)
            elif _is_breaker_mtext_text(cleaned_text):
                cleaned_text = _fit_breaker_mtext(entity, cleaned_text)
            elif _is_spec_table_quantity_text(cleaned_text) or _is_numeric_result_text(cleaned_text, replacement_map):
                cleaned_text = _fit_spec_table_quantity_mtext(entity, cleaned_text)
                _fit_numeric_result_mtext(entity, cleaned_text, replacement_map)
            elif _is_equipment_footnote_mtext(cleaned_text):
                cleaned_text = _format_equipment_footnote_text(cleaned_text)
        if count or cleaned_text != text:
            _set_text(entity, cleaned_text)
            replaced_count += count

    _move_climate_table_down(document)
    _move_reference_docs_table_down(document)
    _raise_stamp_signature_text(document)
    _update_sheet_count_entities(document, replacement_map)
    _fit_table_block_mtext_entities(document)
    _fit_stamp_title_mtext_entities(document)
    _fix_work_table_support_quantities(document, replacement_map)
    _fix_climate_table_mtext_values(document, replacement_map)
    _fix_supports_install_note_entities(document, replacement_map)
    _fix_toc_electro_item_alignment_entities(document)
    _left_align_equipment_footnote_entities(document)

    document.saveas(output_dxf)
    _repair_mtext_continuation_group_codes_file(output_dxf)
    _move_climate_table_down_raw(output_dxf)
    _move_reference_docs_table_down_raw(output_dxf)
    replaced_count += _replace_placeholders_in_raw_dxf(output_dxf, replacement_map)
    _fix_project_indicator_table_values(output_dxf, replacement_map)
    _apply_sheet_count_replacements_raw(output_dxf, replacement_map)
    _fix_work_table_support_quantities_raw(output_dxf, replacement_map)
    _fix_climate_table_mtext_values_raw(output_dxf, replacement_map)
    _fix_supports_install_note_raw(output_dxf, replacement_map)
    _fix_branch_armature_line_raw(output_dxf, replacement_map)
    _adjust_stamp_signature_positions_raw(output_dxf)
    _fix_labeled_spec_table_values_raw(output_dxf, replacement_map)
    _fix_sip4_spec_table_values_raw(output_dxf, replacement_map)
    _apply_phase_breaker_replacements_raw(output_dxf, replacement_map)
    _cleanup_raw_dxf_text(output_dxf, replacement_map)
    _fix_sip4_numeric_width_raw(output_dxf, replacement_map)
    _fix_spec_certificate_text_heights_raw(output_dxf)
    _fix_toc_electro_item_alignment_raw(output_dxf)
    _left_align_equipment_footnote_raw(output_dxf)
    _fix_toc_electro_item_alignment_raw(output_dxf)
    if logger:
        logger.info(f"DXF placeholders replaced: {replaced_count}")
    return replaced_count


def _find_placeholders_in_dxf(path: Path) -> list[str]:
    document = ezdxf.readfile(path)
    found: set[str] = set()
    for entity in _iter_text_entities(document):
        text = _normalize_escaped_braces(_get_text(entity))
        found.update(
            placeholder
            for value in PLACEHOLDER_RE.findall(text)
            if (placeholder := _canonical_placeholder(value))
        )
    return sorted(found)


def _replace_text(text: str, replacement_map: dict[str, str]) -> tuple[str, int]:
    result = text
    count = 0
    result, sequence_count = _replace_commutator_template_sequence(result, replacement_map)
    count += sequence_count
    for placeholder, value in replacement_map.items():
        field_name = _placeholder_name(placeholder)
        if not field_name:
            continue
        result, occurrences = _replace_placeholder_name(result, field_name, value)
        count += occurrences
    result, hardcode_count = _replace_route_distance_km_hardcode(result, replacement_map)
    count += hardcode_count
    return result, count


ROUTE_DISTANCE_KM_PATTERN = re.compile(
    r"(составляет(?:\s|\}\{[^}]*;)*)(?:\{\{ROUTE_DISTANCE_KM\}\}|23)(\s*км)",
    re.IGNORECASE,
)


def _replace_route_distance_km_hardcode(text: str, replacement_map: dict[str, str]) -> tuple[str, int]:
    distance_km = replacement_map.get("{{ROUTE_DISTANCE_KM}}", "").strip()
    if not distance_km:
        return text, 0
    return ROUTE_DISTANCE_KM_PATTERN.subn(rf"\g<1>{distance_km}\2", text)


def _replace_commutator_template_sequence(text: str, replacement_map: dict[str, str]) -> tuple[str, int]:
    build_from = replacement_map.get("{{OTKUDASTROIT}}") or replacement_map.get("{{OTUDASTROIT}}") or ""
    if "коммутационного аппарата" not in build_from.lower():
        return text, 0

    otkuda = _placeholder_token_pattern("OTKUDASTROIT")
    otuda = _placeholder_token_pattern("OTUDASTROIT")
    tp_name = _placeholder_token_pattern("TP_NAME")
    to_name = _placeholder_token_pattern("TO_NAME")
    endpoint = r"\s*кВА\s+до\s+границы\s+участка\s+Заявителя"
    pattern = re.compile(rf"(?:{otkuda}|{otuda})\s*(?:{tp_name}|{to_name}){endpoint}", re.IGNORECASE)
    return pattern.subn(build_from, text)


def _placeholder_token_pattern(field_name: str) -> str:
    brace = r"(?:\\\{|\{)"
    close_brace = r"(?:\\\}|\})"
    return rf"{brace}{{1,2}}{re.escape(field_name)}{close_brace}{{1,2}}"


def _replace_placeholders_in_raw_dxf(path: Path, replacement_map: dict[str, str]) -> int:
    original_text = path.read_text(encoding="utf-8", errors="replace")
    text = original_text
    replaced_text, count = _replace_text(text, replacement_map)
    if count:
        path.write_text(replaced_text, encoding="utf-8")
    return count


def _apply_phase_breaker_replacements_raw(path: Path, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return
    original_text = path.read_text(encoding="utf-8", errors="replace")
    updated = _apply_calculated_literal_replacements_acad_table_raw(original_text, replacement_map)
    updated = _apply_calculated_literal_replacements_block_mtext_raw(updated, replacement_map)
    updated = _apply_calculated_literal_replacements_table_group_codes_raw(updated, replacement_map)
    if updated != original_text:
        path.write_text(updated, encoding="utf-8")


def _table_group_code_needs_phase_breaker_replacement(value: str) -> bool:
    lowered = value.lower()
    return (
        "полюс" in lowered
        or "ва47-29" in lowered
        or "вa47-29" in lowered
    )


def _apply_calculated_literal_replacements_table_group_codes_raw(
    text: str,
    replacement_map: dict[str, str] | None,
) -> str:
    if not replacement_map:
        return text

    lines = text.splitlines()
    changed = False
    index = 0
    while index < len(lines) - 1:
        code = lines[index].strip()
        if code not in {"1", "3", "302"}:
            index += 1
            continue
        value = lines[index + 1]
        if not _table_group_code_needs_phase_breaker_replacement(value):
            index += 2
            continue
        cleaned = _apply_calculated_literal_replacements(value, replacement_map)
        cleaned = _strip_table_inline_scales(cleaned)
        if cleaned != value:
            lines[index + 1] = cleaned
            changed = True
        index += 2

    if not changed:
        return text
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + suffix


def _cleanup_raw_dxf_text(path: Path, replacement_map: dict[str, str] | None = None) -> bool:
    original_text = path.read_text(encoding="utf-8", errors="replace")
    text = original_text
    cleaned_text = _apply_generated_text_cleanup_to_mtext_raw(text, replacement_map)
    cleaned_text = _apply_calculated_literal_replacements_acad_table_raw(cleaned_text, replacement_map)
    cleaned_text = _apply_calculated_literal_replacements_block_mtext_raw(cleaned_text, replacement_map)
    cleaned_text = _apply_calculated_literal_replacements_table_group_codes_raw(cleaned_text, replacement_map)
    cleaned_text = _repair_mtext_continuation_group_codes_raw(cleaned_text)
    cleaned_text = _position_title_page_year_text_raw(cleaned_text)
    cleaned_text = _apply_mtext_entity_fixes_raw(cleaned_text)
    cleaned_text = _normalize_body_note_heights_raw(cleaned_text)
    cleaned_text = _fit_specification_long_text_raw(cleaned_text)
    cleaned_text = _set_work_table_row_heights_raw(cleaned_text)
    cleaned_text = _strip_table_cell_inline_scales_raw(cleaned_text)
    cleaned_text = _normalize_table_style_heights_raw(cleaned_text)
    cleaned_text = _normalize_numeric_table_cell_heights_raw(cleaned_text)
    cleaned_text = _normalize_spec_table_quantity_heights_raw(cleaned_text)
    cleaned_text = _normalize_stamp_title_heights_raw(cleaned_text)
    cleaned_text = _normalize_breaker_text_heights_raw(cleaned_text)
    cleaned_text = _normalize_numeric_result_mtext_heights_raw(cleaned_text, replacement_map)
    if replacement_map:
        cleaned_text = _apply_climate_replacements_raw(cleaned_text, replacement_map)
    if cleaned_text != text:
        path.write_text(cleaned_text, encoding="utf-8")
        return True
    return False


def _apply_generated_text_cleanup_to_mtext_raw(
    text: str,
    replacement_map: dict[str, str] | None = None,
) -> str:
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_object(match: re.Match[str]) -> str:
        object_text = match.group(1)
        pairs, tail = _split_object_pairs(object_text)
        changed = False
        for pair in pairs:
            if pair[0].strip() not in {"1", "3"}:
                continue
            cleaned = _cleanup_generated_text(pair[1], replacement_map)
            if cleaned != pair[1]:
                pair[1] = cleaned
                changed = True
        if not changed:
            return object_text
        return _rebuild_dxf_object("MTEXT", pairs, tail, object_text)

    return object_pattern.sub(fix_object, text)


def _placeholder_name(placeholder: str) -> str:
    match = re.fullmatch(r"\{\{([A-Z0-9_]+)\}\}", placeholder)
    return match.group(1) if match else ""


def _replace_placeholder_name(text: str, field_name: str, value: str) -> tuple[str, int]:
    pattern = re.compile(_placeholder_token_pattern(field_name))
    return pattern.subn(value, text)


def _normalize_escaped_braces(text: str) -> str:
    return text.replace(r"\{", "{").replace(r"\}", "}")


def _canonical_placeholder(value: str) -> str:
    normalized = _normalize_escaped_braces(value)
    if normalized.startswith("{{") and normalized.endswith("}}"):
        field_name = normalized[2:-2]
    elif normalized.startswith("{") and normalized.endswith("}"):
        field_name = normalized[1:-1]
        if field_name.isdigit():
            return ""
    else:
        return ""
    if not field_name or not re.fullmatch(r"[A-Z0-9_]+", field_name):
        return ""
    return f"{{{{{field_name}}}}}"


def _cleanup_generated_text(text: str, replacement_map: dict[str, str] | None = None) -> str:
    replacements = {
        "технологическогоприсоединения": "технологического присоединения",
        "присоединенияэнергопринимающих": "присоединения энергопринимающих",
        "однофазныйприбор": "однофазный прибор",
        "однофазныйна": "однофазный на",
        "трехфазныйприбор": "трехфазный прибор",
        "трехфазныйна": "трехфазный на",
        "трёхфазныйприбор": "трёхфазный прибор",
        "трёхфазныйна": "трёхфазный на",
        "подвесомТП": "подвесом ТП",
        "кВА кВА": "кВА",
        ",к/н": ", к/н",
        "Автоматизированная система управления II категории технической сложности с количеством каналов (Кобщ): 2": (
            r"Автоматизированная система управления II категории\P"
            "технической сложности, Кобщ: 2"
        ),
    }
    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)
    result = _repair_mtext_format_garbage(result)
    result = result.replace(r"\pq*,tz;", r"\pqc,tz;")
    result = re.sub(r"\\P\s*,\s*к/н", ", к/н", result)
    result = re.sub(r"\bкВА\s+кВА\b", "кВА", result)
    result = re.sub(
        r"\bкВА\s+до\s+границы\s+участка\s+Заявителя\s+кВА\s+до\s+границы\s+участка\s+Заявителя\b",
        "кВА до границы участка Заявителя",
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(
        r"(до\s+границы\s+участка\s+Заявителя)\s+кВА\s+\1",
        r"\1",
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(
        r"(ТП\s*№\s*[0-9][0-9\s/\-]*[0-9]\s*кВА\s+до\s+границы\s+участка\s+Заявителя)\s+кВА\s+до\s+границы\s+участка\s+Заявителя",
        r"\1",
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(r"\bна\s+4\s+модулей\b", "на 4 модуля", result)
    result = re.sub(r"\bна\s+8\s+модуля\b", "на 8 модулей", result)
    result = _remove_visible_mtext_format_fragments(result)
    result = _collapse_duplicate_tp_names(result)
    if replacement_map:
        result = _apply_project_number_literal_replacements(result, replacement_map)
        result = _apply_address_literal_replacements(result, replacement_map)
        result = _apply_commutator_literal_replacements(result, replacement_map)
        result = _apply_calculated_literal_replacements(result, replacement_map)
        result = _apply_climate_literal_replacements(result, replacement_map)
        result = _apply_branch_armature_literal_replacements(result, replacement_map)
    result = re.sub(r"(?<=[А-Яа-яЁё])\((?=[А-ЯЁ])", " (", result)
    return result


def _apply_branch_armature_literal_replacements(text: str, replacement_map: dict[str, str]) -> str:
    branch_line = replacement_map.get("{{BRANCH_ARMATURE_LINE}}", "")
    if not branch_line:
        return text

    patterns = (
        re.compile(
            r"Монтаж ответвительной арматуры от сущ\. опоры №[\w/-]+ ВлИ 0,4 кВ фидера №\d+ [^\n\\]+",
            re.IGNORECASE,
        ),
        re.compile(
            r"Монтаж ответвительной арматуры на опоре №\d+ ВЛ 0,4 кВ фидера №\d+ [^\n\\]+",
            re.IGNORECASE,
        ),
        re.compile(
            r"Монтаж ответвительной арматуры от РУ 0,4 кВ [^\n\\]+",
            re.IGNORECASE,
        ),
    )
    result = text
    for pattern in patterns:
        result = pattern.sub(branch_line, result)
    return result


def _fix_branch_armature_line_raw(path: Path, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return
    if not replacement_map.get("{{BRANCH_ARMATURE_LINE}}", ""):
        return

    original_text = path.read_text(encoding="utf-8", errors="replace")
    updated_text = _apply_branch_armature_literal_replacements(original_text, replacement_map)
    if updated_text != original_text:
        path.write_text(updated_text, encoding="utf-8")


def _remove_visible_mtext_format_fragments(text: str) -> str:
    result = re.sub(r"(?<!\\H)\b1\.20000x;", "", text)
    result = re.sub(r"(?<!\\H)\b0{3,4}x;", "", result)
    result = re.sub(r"(?<!sm1\.)\b5,ql;", "", result)
    result = re.sub(r"\\pxql;(?:t0,ql;)+", r"\\pxql;", result)
    result = re.sub(r"(\\pxi[^;]*;)(?:t0,ql;)+", r"\1", result)
    return result


def _apply_project_number_literal_replacements(text: str, replacement_map: dict[str, str]) -> str:
    project_number = replacement_map.get("{{PROJNUMB}}", "")
    match = re.match(r"^(ПСД/48/2026/\d{3})(?:-[А-ЯA-Z0-9.]+)?$", project_number)
    if not match:
        return text

    project_base = match.group(1)

    def replace(match: re.Match[str]) -> str:
        suffix = match.group(1) or ""
        return f"{project_base}{suffix}"

    return re.sub(r"ПСД/48/2026/\d{3}(-[А-ЯA-Z0-9.]+)?", replace, text)


def _apply_address_literal_replacements(text: str, replacement_map: dict[str, str]) -> str:
    address = replacement_map.get("{{ADRESS}}") or replacement_map.get("{{ADDRESS}}") or ""
    address = abbreviate_address_display_terms(address)
    kad_number = replacement_map.get("{{KADNUMBER}}", "")
    project_number = replacement_map.get("{{PROJECTNUMBER}}", "")
    if not address:
        return text

    result = text
    result = re.sub(
        r"Проектируемый\s+объект\s+находится\s+на\s+территории\s+Липецкая\s+область,\s*г\.?\s*Липецк\s*\.",
        f"Проектируемый объект находится на территории {address}.",
        result,
        flags=re.IGNORECASE,
    )

    legacy_addresses = (
        r"Липецкая область,\s*Липецкий район,\s*Падовский с/с,\s*п\.\s*Первое Мая",
        r"Липецкая область,\s*\\?Pг\.Грязи,\s*район АООТ \"Грязиагропромсервис",
        r"Липецкая область,\s*г\.?\s*Грязи,\s*район АООТ \"Грязиагропромсервис",
    )
    for pattern in legacy_addresses:
        result = re.sub(pattern, address, result, flags=re.IGNORECASE)

    def replace_stamp_address(match: re.Match[str]) -> str:
        segment = _plain_mtext(match.group(2))
        if address in segment:
            return match.group(0)
        return f"{match.group(1)}{address}{match.group(3)}"

    result = re.sub(
        r"(по\s+адресу:\s*)((?:[^{}\\]|\\[A-Za-z][^;{}\\]*;)+?)(,\s*(?:к/н|к/))",
        replace_stamp_address,
        result,
        flags=re.IGNORECASE,
    )

    result = re.sub(
        r", к/\s*\n(?:[^\n]*\n)*?\s*1\s*\nн\s*(48:\d{2}:\d+:\d+)",
        rf", к/н \1",
        result,
    )

    legacy_kad_numbers = (
        "48:13:1530301:2878",
        "48:02:1040423:107",
    )
    if kad_number:
        for legacy_kad in legacy_kad_numbers:
            result = result.replace(legacy_kad, kad_number)

    legacy_project_numbers = (
        "2024/ 161435",
        "2024/ 111945",
    )
    if project_number:
        for legacy_project in legacy_project_numbers:
            result = result.replace(legacy_project, project_number)

    result = re.sub(r"\bземельный участок\b", "з.у.", result, flags=re.IGNORECASE)

    return result


def _apply_commutator_literal_replacements(text: str, replacement_map: dict[str, str]) -> str:
    build_from = replacement_map.get("{{OTKUDASTROIT}}", "")
    if "коммутационного аппарата" not in build_from.lower():
        return text

    result = text
    result = re.sub(
        r"от\s+коммутационного\s+аппарата\s+по\s+п\.\s*13\.1\.3\.?\s+к\s+границе\s+земельного\s+участка\s+Заявителя",
        build_from,
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(
        r"от\s+коммутационного\s+аппарата\s+по\s+п\.\s*13\.1\.3\.",
        build_from,
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(
        r"(от\s+коммутационного\s+аппарата\s+ТП\s*№\s*[0-9][0-9\s/\-]*[0-9]\s*кВА\s+до\s+границы\s+участка\s+Заявителя)\s*"
        r"ТП\s*№\s*[0-9][0-9\s/\-]*[0-9]\s*кВА(?:\s+до\s+границы\s+участка\s+Заявителя)?",
        r"\1",
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(r"(Заявителя)(ТП\s*№)", r"\1 \2", result)
    return result


def _apply_calculated_literal_replacements(text: str, replacement_map: dict[str, str]) -> str:
    result = text

    supports_note = replacement_map.get("{{SUPPORTS_INSTALL_NOTE}}", "")
    if supports_note:
        result = re.sub(r"по\s+\d+\s+опорам", supports_note, result)
        result = re.sub(r"по\s+одной\s+опоре", supports_note, result)

    breaker = replacement_map.get("{{BREAKER}}", "")
    if breaker:
        result = re.sub(r"ВА47-29\s+[13][PР]\s*\d+\s*[АA]", breaker, result)

    breaker_current = replacement_map.get("{{BREAKER_CURRENT}}", "")
    if breaker_current:
        result = re.sub(r"(?:I|І|И)н\s*=\s*\d+\s*[АA]", f"Iн={breaker_current}", result)

    poles_text = replacement_map.get("{{BREAKER_POLES_TEXT}}", "")
    if poles_text:
        result = re.sub(r"(?:трех|трёх|одно)полюсный", poles_text, result, flags=re.IGNORECASE)

    poles_text_genitive = replacement_map.get("{{BREAKER_POLES_TEXT_GENITIVE}}", "")
    if poles_text_genitive:
        result = re.sub(r"(?:трех|трёх|одно)полюсного", poles_text_genitive, result, flags=re.IGNORECASE)

    return result


def _apply_calculated_literal_replacements_to_text_pairs(
    pairs: list[list[str]],
    replacement_map: dict[str, str] | None,
) -> bool:
    if not replacement_map:
        return False
    changed = False
    for pair in pairs:
        if pair[0].strip() not in {"1", "302"}:
            continue
        cleaned = _apply_calculated_literal_replacements(pair[1], replacement_map)
        cleaned = _strip_table_inline_scales(cleaned)
        if cleaned != pair[1]:
            pair[1] = cleaned
            changed = True
    return changed


def _apply_calculated_literal_replacements_acad_table_raw(
    text: str,
    replacement_map: dict[str, str] | None,
) -> str:
    if not replacement_map:
        return text

    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if not _is_project_table_text(table_text):
            return table_text
        pairs, tail = _split_object_pairs(table_text)
        if not _apply_calculated_literal_replacements_to_text_pairs(pairs, replacement_map):
            return table_text
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    return table_pattern.sub(fix_table, text)


def _apply_calculated_literal_replacements_block_mtext_raw(
    text: str,
    replacement_map: dict[str, str] | None,
) -> str:
    if not replacement_map:
        return text

    block_pattern = re.compile(r"(^  0\nBLOCK\n.*?^  0\nENDBLK)", re.DOTALL | re.MULTILINE)
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_block(match: re.Match[str]) -> str:
        block_text = match.group(1)
        rebuilt = block_text
        for object_match in object_pattern.finditer(block_text):
            object_text = object_match.group(1)
            pairs, tail = _split_object_pairs(object_text)
            if not _apply_calculated_literal_replacements_to_text_pairs(pairs, replacement_map):
                continue
            rebuilt = rebuilt.replace(
                object_text,
                _rebuild_dxf_object("MTEXT", pairs, tail, object_text),
                1,
            )
        return rebuilt

    return block_pattern.sub(fix_block, text)


def _apply_climate_literal_replacements(text: str, replacement_map: dict[str, str]) -> str:
    values = _climate_values_from_map(replacement_map)
    if not values:
        return text

    result = text
    result = re.sub(
        r"(район\s+по\s+голол[её]ду\s*-\s*)(?:IV|III|II|I)",
        lambda match: f"{match.group(1).rstrip()} {values['ice_district']}",
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(
        r"(нормативная\s+толщина\s+стенки\s+голол[её]да\s*-\s*)\d+",
        rf"\g<1>{values['ice_thickness']}",
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(
        r"(район\s+по\s+ветру\s*-\s*)(?:IV|III|II|I)",
        lambda match: f"{match.group(1).rstrip()} {values['wind_district']}",
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(
        r"(нормативная\s+скорость\s+ветра\s*-\s*)\d+",
        rf"\g<1>{values['wind_speed']}",
        result,
        flags=re.IGNORECASE,
    )
    result = re.sub(
        r"(ветровое\s+давление\s*-\s*)\d+",
        rf"\g<1>{values['wind_pressure']}",
        result,
        flags=re.IGNORECASE,
    )
    return result


def _collapse_duplicate_tp_names(text: str) -> str:
    number = r"([0-9][0-9\s/\-]*[0-9])"
    style_open = r"(?:\}\{\\[^;{}]+;)?"
    pattern = re.compile(
        rf"(ТП\s*№\s*{style_open}\s*{number}\s*кВА)\s*ТП\s*№\s*\2\s*кВА",
        re.IGNORECASE,
    )
    previous = None
    result = text
    while previous != result:
        previous = result
        result = pattern.sub(r"\1", result)
        result = re.sub(
            r"(ТП\s*№\s*([0-9][0-9\s/\-]*[0-9])\s*кВА)\s*ТП\s*№\s*\2\s*кВА",
            r"\1",
            result,
            flags=re.IGNORECASE,
        )
    return result


def _fit_long_table_mtext(entity: Any, text: str) -> None:
    if "Автоматизированная система управления II категории" not in text:
        return

    char_height = float(getattr(entity.dxf, "char_height", 0) or 0)
    if char_height > LONG_SPEC_TEXT_HEIGHT or 0 < char_height < LONG_SPEC_TEXT_HEIGHT:
        entity.dxf.char_height = LONG_SPEC_TEXT_HEIGHT


def _fit_volume_table_mtext(entity: Any, text: str) -> None:
    volume_markers = (
        "Строительная длина линии",
        "Установка ж.б.опоры",
        "Монтаж ответвительной",
        "Монтаж самонесущего",
        "Монтаж заземляющего",
        "Монтаж счетчика",
        "Монтаж выключателя",
        "Монтаж щита",
        "Монтаж проката",
        "Состав электротехнических измерений",
    )
    if not any(marker in text for marker in volume_markers):
        return

    char_height = float(getattr(entity.dxf, "char_height", 0) or 0)
    if 0 < char_height < BODY_TEXT_HEIGHT:
        entity.dxf.char_height = BODY_TEXT_HEIGHT


def _fit_body_note_mtext(entity: Any, text: str) -> None:
    if not _is_body_note_mtext(text):
        return

    entity.dxf.char_height = BODY_TEXT_HEIGHT


def _fit_numeric_result_mtext(entity: Any, text: str, replacement_map: dict[str, str]) -> None:
    if not _is_numeric_result_text(text, replacement_map) and not _is_spec_table_quantity_text(text):
        return

    entity.dxf.char_height = BODY_TEXT_HEIGHT


def _is_numeric_result_text(text: str, replacement_map: dict[str, str] | None) -> bool:
    plain = _plain_mtext(text).replace(",", ".").strip()
    if not re.fullmatch(r"\d+(?:\.\d+)?", plain):
        return False
    return plain in _numeric_result_values(replacement_map)


def _numeric_result_values(replacement_map: dict[str, str] | None) -> set[str]:
    if not replacement_map:
        return set()

    values: set[str] = set()
    for field_name in NUMERIC_RESULT_TEXT_FIELDS:
        value = replacement_map.get(f"{{{{{field_name}}}}}")
        if not value:
            continue
        normalized = str(value).replace(",", ".").strip()
        values.add(normalized)
    return values


def _is_body_or_work_table_text(text: str) -> bool:
    plain = _plain_mtext(text)
    return any(
        marker in plain
        for marker in (*LEFT_ALIGNED_BODY_MARKERS, *BODY_PARAGRAPH_LEFT_ALIGN_MARKERS, *WORK_TABLE_MARKERS)
    )


def _is_spec_table_quantity_text(text: str) -> bool:
    plain = _plain_mtext(text).replace(",", ".").strip()
    return _is_numeric_quantity_cell_text(plain)


def _plain_numeric_token(text: str) -> str:
    plain = _plain_mtext(text).replace(",", ".").strip()
    return plain.lstrip("{").rstrip("}").lstrip("/")


def _is_numeric_quantity_cell_text(text: str) -> bool:
    plain = _plain_numeric_token(text)
    if not plain:
        return False
    if re.fullmatch(r"\d+(?:\.\d+)?", plain):
        return True
    return bool(re.fullmatch(r"\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?", plain))


def _is_dxf_numeric(value: str) -> bool:
    try:
        float(value.replace(",", ".").strip())
        return True
    except ValueError:
        return False


def _repair_mtext_continuation_group_codes_raw(text: str) -> str:
    """Fix ezdxf MTEXT chunks that start with digits and were saved as group 10/20/30."""
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)
    coord_codes = frozenset({"10", "20", "30"})

    def fix_object(match: re.Match[str]) -> str:
        object_text = match.group(1)
        pairs, tail = _split_object_pairs(object_text)
        text_started = False
        for pair in pairs:
            code = pair[0].strip()
            value = pair[1]
            if code in {"1", "3"}:
                text_started = True
                continue
            if not text_started or code not in coord_codes:
                continue
            if not _is_dxf_numeric(value):
                pair[0] = "  3"
        return _rebuild_dxf_object("MTEXT", pairs, tail, object_text)

    return object_pattern.sub(fix_object, text)


def _repair_mtext_continuation_group_codes_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    repaired = _repair_mtext_continuation_group_codes_raw(text)
    if repaired != text:
        path.write_text(repaired, encoding="utf-8")


def _repair_mtext_format_garbage(text: str) -> str:
    result = text
    result = re.sub(r"\\pxql,ql;", r"\\pxqc;", result)
    result = re.sub(r"\\pxqc,ql;", r"\\pxqc;", result)
    result = re.sub(r"\\pxql;(?=i[34],l0)", r"\\px", result)
    result = re.sub(r"\\pxql;(?=(?!Все)[А-Яа-яЁёA-Za-z])", "", result)
    result = re.sub(r"(?<=;)\\pxql;(?=\{)", "", result)
    result = re.sub(r"(?:t0,0;|t0,ql;)i[34],l0,sm1,t0,ql;", "t0,0;", result)
    result = re.sub(r"(?:t0,0;|t0,ql;)i[34],l0,t0,ql;", "t0,0;", result)
    result = re.sub(r"\\pxql;(\\px)?(i[34],)", r"\\px\2", result)
    result = re.sub(r"\\pxql;\{\\L\}", r"\\pxqc;{\\L}", result)
    return result


def _apply_body_mtext_formatting(text: str) -> str:
    return _format_body_note_text(text)


def _has_paragraph_align(content: str) -> bool:
    return bool(re.search(r"(?:^|[,;])q[clrj]", content))


def _paragraph_has_format(paragraph: str) -> bool:
    return bool(re.match(r"\\px", paragraph.lstrip()))


def _is_section_5_6_heading(paragraph: str) -> bool:
    if "Противопожарные мероприятия и пожарная защита" in paragraph:
        return True
    if "\\LОрганизация строительства" in paragraph or (
        "Организация строительства" in paragraph and "\\L6." in paragraph
    ):
        return True
    if re.search(r"5\.\}.*Охрана труда и техника безопасности", paragraph):
        return True
    if "Охрана труда и техника безопасности" not in paragraph:
        return False
    if "при строительстве" in paragraph:
        return False
    plain = _plain_mtext(paragraph)
    return len(plain) < 80 and "5." in plain


def _is_centered_heading_paragraph(paragraph: str) -> bool:
    if any(marker in paragraph for marker in BODY_PARAGRAPH_LEFT_ALIGN_MARKERS):
        return False
    if 'Проект "' in paragraph or "Проектом технологического" in paragraph:
        return False
    if "На основании уточненных" in paragraph:
        return False
    if "Технические  характеристики" in paragraph or "Технические характеристики" in paragraph:
        return False
    if _is_section_5_6_heading(paragraph):
        return True
    return any(marker in paragraph for marker in CENTERED_HEADING_PLAIN_MARKERS)


def _paragraph_format_to_center(paragraph: str) -> str:
    paragraph = re.sub(r"\\pxql,ql;", r"\\pxqc;", paragraph)
    paragraph = re.sub(r"\\pxql;", r"\\pxqc;", paragraph)
    paragraph = re.sub(r"\\pxqc,ql;", r"\\pxqc;", paragraph)

    def replace_format(match: re.Match[str]) -> str:
        content = match.group(1)
        content = re.sub(r",ql(?=[,;]|$)", "", content)
        content = re.sub(r"^ql(?=[,;]|$)", "qc", content)
        if not _has_paragraph_align(content):
            content = f"{content},qc" if content else "qc"
        return f"\\px{content};"

    return re.sub(r"\\px([^;\\]+);", replace_format, paragraph, count=1)


def _paragraph_format_to_center_heading(paragraph: str) -> str:
    body_match = re.match(r"\\px[^;\\]+;(.*)$", paragraph, re.DOTALL)
    body = body_match.group(1) if body_match else paragraph.lstrip()
    extras: list[str] = []
    format_match = re.search(r"\\px([^;\\]+);", paragraph)
    if format_match:
        for token in format_match.group(1).split(","):
            if re.fullmatch(r"t[\d.]+", token) or re.fullmatch(r"b[\d.]+", token):
                extras.append(token)
    format_code = ",".join(["qc", *extras]) if extras else "qc"
    return rf"\px{format_code};{body}"


def _paragraph_format_to_left(paragraph: str) -> str:
    def replace_format(match: re.Match[str]) -> str:
        content = match.group(1)
        content = re.sub(r"^qc(?=[,;])", "ql", content)
        content = re.sub(r",qc(?=[,;])", ",ql", content)
        if not _has_paragraph_align(content):
            content = f"{content},ql" if content else "ql"
        return f"\\px{content};"

    paragraph = re.sub(r"\\pxqc;", r"\\pxql;", paragraph)
    return re.sub(r"\\px([^;\\]+);", replace_format, paragraph, count=1)


def _tighten_general_notes_line_spacing(text: str) -> str:
    plain = _plain_mtext(text)
    if "ОБЩИЕ УКАЗАНИЯ" not in plain or "Строительство ЛЭП" not in plain:
        return text

    def replace_format(match: re.Match[str]) -> str:
        content = match.group(1)
        if "sm1.5" in content:
            return match.group(0)
        if re.search(r"sm[\d.]+", content):
            return match.group(0)
        return f"\\px{content},sm{GENERAL_NOTES_LINE_SPACING:g};"

    return re.sub(r"\\px([^;\\]+);", replace_format, text)


def _is_decorative_centered_paragraph(paragraph: str) -> bool:
    if _is_column_spacer_paragraph(paragraph):
        return True
    return bool(re.search(r"\\pxqc,t4.*\{\\A1;\\L\}\s*$", paragraph))


def _is_column_spacer_paragraph(paragraph: str) -> bool:
    return bool(re.fullmatch(r"\\pxq[cl];\{\\L\}", paragraph.strip()))


def _prepend_left_format(paragraph: str) -> str:
    body_match = re.match(r"\\px[^;\\]+;(.*)$", paragraph, re.DOTALL)
    body = body_match.group(1) if body_match else paragraph.lstrip()
    return rf"\pxi3,l1,ql,sm1;{body.lstrip()}"


def _format_body_note_text(text: str) -> str:
    text = _normalize_body_note_inline_heights(text)
    paragraphs = text.split(r"\P")
    formatted = []
    for paragraph in paragraphs:
        if _is_column_spacer_paragraph(paragraph):
            formatted.append(r"\pxqc;{\L}")
            continue
        if _is_centered_heading_paragraph(paragraph) or _is_decorative_centered_paragraph(paragraph):
            formatted.append(_paragraph_format_to_center_heading(paragraph))
        elif any(marker in paragraph for marker in LEFT_ALIGNED_INTRO_MARKERS):
            formatted.append(_prepend_left_format(paragraph))
        elif _paragraph_has_format(paragraph):
            formatted.append(_paragraph_format_to_left(paragraph))
        else:
            formatted.append(_prepend_left_format(paragraph))
    text = r"\P".join(formatted)
    text = _remove_empty_body_paragraphs_before_markers(text)
    return _tighten_general_notes_line_spacing(text)


def _position_title_page_year_text(text: str) -> str:
    if "2026г." not in text:
        return text
    gaps = r"\P" * TITLE_PAGE_YEAR_PARAGRAPH_GAPS
    result = re.sub(
        r"(\\H[\d.]+x?;)(?:\\P)+(?=2026г\.)",
        r"\1",
        text,
    )
    updated = re.sub(
        r"(\\H[\d.]+x?;)(?=2026г\.)",
        lambda match: match.group(1) + gaps,
        result,
        count=1,
    )
    if updated != result:
        return updated
    result = re.sub(r"(?:\\P)+(?=2026г\.)", "", text)
    return re.sub(
        r"(?=2026г\.)",
        lambda _match: gaps,
        result,
        count=1,
    )


def _position_title_page_year_text_raw(text: str) -> str:
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_object(match: re.Match[str]) -> str:
        object_text = match.group(1)
        raw_text = _raw_text_content_from_object(object_text)
        if not _is_title_page_mtext(raw_text):
            return object_text

        pairs, tail = _split_object_pairs(object_text)
        changed = False
        for pair in pairs:
            if pair[0].strip() not in {"1", "3"}:
                continue
            updated = _position_title_page_year_text(pair[1])
            if updated != pair[1]:
                pair[1] = updated
                changed = True
        if not changed:
            return object_text
        return _rebuild_dxf_object("MTEXT", pairs, tail, object_text)

    return object_pattern.sub(fix_object, text)


def _format_title_page_text(text: str) -> str:
    paragraphs = text.split(r"\P")
    formatted = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            formatted.append(paragraph)
            continue
        if re.search(r"\\px[^;\\]*(?:^|[,;])ql(?:[,;]|$)", paragraph):
            formatted.append(_paragraph_format_to_center(paragraph))
        else:
            formatted.append(paragraph)
    return r"\P".join(formatted)


def _is_title_page_mtext(text: str) -> bool:
    plain = _plain_mtext(text)
    return any(marker in plain for marker in TITLE_PAGE_MARKERS)


def _format_mtext_alignment(text: str) -> str:
    if _is_title_page_mtext(text):
        return _format_title_page_text(text)
    if _is_body_note_mtext(text):
        return _format_body_note_text(text)
    return text


def _apply_body_alignment_only(text: str) -> str:
    return _format_body_note_text(text)


def _normalize_body_note_inline_heights(text: str) -> str:
    result = re.sub(r"\\T[\d.]+;", "", text)
    result = re.sub(r"\\W[\d.]+;", "", result)
    result = re.sub(r"\\H[\d.]+x?;", r"\\H1.0x;", result)
    result = re.sub(r"\\H1\.2[^;]*;", r"\\H1.0x;", result)
    return re.sub(r"\\H0\.9999\d*x;", r"\\H1.0x;", result)


def _is_toc_item_mtext(text: str) -> bool:
    plain = _plain_mtext(text).strip()
    return plain in {
        "Пояснительная записка",
        "1. Исходные данные",
        TOC_ELECTRO_ITEM_PLAIN,
        "3. Строительные решения",
        "4. Охрана окружающей среды",
        "6. Организация строительства",
        "Приложения:",
    }


def _is_body_note_mtext(text: str) -> bool:
    if _is_toc_item_mtext(text):
        return False
    plain = _plain_mtext(text)
    if any(marker in plain for marker in WORK_TABLE_MARKERS):
        return False
    return any(
        marker in plain
        for marker in (
            *LEFT_ALIGNED_BODY_MARKERS,
            *BODY_PARAGRAPH_LEFT_ALIGN_MARKERS,
            "ОБЩИЕ УКАЗАНИЯ",
            "Электротехнические решения",
            "Электротехнические  решения",
        )
    )


def _apply_body_alignment_raw(text: str) -> str:
    return _apply_mtext_entity_fixes_raw(text)


def _normalize_body_note_heights_raw(text: str) -> str:
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_object(match: re.Match[str]) -> str:
        object_text = match.group(1)
        raw_text = _raw_text_content_from_object(object_text)
        if not _is_body_note_mtext(raw_text):
            return object_text

        pairs, tail = _split_object_pairs(object_text)
        for pair in pairs:
            if pair[0].strip() not in {"1", "3"}:
                continue
            pair[1] = _normalize_body_note_inline_heights(pair[1])
        for pair in pairs:
            if pair[0].strip() != "40":
                continue
            pair[1] = f"{BODY_TEXT_HEIGHT:.1f}"
            break
        return _rebuild_dxf_object("MTEXT", pairs, tail, object_text)

    return object_pattern.sub(fix_object, text)


def _safe_left_align_mtext_content(text: str) -> str:
    return _apply_body_mtext_formatting(_repair_mtext_format_garbage(text))


def _detach_mtext_columns_raw(text: str) -> str:
    patterns = (
        r"\n1000\nACAD_MTEXT_COLUMN_INFO_BEGIN\n.*?\n1000\nACAD_MTEXT_COLUMN_INFO_END",
        r"\n1000\nACAD_MTEXT_COLUMNS_BEGIN\n.*?\n1000\nACAD_MTEXT_COLUMNS_END",
        r"\n1000\nACAD_MTEXT_DEFINED_HEIGHT_BEGIN\n.*?\n1000\nACAD_MTEXT_DEFINED_HEIGHT_END",
    )
    result = text
    for pattern in patterns:
        result = re.sub(pattern, "", result, flags=re.DOTALL)
    return result


def _split_mtext_dxf_chunks(text: str, max_len: int = 250) -> tuple[list[str], str]:
    if len(text) <= max_len:
        return [], text

    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_len:
        chunks.append(remaining[:max_len])
        remaining = remaining[max_len:]
    return chunks, remaining


def _assign_mtext_dxf_chunks(pairs: list[list[str]], fixed_text: str) -> None:
    indices_3 = [index for index, (code, _) in enumerate(pairs) if code.strip() == "3"]
    indices_1 = [index for index, (code, _) in enumerate(pairs) if code.strip() == "1"]
    chunks, last_chunk = _split_mtext_dxf_chunks(fixed_text)

    for index in indices_3:
        pairs[index][1] = ""
    for index in indices_1:
        pairs[index][1] = ""

    if indices_3:
        for index, chunk in zip(indices_3, chunks):
            pairs[index][1] = chunk
        if indices_1:
            pairs[indices_1[-1]][1] = last_chunk
        elif chunks:
            pairs[indices_3[-1]][1] += last_chunk
        return

    if indices_1:
        pairs[indices_1[-1]][1] = fixed_text


def _apply_mtext_entity_fixes_raw(text: str) -> str:
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_object(match: re.Match[str]) -> str:
        object_text = match.group(1)
        raw_text = _raw_text_content_from_object(object_text)
        if _is_title_page_mtext(raw_text):
            return object_text
        if _is_equipment_footnote_mtext(raw_text):
            return object_text

        pairs, tail = _split_object_pairs(object_text)
        stripped_changed = False
        for pair in pairs:
            if pair[0].strip() in {"1", "3"}:
                cleaned = _strip_table_inline_scales(pair[1])
                if cleaned != pair[1]:
                    pair[1] = cleaned
                    stripped_changed = True
        text_indices = [index for index, (code, _) in enumerate(pairs) if code.strip() in {"1", "3"}]
        if not text_indices:
            return object_text

        full_text = "".join(pairs[index][1] for index in text_indices)
        fixed_text = _format_mtext_alignment(full_text)
        if fixed_text == full_text and not stripped_changed:
            return object_text

        if fixed_text != full_text:
            _assign_mtext_dxf_chunks(pairs, fixed_text)
        return _rebuild_dxf_object("MTEXT", pairs, tail, object_text)

    return object_pattern.sub(fix_object, text)


def _rebuild_dxf_object(entity_type: str, pairs: list[list[str]], tail: list[str], original_text: str) -> str:
    rebuilt = "\n".join(_join_object_pairs(pairs, tail, entity_type))
    if original_text.endswith("\n") and not rebuilt.endswith("\n"):
        rebuilt += "\n"
    return rebuilt


def _split_object_pairs(object_text: str) -> tuple[list[list[str]], list[str]]:
    lines = object_text.splitlines()
    if len(lines) < 2:
        return [], lines
    pairs = [[lines[index], lines[index + 1]] for index in range(2, len(lines) - 1, 2)]
    tail = lines[2 + len(pairs) * 2 :]
    return pairs, tail


def _join_object_pairs(pairs: list[list[str]], tail: list[str], entity_type: str = "MTEXT") -> list[str]:
    lines = ["  0", entity_type]
    for code, value in pairs:
        lines.extend((code, value))
    lines.extend(tail)
    return lines


def _strip_table_inline_scales(text: str) -> str:
    text = re.sub(r"\\W[\d.]+;", "", text)
    text = re.sub(r"\\T[\d.]+;", "", text)
    text = re.sub(r"\\H[\d.]+x?;", "", text)
    text = re.sub(r"\{(\d+)\}", r"\1", text)
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}") and "{" not in stripped[1:-1]:
        return stripped[1:-1]
    return text


def _is_stamp_title_mtext(text: str) -> bool:
    if any(
        marker in text
        for marker in ("ОБЩИЕ УКАЗАНИЯ", "УПРАВЛЕНИЕ ТЕХНОЛОГИЧЕСКОГО", "ПРОЕКТНАЯ ДОКУМЕНТАЦИЯ", "Исходные данные")
    ):
        return False

    normalized = text.replace(r"\P", " ")
    if re.match(r"^\s*\d+\.", normalized.lstrip()):
        return False
    if "Строительство ЛЭП" not in normalized:
        return False
    if "расположен" not in normalized.lower():
        return False
    return "к/н" in normalized.lower()


def _fit_stamp_title_mtext(entity: Any, text: str) -> str:
    text = _strip_table_inline_scales(text)
    entity.dxf.char_height = STAMP_TITLE_TEXT_HEIGHT
    return text


def _fit_stamp_title_mtext_entities(document: Any) -> None:
    for entity in _iter_text_entities(document):
        if entity.dxftype() != "MTEXT":
            continue
        if not _is_stamp_title_mtext(entity.plain_text()):
            continue
        text = _get_text(entity)
        if not text:
            continue
        _set_text(entity, _fit_stamp_title_mtext(entity, text))


def _is_breaker_mtext_text(text: str) -> bool:
    return "ВА47-29" in _plain_mtext(text)


def _fit_breaker_mtext(entity: Any, text: str) -> str:
    text = _strip_table_inline_scales(text)
    entity.dxf.char_height = BREAKER_TEXT_HEIGHT
    return text


def _remove_empty_body_paragraphs_before_markers(text: str) -> str:
    paragraphs = text.split(r"\P")
    cleaned: list[str] = []
    index = 0
    while index < len(paragraphs):
        paragraph = paragraphs[index]
        if not _plain_mtext(paragraph).strip():
            next_index = index + 1
            while next_index < len(paragraphs) and not _plain_mtext(paragraphs[next_index]).strip():
                next_index += 1
            if next_index < len(paragraphs):
                next_plain = _plain_mtext(paragraphs[next_index]).strip()
                if any(next_plain.startswith(marker) for marker in BODY_EMPTY_PARAGRAPH_NEXT_MARKERS):
                    index = next_index
                    continue
        cleaned.append(paragraph)
        index += 1
    return r"\P".join(cleaned)


def _fit_spec_table_quantity_mtext(entity: Any, text: str) -> str:
    text = _strip_table_inline_scales(text)
    entity.dxf.char_height = BODY_TEXT_HEIGHT
    return text


def _is_table_block_text(text: str) -> bool:
    plain = _plain_mtext(text)
    return any(
        marker in plain
        for marker in (
            *SPEC_TABLE_MARKERS,
            *WORK_TABLE_MARKERS,
            *CLIMATE_TABLE_LABELS,
            "Наименование показателя",
            "Единица",
            "Показатель",
            "Основные показатели",
            "Кол.",
        )
    )


def _fit_table_block_mtext_entities(document: Any) -> None:
    for block in document.blocks:
        if not block.name.startswith("*T"):
            continue
        block_text = " ".join(
            _get_text(entity)
            for entity in block
            if entity.dxftype() in {"TEXT", "MTEXT"} and _get_text(entity)
        )
        if not _is_table_block_text(block_text):
            continue
        for entity in block:
            if entity.dxftype() != "MTEXT":
                continue
            text = _get_text(entity)
            if not text:
                continue
            plain = _plain_mtext(text).replace(",", ".").strip()
            if _is_breaker_mtext_text(text):
                _set_text(entity, _fit_breaker_mtext(entity, text))
                continue
            if _is_spec_table_quantity_text(text) or re.fullmatch(r"\d+(?:\.\d+)?", plain):
                _set_text(entity, _fit_spec_table_quantity_mtext(entity, text))
                continue
            if "\\W" in text or "\\T" in text:
                cleaned = _strip_table_inline_scales(text)
                if cleaned != text:
                    entity.dxf.char_height = BODY_TEXT_HEIGHT
                    _set_text(entity, cleaned)


def _work_table_support_placeholder(marker: str) -> str | None:
    normalized = re.sub(r"\s+", "", marker.strip())
    return WORK_TABLE_SUPPORT_MARKERS.get(marker.strip()) or WORK_TABLE_SUPPORT_MARKERS.get(normalized)


def _work_table_support_field_name(marker: str) -> str | None:
    placeholder = _work_table_support_placeholder(marker)
    if not placeholder:
        return None
    match = re.fullmatch(r"\{\{([A-Z0-9_]+)\}\}", placeholder)
    return match.group(1) if match else None


def _dedupe_table_cell_text(text: str) -> str:
    plain = _plain_mtext(text).strip()
    if not plain:
        return ""
    chunks = re.split(r"\s{2,}", plain)
    if len(chunks) >= 2 and chunks[0] == chunks[1]:
        return chunks[0]
    midpoint = len(plain) // 2
    if midpoint > 0:
        left = plain[:midpoint].strip()
        right = plain[midpoint:].strip()
        if left and left == right:
            return left
    return plain


def _work_table_support_field_for_row(row_cells: list[str]) -> str | None:
    if not row_cells:
        return None

    name = _dedupe_table_cell_text(row_cells[1] if len(row_cells) > 1 else "")
    if re.search(r"всего\s+опор", name, flags=re.IGNORECASE):
        return "S"

    type_text = _dedupe_table_cell_text(row_cells[2] if len(row_cells) > 2 else "")
    field_name = _work_table_support_field_name(type_text)
    if field_name:
        return field_name
    for pattern, field in WORK_TABLE_SUPPORT_TYPE_PATTERNS:
        if pattern.search(type_text):
            return field
    for pattern, field in WORK_TABLE_SUPPORT_NAME_PATTERNS:
        if pattern.search(name):
            return field
    return None


def _work_table_support_replacement_value(field_name: str, replacement_map: dict[str, str]) -> str:
    value = replacement_map.get(f"{{{{{field_name}}}}}", "")
    if value != "":
        return str(value)
    if field_name in {"P23", "A23", "YA23", "K21", "S", "GROUND"}:
        return "0"
    return ""


def _is_work_volume_table_text(table_text: str) -> bool:
    plain = _plain_mtext(table_text)
    return any(marker in plain for marker in WORK_TABLE_MARKERS)


def _acad_table_dimension_pair_indexes(
    pairs: list[list[str]],
) -> tuple[int, int, list[int], list[int]] | None:
    table_index = next(
        (index for index, (_, value) in enumerate(pairs) if value == "AcDbTable"),
        None,
    )
    if table_index is None:
        return None

    row_count: int | None = None
    col_count: int | None = None
    for index in range(table_index + 1, min(len(pairs), table_index + 40)):
        code = pairs[index][0].strip()
        if code == "91" and row_count is None:
            try:
                candidate = int(pairs[index][1])
            except ValueError:
                continue
            if candidate > 0:
                row_count = candidate
        elif code == "92" and col_count is None and row_count is not None:
            try:
                candidate = int(pairs[index][1])
            except ValueError:
                continue
            if candidate > 0:
                col_count = candidate
                break

    if not row_count or not col_count:
        return None

    height_indexes = [index for index, (code, _) in enumerate(pairs) if code.strip() == "141"]
    width_indexes = [index for index, (code, _) in enumerate(pairs) if code.strip() == "142"]
    if len(height_indexes) != row_count or len(width_indexes) != col_count:
        return None
    return row_count, col_count, height_indexes, width_indexes


def _extract_work_table_row_cell_texts(
    pairs: list[list[str]],
    row_count: int,
    col_count: int,
) -> list[list[str]]:
    rows: list[list[str]] = [[] for _ in range(row_count)]
    current_row = 0
    current_col = 0
    collecting = False
    cell_parts: list[str] = []

    for code, value in pairs:
        if value == "CELL_VALUE":
            collecting = True
            cell_parts = []
            continue
        if collecting and value == "ACVALUE_END":
            if current_row < row_count and len(rows[current_row]) < col_count:
                rows[current_row].append(" ".join(cell_parts).strip())
            current_col += 1
            if current_col >= col_count:
                current_col = 0
                current_row += 1
            collecting = False
            continue
        if collecting and code.strip() == "1":
            cell_parts.append(value)
        elif collecting and code.strip() == "302" and not cell_parts:
            cell_parts.append(value)

    return rows


def _set_acad_table_cell_text_pairs(
    pairs: list[list[str]],
    cell_start: int,
    cell_end: int,
    new_value: str,
) -> bool:
    primary_index: int | None = None
    fallback_index: int | None = None
    for index in range(cell_start + 1, cell_end):
        code = pairs[index][0].strip()
        if code == "1":
            primary_index = index
            break
        if code == "302" and fallback_index is None:
            fallback_index = index

    if primary_index is None and fallback_index is not None:
        pairs[fallback_index][1] = new_value
        pairs.insert(fallback_index, ["1", new_value])
        return True
    if primary_index is None:
        pairs.insert(cell_end, ["1", new_value])
        return True

    changed = False
    for index in range(cell_start + 1, cell_end):
        if pairs[index][0].strip() not in {"1", "302"}:
            continue
        if pairs[index][1] != new_value:
            pairs[index][1] = new_value
            changed = True
    return changed


def _update_work_table_support_quantities_in_pairs(
    pairs: list[list[str]],
    row_count: int,
    col_count: int,
    replacement_map: dict[str, str],
) -> bool:
    row_texts = _extract_work_table_row_cell_texts(pairs, row_count, col_count)
    cell_targets: dict[tuple[int, int], str] = {}
    for row_index, row_cells in enumerate(row_texts):
        field_name = _work_table_support_field_for_row(row_cells)
        if not field_name:
            continue
        value = _work_table_support_replacement_value(field_name, replacement_map)
        if value == "":
            continue
        cell_targets[(row_index, WORK_TABLE_QUANTITY_COLUMN_INDEX)] = value

    if not cell_targets:
        return False

    changed = False
    current_row = 0
    current_col = 0
    cell_start: int | None = None
    for index, (_, value) in enumerate(pairs):
        if value == "CELL_VALUE":
            cell_start = index
            continue
        if cell_start is None or value != "ACVALUE_END":
            continue

        target_value = cell_targets.get((current_row, current_col))
        if target_value is not None:
            changed = _set_acad_table_cell_text_pairs(pairs, cell_start, index, target_value) or changed

        current_col += 1
        if current_col >= col_count:
            current_col = 0
            current_row += 1
        cell_start = None

    return changed


def _fix_work_table_support_quantities_in_acad_tables_raw(text: str, replacement_map: dict[str, str]) -> str:
    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if not _is_work_volume_table_text(table_text):
            return table_text
        pairs, tail = _split_object_pairs(table_text)
        dimensions = _acad_table_dimension_pair_indexes(pairs)
        if dimensions is None:
            return table_text
        row_count, col_count, _, _ = dimensions
        if not _update_work_table_support_quantities_in_pairs(
            pairs,
            row_count,
            col_count,
            replacement_map,
        ):
            return table_text
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    return table_pattern.sub(fix_table, text)


def _fix_work_table_support_quantities(document: Any, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return
    for block in document.blocks:
        if not block.name.startswith("*T"):
            continue
        entities = [entity for entity in block if entity.dxftype() == "MTEXT"]
        for index, entity in enumerate(entities):
            marker = _plain_mtext(_get_text(entity)).strip()
            placeholder = _work_table_support_placeholder(marker)
            if not placeholder:
                continue
            value = replacement_map.get(placeholder, "")
            if value == "" and placeholder in {
                "{{P23}}",
                "{{A23}}",
                "{{YA23}}",
                "{{K21}}",
                "{{S}}",
            }:
                value = "0"
            if not value:
                continue
            for next_entity in entities[index + 1 :]:
                text = _get_text(next_entity)
                plain = _plain_mtext(text).replace(",", ".").strip()
                if plain in {"шт", "м", "км", "м³", "км/кг", "шт/ м³"}:
                    continue
                if not re.fullmatch(r"\d+(?:\.\d+)?", plain):
                    continue
                _set_text(next_entity, _fit_spec_table_quantity_mtext(next_entity, value))
                break


def _climate_mtext_value_matches(plain: str, value_kind: str) -> bool:
    if value_kind == "roman":
        return bool(re.fullmatch(r"I|II|III|IV", plain))
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", plain))


def _fix_climate_table_mtext_values(document: Any, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return
    values = _climate_values_from_map(replacement_map)
    if not values:
        return
    for block in document.blocks:
        if not block.name.startswith("*T"):
            continue
        entities = [entity for entity in block if entity.dxftype() == "MTEXT"]
        label_texts = [_plain_mtext(_get_text(entity)) for entity in entities]
        if not any("Район по гололеду" in text for text in label_texts):
            continue
        for index, entity in enumerate(entities):
            plain = _plain_mtext(_get_text(entity)).strip()
            for label, value_kind, value_key in CLIMATE_TABLE_ROW_REPLACEMENTS:
                if label not in plain:
                    continue
                replacement = values[value_key]
                for next_entity in entities[index + 1 :]:
                    text = _get_text(next_entity)
                    next_plain = _plain_mtext(text).strip()
                    if not _climate_mtext_value_matches(next_plain, value_kind):
                        continue
                    _set_text(
                        next_entity,
                        _replace_raw_content_value(text, str(replacement), value_kind),
                    )
                    break


def _replace_supports_install_note_text(raw_value: str, supports_note: str) -> str:
    return re.sub(r"по\s+\d+\s+опорам", supports_note, raw_value, flags=re.IGNORECASE)


def _fix_supports_install_note_entities(document: Any, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return
    supports_note = replacement_map.get("{{SUPPORTS_INSTALL_NOTE}}", "")
    if not supports_note:
        return
    for block in document.blocks:
        if not block.name.startswith("*T"):
            continue
        for entity in block:
            if entity.dxftype() != "MTEXT":
                continue
            text = _get_text(entity)
            if not re.search(r"по\s+\d+\s+опорам", text, flags=re.IGNORECASE):
                continue
            updated = _replace_supports_install_note_text(text, supports_note)
            if updated != text:
                _set_text(entity, updated)


def _fix_supports_install_note_raw(path: Path, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return
    supports_note = replacement_map.get("{{SUPPORTS_INSTALL_NOTE}}", "")
    if not supports_note:
        return

    original_text = path.read_text(encoding="utf-8", errors="replace")
    text = _replace_supports_install_note_in_acad_tables_raw(original_text, supports_note)
    block_pattern = re.compile(r"(^  0\nBLOCK\n.*?^  0\nENDBLK)", re.DOTALL | re.MULTILINE)
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_block(match: re.Match[str]) -> str:
        block_text = match.group(1)
        if not re.search(r"по\s+\d+\s+опорам", block_text, flags=re.IGNORECASE):
            return block_text
        rebuilt = block_text
        for object_match in object_pattern.finditer(block_text):
            object_text = object_match.group(1)
            pairs, tail = _split_object_pairs(object_text)
            changed = False
            for pair in pairs:
                if pair[0].strip() not in {"1", "3", "302"}:
                    continue
                updated = _replace_supports_install_note_text(pair[1], supports_note)
                if updated != pair[1]:
                    pair[1] = updated
                    changed = True
            if changed:
                rebuilt = rebuilt.replace(
                    object_text,
                    _rebuild_dxf_object("MTEXT", pairs, tail, object_text),
                    1,
                )
        return rebuilt

    text = block_pattern.sub(fix_block, text)
    text = re.sub(r"по\s+\d+\s+опорам", supports_note, text, flags=re.IGNORECASE)
    if text != original_text:
        path.write_text(text, encoding="utf-8")


def _replace_supports_install_note_in_acad_tables_raw(text: str, supports_note: str) -> str:
    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if not re.search(r"по\s+\d+\s+опорам", table_text, flags=re.IGNORECASE):
            return table_text
        pairs, tail = _split_object_pairs(table_text)
        changed = False
        for index, (code, raw_value) in enumerate(pairs):
            if code.strip() not in {"1", "302"}:
                continue
            updated = _replace_supports_install_note_text(raw_value, supports_note)
            if updated != raw_value:
                pairs[index][1] = updated
                changed = True
        if not changed:
            return table_text
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    return table_pattern.sub(fix_table, text)


def _toc_electro_item_plain(text: str) -> str:
    return _plain_mtext(text).strip()


def _fix_toc_electro_item_alignment_entities(document: Any) -> None:
    for block in document.blocks:
        if not block.name.startswith("*T"):
            continue
        reference_entity = None
        electro_entity = None
        for entity in block:
            if entity.dxftype() != "MTEXT":
                continue
            plain = _toc_electro_item_plain(_get_text(entity))
            if plain in TOC_ALIGNMENT_REFERENCE_ITEMS:
                reference_entity = entity
            if plain == TOC_ELECTRO_ITEM_PLAIN:
                electro_entity = entity
        if reference_entity is None or electro_entity is None:
            continue
        electro_entity.dxf.attachment_point = reference_entity.dxf.attachment_point
        insert = electro_entity.dxf.insert
        reference_insert = reference_entity.dxf.insert
        electro_entity.dxf.insert = (reference_insert.x, insert.y, insert.z)


def _fix_toc_electro_item_alignment_raw(path: Path) -> None:
    original_text = path.read_text(encoding="utf-8", errors="replace")
    block_pattern = re.compile(r"(^  0\nBLOCK\n.*?^  0\nENDBLK)", re.DOTALL | re.MULTILINE)
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_block(match: re.Match[str]) -> str:
        block_text = match.group(1)
        if TOC_ELECTRO_ITEM_PLAIN not in _plain_mtext(block_text):
            return block_text

        objects = [object_match.group(1) for object_match in object_pattern.finditer(block_text)]
        reference_object = None
        electro_object = None
        for object_text in objects:
            plain = _toc_electro_item_plain(_raw_text_content_from_object(object_text))
            if plain in TOC_ALIGNMENT_REFERENCE_ITEMS:
                reference_object = object_text
            if plain == TOC_ELECTRO_ITEM_PLAIN:
                electro_object = object_text

        if reference_object is None or electro_object is None:
            return block_text

        ref_pairs, _ = _split_object_pairs(reference_object)
        ref_attachment = None
        ref_insert_x = None
        for code, value in ref_pairs:
            stripped = code.strip()
            if stripped == "71":
                ref_attachment = value
            elif stripped == "10":
                ref_insert_x = value

        if ref_attachment is None and ref_insert_x is None:
            return block_text

        electro_pairs, electro_tail = _split_object_pairs(electro_object)
        changed = False
        for pair in electro_pairs:
            stripped = pair[0].strip()
            if stripped == "71" and ref_attachment is not None and pair[1] != ref_attachment:
                pair[1] = ref_attachment
                changed = True
            elif stripped == "10" and ref_insert_x is not None and pair[1] != ref_insert_x:
                pair[1] = ref_insert_x
                changed = True

        if not changed:
            return block_text
        rebuilt_electro = _rebuild_dxf_object("MTEXT", electro_pairs, electro_tail, electro_object)
        return block_text.replace(electro_object, rebuilt_electro, 1)

    updated = block_pattern.sub(fix_block, original_text)
    if updated != original_text:
        path.write_text(updated, encoding="utf-8")


def _normalize_spec_table_quantity_heights_raw(text: str) -> str:
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_object(match: re.Match[str]) -> str:
        object_text = match.group(1)
        plain = _plain_mtext(_raw_text_content_from_object(object_text)).replace(",", ".").strip()
        if not _is_numeric_quantity_cell_text(plain):
            return object_text

        height_match = re.search(r"\n 40\n([-+]?\d+(?:\.\d+)?)", object_text)
        if height_match:
            updated = re.sub(
                r"(\n 40\n)([-+]?\d+(?:\.\d+)?)",
                lambda item: f"{item.group(1)}{_min_height_value(item.group(2), BODY_TEXT_HEIGHT)}",
                object_text,
                count=1,
            )
        else:
            updated = object_text
        updated = re.sub(r"\\T[\d.]+;", "", updated)
        return updated

    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if not _is_project_table_text(table_text):
            return table_text
        pairs, tail = _split_object_pairs(table_text)
        _fix_acad_table_numeric_cell_pairs(pairs)
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    text = object_pattern.sub(fix_object, text)
    return table_pattern.sub(fix_table, text)


def _fix_acad_table_numeric_cell_pairs(pairs: list[list[str]]) -> None:
    cell_value_indexes = [
        index for index, (_, value) in enumerate(pairs) if value == "CELL_VALUE"
    ]
    for cell_value_index in reversed(cell_value_indexes):
        if not _cell_contains_numeric_quantity(pairs, cell_value_index):
            continue
        height_index = _cell_text_height_pair_in_cell_value(pairs, cell_value_index)
        if height_index is None:
            height_index = _cell_text_height_pair_before_cell_value(pairs, cell_value_index)
        if height_index is None:
            cell_value_index = _insert_cell_text_height_pair(pairs, cell_value_index)
        else:
            pairs[height_index][1] = f"{BODY_TEXT_HEIGHT:.1f}"
            cell_value_index = _canonicalize_cell_text_height_pair(pairs, cell_value_index)
            height_index = _cell_text_height_pair_in_cell_value(pairs, cell_value_index)
            if height_index is None:
                height_index = _cell_text_height_pair_before_cell_value(pairs, cell_value_index)
            if height_index is not None:
                pairs[height_index][1] = f"{BODY_TEXT_HEIGHT:.1f}"
        _ensure_cell_text_height_override_flag(pairs, cell_value_index)
        for value_index in _cell_text_value_pair_indexes(pairs, cell_value_index):
            code, raw_value = pairs[value_index]
            if code.strip() not in {"1", "302"}:
                continue
            pairs[value_index][1] = _strip_table_inline_scales(raw_value)


def _insert_cell_text_height_pair(pairs: list[list[str]], cell_value_index: int) -> int:
    for index in range(cell_value_index + 1, min(len(pairs), cell_value_index + 12)):
        if pairs[index][0].strip() == "170":
            pairs.insert(index + 1, ["140", f"{BODY_TEXT_HEIGHT:.1f}"])
            if index + 1 <= cell_value_index:
                return cell_value_index + 1
            return cell_value_index
    insert_at = cell_value_index + 1
    pairs.insert(insert_at, ["140", f"{BODY_TEXT_HEIGHT:.1f}"])
    return cell_value_index + 1


def _canonicalize_cell_text_height_pair(pairs: list[list[str]], cell_value_index: int) -> int:
    height_index = _cell_text_height_pair_before_cell_value(pairs, cell_value_index)
    if height_index is None:
        return cell_value_index

    align_index = _cell_alignment_pair_index_before_cell_value(pairs, cell_value_index)
    if align_index is None:
        return cell_value_index

    target_index = align_index + 1
    if height_index == target_index:
        return cell_value_index

    height_pair = pairs.pop(height_index)
    if height_index < cell_value_index:
        cell_value_index -= 1
    if height_index < target_index:
        target_index -= 1
    pairs.insert(target_index, height_pair)
    if target_index <= cell_value_index:
        cell_value_index += 1
    return cell_value_index


def _ensure_cell_text_height_override_flag(pairs: list[list[str]], cell_value_index: int) -> None:
    for index in range(cell_value_index - 1, max(-1, cell_value_index - 30), -1):
        code, value = pairs[index]
        if value in {"ACVALUE_END", "CELLCONTENT_BEGIN"}:
            break
        if code.strip() != "91":
            continue
        try:
            flag = int(value)
        except ValueError:
            return
        pairs[index][1] = str(flag | CELL_TEXT_HEIGHT_OVERRIDE_BIT)
        return


def _cell_alignment_pair_index_before_cell_value(pairs: list[list[str]], cell_value_index: int) -> int | None:
    for index in range(cell_value_index - 1, max(-1, cell_value_index - 24), -1):
        code, value = pairs[index]
        if value in {"ACVALUE_END", "CELLCONTENT_BEGIN"}:
            break
        if code.strip() == "170":
            return index
    return None


def _numeric_cell_value_pair_indexes(pairs: list[list[str]], cell_value_index: int) -> list[int]:
    indexes: list[int] = []
    for index in _cell_text_value_pair_indexes(pairs, cell_value_index):
        code, raw_value = pairs[index]
        plain = _plain_numeric_token(raw_value)
        if _is_numeric_quantity_cell_text(plain):
            indexes.append(index)
    return indexes


def _cell_text_value_pair_indexes(pairs: list[list[str]], cell_value_index: int) -> list[int]:
    indexes: list[int] = []
    for index in range(cell_value_index + 1, min(len(pairs), cell_value_index + 24)):
        code, raw_value = pairs[index]
        if raw_value in {"ACVALUE_END", "CELLCONTENT_BEGIN", "CELL_VALUE"}:
            break
        if code.strip() in {"1", "302"}:
            indexes.append(index)
    return indexes


def _cell_contains_numeric_quantity(pairs: list[list[str]], cell_value_index: int) -> bool:
    indexes = _cell_text_value_pair_indexes(pairs, cell_value_index)
    if not indexes:
        return False

    combined = "".join(_plain_mtext(pairs[index][1]) for index in indexes).replace(",", ".").strip()
    if _is_numeric_quantity_cell_text(combined):
        return True

    return any(
        _is_numeric_quantity_cell_text(_plain_numeric_token(pairs[index][1]))
        for index in indexes
    )


def _cell_text_height_pair_in_cell_value(pairs: list[list[str]], cell_value_index: int) -> int | None:
    for index in range(cell_value_index + 1, min(len(pairs), cell_value_index + 24)):
        code, value = pairs[index]
        if value == "ACVALUE_END":
            break
        if code.strip() == "140":
            return index
    return None


def _cell_text_height_pair_before_cell_value(pairs: list[list[str]], cell_value_index: int) -> int | None:
    for index in range(cell_value_index - 1, max(-1, cell_value_index - 24), -1):
        code, value = pairs[index]
        if value in {"ACVALUE_END", "CELLCONTENT_BEGIN"}:
            break
        if code.strip() == "140":
            return index
    return None


def _raw_text_content_from_object(object_text: str) -> str:
    pairs, _ = _split_object_pairs(object_text)
    return "".join(value for code, value in pairs if code.strip() in {"1", "3"})


def _normalize_small_inline_heights(text: str) -> str:
    text = re.sub(r"\\H[\d.]+x?;", "", text)
    return text


def _raise_stamp_signature_text(document: Any) -> None:
    if "Штамп фамилии" not in document.blocks:
        return

    for entity in document.blocks["Штамп фамилии"]:
        if entity.dxftype() != "MTEXT":
            continue
        plain = _plain_mtext(_get_text(entity)).strip()
        target_y = _stamp_signature_target_y(plain, entity.dxf.insert.y)
        if target_y is None:
            continue
        insert = entity.dxf.insert
        entity.dxf.insert = (insert.x, target_y, insert.z)


def _stamp_signature_target_y(text: str, insert_y: float | None = None) -> float | None:
    if text == "Суринов" and insert_y is not None:
        if insert_y <= STAMP_SURINOV_TOP_Y_THRESHOLD:
            return STAMP_SURINOV_BOTTOM_TARGET_Y
        return STAMP_SURINOV_TOP_TARGET_Y
    return STAMP_SIGNATURE_TARGET_Y.get(text)


def _adjust_stamp_signature_positions_raw(path: Path) -> None:
    original_text = path.read_text(encoding="utf-8", errors="replace")
    block_pattern = re.compile(
        r"(^  0\nBLOCK\n.*?^  2\nШтамп фамилии\n.*?)(?=^  0\n(?:BLOCK|ENDBLK|ENDSEC))",
        re.DOTALL | re.MULTILINE,
    )
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_block(match: re.Match[str]) -> str:
        block_text = match.group(1)
        rebuilt = block_text
        for object_match in object_pattern.finditer(block_text):
            object_text = object_match.group(1)
            plain = _plain_mtext(_raw_text_content_from_object(object_text)).strip()
            pairs, tail = _split_object_pairs(object_text)
            insert_y = None
            for pair in pairs:
                if pair[0].strip() == "20":
                    try:
                        insert_y = float(pair[1])
                    except ValueError:
                        insert_y = None
                    break
            target_y = _stamp_signature_target_y(plain, insert_y)
            if target_y is None:
                continue
            for pair in pairs:
                if pair[0].strip() == "20":
                    pair[1] = f"{target_y:g}"
                    break
            rebuilt = rebuilt.replace(object_text, _rebuild_dxf_object("MTEXT", pairs, tail, object_text), 1)
        return rebuilt

    updated = block_pattern.sub(fix_block, original_text)
    if updated != original_text:
        path.write_text(updated, encoding="utf-8")


def _fit_specification_long_text_raw(text: str) -> str:
    marker = re.escape("Автоматизированная система управления II категории")
    before_pattern = re.compile(
        rf"((?: 40|140|144)\n\s*)(?:3\.0|2\.5|2\.4|2\.0|1\.4)(?=(?:(?!\n  0\n).){{0,700}}{marker})",
        re.DOTALL,
    )
    after_pattern = re.compile(
        rf"({marker}(?:(?!\n  0\n).){{0,900}}(?: 40|140|144)\n\s*)(?:3\.0|2\.5|2\.4|2\.0|1\.4)",
        re.DOTALL,
    )
    text = before_pattern.sub(rf"\g<1>{LONG_SPEC_TEXT_HEIGHT}", text)
    return after_pattern.sub(rf"\g<1>{LONG_SPEC_TEXT_HEIGHT}", text)


def _normalize_small_inline_heights_raw(text: str) -> str:
    pairs, tail = _split_dxf_pairs(text)
    for pair in pairs:
        code, raw_value = pair
        if code.strip() not in {"1", "2", "3", "302"}:
            continue
        if not _is_body_or_work_table_text(raw_value):
            continue
        pair[1] = _normalize_small_inline_heights(raw_value)

    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(_join_dxf_pairs(pairs, tail)) + suffix


def _set_work_table_row_heights_raw(text: str) -> str:
    object_pattern = re.compile(r"(^  0\nTABLETEMPLATE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_object(match: re.Match[str]) -> str:
        table_object = match.group(1)
        plain = _plain_mtext(table_object)
        if not any(marker in plain for marker in WORK_TABLE_MARKERS):
            return table_object

        row_pattern = re.compile(
            r"(\n  1\nTABLEROW_BEGIN\n(?:(?!\n309\nTABLEROW_END).)*?\n 40\n)([-+]?\d+(?:\.\d+)?)",
            re.DOTALL,
        )

        def fix_row(row_match: re.Match[str]) -> str:
            current_height = float(row_match.group(2))
            if current_height >= MIN_WORK_TABLE_ROW_HEIGHT:
                return row_match.group(0)
            return f"{row_match.group(1)}{MIN_WORK_TABLE_ROW_HEIGHT:g}"

        return row_pattern.sub(fix_row, table_object)

    return object_pattern.sub(fix_object, text)


def _is_project_table_text(table_text: str) -> bool:
    plain = _plain_mtext(table_text)
    return any(
        marker in plain
        for marker in (
            *SPEC_TABLE_MARKERS,
            *WORK_TABLE_MARKERS,
            "Основные показатели",
            "Наименование характеристики",
            "Кол.",
        )
    )


def _normalize_table_style_heights_raw(text: str) -> str:
    object_pattern = re.compile(r"(^  0\nTABLESTYLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_object(match: re.Match[str]) -> str:
        object_text = match.group(1)
        pairs, tail = _split_object_pairs(object_text)
        for pair in pairs:
            if pair[0].strip() != "140":
                continue
            try:
                height = float(pair[1])
            except ValueError:
                continue
            if abs(height - BODY_TEXT_HEIGHT) > 0.001:
                pair[1] = f"{BODY_TEXT_HEIGHT:.1f}"
        return _rebuild_dxf_object("TABLESTYLE", pairs, tail, object_text)

    return object_pattern.sub(fix_object, text)


def _is_climate_table_text(table_text: str) -> bool:
    plain = _plain_mtext(table_text)
    return any(label in plain for label in CLIMATE_TABLE_LABELS)


def _strip_table_cell_inline_scales_raw(text: str) -> str:
    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if not _is_project_table_text(table_text) and not _is_climate_table_text(table_text):
            return table_text
        pairs, tail = _split_object_pairs(table_text)
        for pair in pairs:
            if pair[0].strip() not in {"1", "302"}:
                continue
            pair[1] = _strip_table_inline_scales(pair[1])
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    return table_pattern.sub(fix_table, text)


def _fix_work_table_support_quantities_raw(path: Path, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return

    original_text = path.read_text(encoding="utf-8", errors="replace")
    block_pattern = re.compile(r"(^  0\nBLOCK\n.*?^  0\nENDBLK)", re.DOTALL | re.MULTILINE)
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_block(match: re.Match[str]) -> str:
        block_text = match.group(1)
        if not any(marker in _plain_mtext(block_text) for marker in WORK_TABLE_SUPPORT_MARKERS):
            return block_text

        objects = [object_match.group(1) for object_match in object_pattern.finditer(block_text)]
        rebuilt = block_text
        for index, object_text in enumerate(objects):
            marker = _plain_mtext(_raw_text_content_from_object(object_text)).strip()
            placeholder = _work_table_support_placeholder(marker)
            if not placeholder:
                continue
            value = replacement_map.get(placeholder, "")
            if value == "" and placeholder in {
                "{{P23}}",
                "{{A23}}",
                "{{YA23}}",
                "{{K21}}",
                "{{S}}",
            }:
                value = "0"
            if not value:
                continue
            for next_object in objects[index + 1 :]:
                content = _plain_mtext(_raw_text_content_from_object(next_object)).replace(",", ".").strip()
                if content in {"шт", "м", "км", "м³", "км/кг", "шт/ м³"}:
                    continue
                if not re.fullmatch(r"\d+(?:\.\d+)?", content):
                    continue
                pairs, tail = _split_object_pairs(next_object)
                for pair in pairs:
                    if pair[0].strip() in {"1", "3"}:
                        pair[1] = value
                for pair in pairs:
                    if pair[0].strip() == "40":
                        pair[1] = f"{BODY_TEXT_HEIGHT:.1f}"
                        break
                rebuilt = rebuilt.replace(next_object, _rebuild_dxf_object("MTEXT", pairs, tail, next_object), 1)
                break
        return rebuilt

    updated = block_pattern.sub(fix_block, original_text)
    updated = _fix_work_table_support_quantities_in_acad_tables_raw(updated, replacement_map)
    if updated != original_text:
        path.write_text(updated, encoding="utf-8")


def _fix_climate_table_mtext_values_raw(path: Path, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return
    values = _climate_values_from_map(replacement_map)
    if not values:
        return

    original_text = path.read_text(encoding="utf-8", errors="replace")
    block_pattern = re.compile(r"(^  0\nBLOCK\n.*?^  0\nENDBLK)", re.DOTALL | re.MULTILINE)
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_block(match: re.Match[str]) -> str:
        block_text = match.group(1)
        if "Район по гололеду" not in _plain_mtext(block_text):
            return block_text

        objects = [object_match.group(1) for object_match in object_pattern.finditer(block_text)]
        rebuilt = block_text
        for index, object_text in enumerate(objects):
            plain = _plain_mtext(_raw_text_content_from_object(object_text)).strip()
            for label, value_kind, value_key in CLIMATE_TABLE_ROW_REPLACEMENTS:
                if label not in plain:
                    continue
                replacement = values[value_key]
                for next_object in objects[index + 1 :]:
                    content = _plain_mtext(_raw_text_content_from_object(next_object)).strip()
                    if not _climate_mtext_value_matches(content, value_kind):
                        continue
                    pairs, tail = _split_object_pairs(next_object)
                    for pair in pairs:
                        if pair[0].strip() in {"1", "3", "302"}:
                            pair[1] = _replace_raw_content_value(
                                pair[1], str(replacement), value_kind
                            )
                    rebuilt = rebuilt.replace(
                        next_object,
                        _rebuild_dxf_object("MTEXT", pairs, tail, next_object),
                        1,
                    )
                    break
        return rebuilt

    updated = block_pattern.sub(fix_block, original_text)
    if updated != original_text:
        path.write_text(updated, encoding="utf-8")


def _normalize_numeric_table_cell_heights_raw(text: str) -> str:
    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if not _is_project_table_text(table_text):
            return table_text
        pairs, tail = _split_object_pairs(table_text)
        _fix_acad_table_numeric_cell_pairs(pairs)
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    return table_pattern.sub(fix_table, text)


def _cell_value_is_numeric(pairs: list[list[str]], start: int) -> bool:
    return _cell_contains_numeric_quantity(pairs, start)


def _previous_cell_height_pair(pairs: list[list[str]], start: int) -> int | None:
    for index in range(start, max(-1, start - 12), -1):
        code, raw_value = pairs[index]
        if raw_value in {"CELL_VALUE", "ACVALUE_END", "CELLCONTENT_BEGIN"}:
            return None
        if code.strip() == "140":
            return index
    return None


def _normalize_stamp_title_heights_raw(text: str) -> str:
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_object(match: re.Match[str]) -> str:
        object_text = match.group(1)
        plain = _raw_text_content_from_object(object_text)
        if not _is_stamp_title_mtext(plain):
            return object_text

        pairs, tail = _split_object_pairs(object_text)
        for pair in pairs:
            if pair[0].strip() == "40":
                pair[1] = f"{STAMP_TITLE_TEXT_HEIGHT:.1f}"
            elif pair[0].strip() in {"1", "3"}:
                pair[1] = _strip_table_inline_scales(pair[1])
                pair[1] = re.sub(r"\bземельный участок\b", "з.у.", pair[1], flags=re.IGNORECASE)
        return _rebuild_dxf_object("MTEXT", pairs, tail, object_text)

    return object_pattern.sub(fix_object, text)


def _normalize_breaker_text_heights_raw(text: str) -> str:
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_object(match: re.Match[str]) -> str:
        object_text = match.group(1)
        plain = _plain_mtext(_raw_text_content_from_object(object_text))
        if "ВА47-29" not in plain:
            return object_text

        pairs, tail = _split_object_pairs(object_text)
        for pair in pairs:
            if pair[0].strip() == "40":
                pair[1] = f"{BREAKER_TEXT_HEIGHT:.1f}"
            elif pair[0].strip() in {"1", "3"}:
                pair[1] = _strip_table_inline_scales(pair[1])
        return _rebuild_dxf_object("MTEXT", pairs, tail, object_text)

    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        pairs, tail = _split_object_pairs(table_text)
        cell_value_indexes = [index for index, (_, value) in enumerate(pairs) if value == "CELL_VALUE"]
        for cell_value_index in cell_value_indexes:
            has_breaker = False
            for index in range(cell_value_index + 1, min(len(pairs), cell_value_index + 24)):
                code, raw_value = pairs[index]
                if raw_value in {"ACVALUE_END", "CELL_VALUE"}:
                    break
                if code.strip() not in {"1", "302"}:
                    continue
                if "ВА47-29" not in _plain_mtext(raw_value):
                    continue
                has_breaker = True
                pairs[index][1] = _strip_table_inline_scales(raw_value)
            if not has_breaker:
                continue
            height_index = _cell_text_height_pair_before_cell_value(pairs, cell_value_index)
            if height_index is None:
                align_index = _cell_alignment_pair_index_before_cell_value(pairs, cell_value_index)
                insert_at = align_index + 1 if align_index is not None else cell_value_index
                pairs.insert(insert_at, ["140", f"{BREAKER_TEXT_HEIGHT:.1f}"])
            else:
                pairs[height_index][1] = f"{BREAKER_TEXT_HEIGHT:.1f}"
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    text = object_pattern.sub(fix_object, text)
    return table_pattern.sub(fix_table, text)


def _normalize_numeric_result_mtext_heights_raw(text: str, replacement_map: dict[str, str] | None) -> str:
    values = _numeric_result_values(replacement_map)
    if not values:
        return text

    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_object(match: re.Match[str]) -> str:
        entity_text = match.group(1)
        plain = _plain_mtext(_raw_text_content(entity_text)).replace(",", ".").strip()
        if plain not in values:
            return entity_text
        return re.sub(
            r"(\n 40\n)([-+]?\d+(?:\.\d+)?)",
            lambda height_match: f"{height_match.group(1)}{_min_height_value(height_match.group(2), BODY_TEXT_HEIGHT)}",
            entity_text,
            count=1,
        )

    return object_pattern.sub(fix_object, text)


def _raw_text_content(text: str) -> str:
    pairs, _ = _split_dxf_pairs(text)
    return r"\P".join(value for code, value in pairs if code.strip() in {"1", "3", "302"})


def _min_height_value(raw_value: str, minimum: float) -> str:
    try:
        value = float(raw_value)
    except ValueError:
        return raw_value
    if value <= 0 or value >= minimum:
        return raw_value
    return f"{minimum:g}"


def _apply_climate_replacements_raw(text: str, replacement_map: dict[str, str]) -> str:
    values = _climate_values_from_map(replacement_map)
    if not values:
        return text

    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)
    replacements = (
        ("Район по гололеду", "roman", values["ice_district"]),
        ("Нормативная толщина стенки гололеда", "number", values["ice_thickness"]),
        ("Район по ветру", "roman", values["wind_district"]),
        ("Нормативная скорость ветра", "number", values["wind_speed"]),
        ("Ветровое давление", "number", values["wind_pressure"]),
    )

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        pairs, tail = _split_object_pairs(table_text)
        for index, (_, raw_value) in enumerate(pairs):
            plain = _plain_mtext(raw_value)
            for label, value_kind, replacement_value in replacements:
                if label not in plain:
                    continue
                end = _next_climate_label_pair(pairs, index + 1)
                _replace_climate_row_values_in_pairs(
                    pairs, index + 1, end, str(replacement_value), value_kind
                )
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    return table_pattern.sub(fix_table, text)


def _split_dxf_pairs(text: str) -> tuple[list[list[str]], list[str]]:
    lines = text.splitlines()
    pairs = [[lines[index], lines[index + 1]] for index in range(0, len(lines) - 1, 2)]
    tail = lines[len(pairs) * 2 :]
    return pairs, tail


def _join_dxf_pairs(pairs: list[list[str]], tail: list[str]) -> list[str]:
    lines: list[str] = []
    for code, value in pairs:
        lines.extend((code, value))
    lines.extend(tail)
    return lines


def _next_climate_label_pair(pairs: list[list[str]], start: int) -> int:
    for index in range(start, min(len(pairs), start + 260)):
        plain = _plain_mtext(pairs[index][1])
        if any(label in plain for label in CLIMATE_TABLE_LABELS):
            return index
    return min(len(pairs), start + 260)


def _replace_climate_row_values_in_pairs(
    pairs: list[list[str]],
    start: int,
    end: int,
    replacement_value: str,
    value_kind: str,
) -> None:
    for index in range(start, end):
        code, raw_value = pairs[index]
        if code.strip() not in {"1", "3", "302"}:
            continue
        plain = _plain_mtext(raw_value).strip()
        if value_kind == "roman":
            if not re.fullmatch(r"I|II|III|IV", plain):
                continue
        elif not re.fullmatch(r"\d+(?:[,.]\d+)?", plain):
            continue
        pairs[index][1] = _replace_raw_content_value(raw_value, replacement_value, value_kind)


def _replace_raw_content_value(raw_value: str, replacement_value: str, value_kind: str) -> str:
    if value_kind == "roman":
        pattern = r"IV|III|II|I"
    else:
        pattern = r"\d+(?:[,.]\d+)?"

    if "}" in raw_value and ";" in raw_value:
        return re.sub(rf"(?<=;){pattern}(?=\}})", replacement_value, raw_value, count=1)
    return re.sub(pattern, replacement_value, raw_value, count=1)


def _climate_values_from_map(replacement_map: dict[str, str]) -> dict[str, str]:
    ice_district = replacement_map.get("{{ICE_DISTRICT}}") or replacement_map.get("{{CLIMATE_DISTRICT}}")
    wind_district = replacement_map.get("{{WIND_DISTRICT}}") or replacement_map.get("{{CLIMATE_DISTRICT}}")
    ice_thickness = replacement_map.get("{{ICE_THICKNESS_MM}}")
    wind_speed = replacement_map.get("{{WIND_SPEED_MS}}")
    wind_pressure = replacement_map.get("{{WIND_PRESSURE_PA}}")
    if not all((ice_district, wind_district, ice_thickness, wind_speed, wind_pressure)):
        return {}
    return {
        "ice_district": ice_district,
        "wind_district": wind_district,
        "ice_thickness": ice_thickness,
        "wind_speed": wind_speed,
        "wind_pressure": wind_pressure,
    }


def _fix_project_indicator_table_values(path: Path, replacement_map: dict[str, str]) -> None:
    line_length_m = replacement_map.get("{{LINE_LENGTH_M}}", "")
    line_length_km = replacement_map.get("{{LINE_LENGTH_KM}}", "")
    if not line_length_m or not line_length_km or line_length_m == line_length_km:
        return

    original_text = path.read_text(encoding="utf-8", errors="replace")
    lines = original_text.splitlines()
    label_indices = [
        index
        for index, line in enumerate(lines)
        if "Строительная длина ВЛИ-0,4 кВ" in _plain_mtext(line)
        or "Строительная длина линии" in _plain_mtext(line)
    ]
    if not label_indices:
        return

    changed = False
    for label_index in label_indices:
        window_end = _next_text_window_end(lines, label_indices, label_index)
        window = lines[label_index:window_end]
        if not any(_plain_mtext(line).strip() == "км" for line in window):
            continue
        changed = _replace_text_code_value_in_window(
            lines,
            label_index,
            window_end,
            line_length_m,
            line_length_km,
        ) or changed

    if changed:
        suffix = "\n" if original_text.endswith("\n") else ""
        path.write_text("\n".join(lines) + suffix, encoding="utf-8")


def _next_text_window_end(lines: list[str], label_indices: list[int], label_index: int) -> int:
    later_labels = [index for index in label_indices if index > label_index]
    return min(later_labels[0] if later_labels else label_index + 2200, len(lines))


def _is_text_content_group_code_line(line: str) -> bool:
    return bool(re.fullmatch(r" {1,3}(1|3|302)\s*", line))


def _replace_text_code_value_in_window(
    lines: list[str],
    start: int,
    end: int,
    old_value: str,
    new_value: str,
) -> bool:
    changed = False
    for index in range(start + 1, end):
        if not _is_text_content_group_code_line(lines[index - 1]):
            continue
        plain = _plain_mtext(lines[index]).strip()
        if plain not in {old_value, old_value.replace(".", ",")}:
            continue
        lines[index] = _replace_raw_content_value(lines[index], new_value, "number")
        changed = True
    return changed


def _is_left_aligned_body_mtext(entity: Any, text: str) -> bool:
    char_height = float(getattr(entity.dxf, "char_height", 0) or 0)
    if char_height > 8:
        return False
    return any(marker in text for marker in LEFT_ALIGNED_BODY_MARKERS)


def _plain_mtext(text: str) -> str:
    result = re.sub(r"\\[A-Za-z][^;{}\\]*(?:;)?", " ", text)
    result = result.replace("{", " ").replace("}", " ")
    return re.sub(r"\s+", " ", result).strip()


def _update_sheet_count_entities(document: Any, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return
    route_sheet = replacement_map.get("{{ROUTE_PLAN_SHEET}}", "")
    total_sheets = str(replacement_map.get("{{TOTAL_SHEETS}}", "") or "")
    if route_sheet:
        _update_route_plan_sheet_entities(document, route_sheet)
    _update_total_sheet_stamp_entities(document, total_sheets)


def _update_route_plan_sheet_entities(document: Any, route_sheet: str) -> None:
    for block in document.blocks:
        entities = [entity for entity in block if entity.dxftype() in {"TEXT", "MTEXT", "ATTRIB"}]
        for index, entity in enumerate(entities):
            text = _get_text(entity)
            if not text or ROUTE_PLAN_SHEET_LABEL not in text:
                continue
            for prev in reversed(entities[:index]):
                prev_text = _get_text(prev)
                if not prev_text:
                    continue
                plain = _plain_mtext(prev_text).strip()
                if re.fullmatch(r"\d+(?:-\d+)?", plain):
                    _set_text(prev, route_sheet)
                    break

    for layout in document.layouts:
        for entity in layout:
            if entity.dxftype() not in {"TEXT", "MTEXT", "ATTRIB"}:
                continue
            text = _get_text(entity)
            if not text or ROUTE_PLAN_SHEET_LABEL not in text:
                continue
            insert = getattr(entity.dxf, "insert", None)
            if insert is None:
                continue
            best_entity = None
            best_distance = None
            for candidate in layout:
                if candidate.dxftype() not in {"TEXT", "MTEXT"}:
                    continue
                candidate_text = _get_text(candidate)
                if not candidate_text:
                    continue
                plain = _plain_mtext(candidate_text).strip()
                if not re.fullmatch(r"\d+(?:-\d+)?", plain):
                    continue
                candidate_insert = candidate.dxf.insert
                if candidate_insert.y > insert.y or abs(candidate_insert.x - insert.x) > 20:
                    continue
                distance = abs(candidate_insert.x - insert.x) + abs(candidate_insert.y - insert.y)
                if best_distance is None or distance < best_distance:
                    best_entity = candidate
                    best_distance = distance
            if best_entity is not None:
                _set_text(best_entity, route_sheet)


def _update_total_sheet_stamp_entities(document: Any, total_sheets: str) -> None:
    if not total_sheets:
        return
    for insert in document.modelspace().query("INSERT"):
        if insert.dxf.name not in STAMP_BLOCK_NAMES:
            continue
        target_x = float(insert.dxf.insert.x) + STAMP_TOTAL_SHEETS_OFFSET[0]
        target_y = float(insert.dxf.insert.y) + STAMP_TOTAL_SHEETS_OFFSET[1]
        best_entity = None
        best_distance = None
        for entity in document.modelspace().query("TEXT"):
            plain = entity.dxf.text.strip()
            if not plain.isdigit():
                continue
            pos = entity.dxf.insert
            distance = abs(pos.x - target_x) + abs(pos.y - target_y)
            if distance > sum(STAMP_FIELD_TOLERANCE):
                continue
            if best_distance is None or distance < best_distance:
                best_entity = entity
                best_distance = distance
        if best_entity is not None:
            best_entity.dxf.text = total_sheets


def _apply_sheet_count_replacements_raw(path: Path, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return
    route_sheet = replacement_map.get("{{ROUTE_PLAN_SHEET}}", "")
    total_sheets = str(replacement_map.get("{{TOTAL_SHEETS}}", "") or "")
    original_text = path.read_text(encoding="utf-8", errors="replace")
    text = original_text
    if route_sheet:
        text = _replace_route_plan_sheet_table_cells_raw(text, route_sheet)
        text = _replace_route_plan_sheet_mtext_blocks_raw(text, route_sheet)
    text = _replace_stamp_total_sheets_raw(text, total_sheets)
    if text != original_text:
        path.write_text(text, encoding="utf-8")


def _replace_route_plan_sheet_table_cells_raw(text: str, route_sheet: str) -> str:
    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if ROUTE_PLAN_SHEET_LABEL not in table_text:
            return table_text
        pairs, tail = _split_object_pairs(table_text)
        route_indexes = [
            index
            for index, (code, raw_value) in enumerate(pairs)
            if code.strip() in {"1", "302"} and ROUTE_PLAN_SHEET_LABEL in raw_value
        ]
        if not route_indexes:
            return table_text
        for route_index in route_indexes:
            for index in range(route_index - 1, max(-1, route_index - 30), -1):
                code, raw_value = pairs[index]
                if code.strip() not in {"1", "302"}:
                    continue
                plain = _plain_mtext(raw_value).strip()
                if re.fullmatch(r"\d+(?:-\d+)?", plain):
                    pairs[index][1] = route_sheet
                    break
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    return table_pattern.sub(fix_table, text)


def _replace_route_plan_sheet_mtext_blocks_raw(text: str, route_sheet: str) -> str:
    block_pattern = re.compile(r"(^  0\nBLOCK\n.*?^  0\nENDBLK)", re.DOTALL | re.MULTILINE)
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_block(match: re.Match[str]) -> str:
        block_text = match.group(1)
        if ROUTE_PLAN_SHEET_LABEL not in block_text:
            return block_text

        objects = [object_match.group(1) for object_match in object_pattern.finditer(block_text)]
        rebuilt = block_text
        for index, object_text in enumerate(objects):
            content = _raw_text_content_from_object(object_text)
            if ROUTE_PLAN_SHEET_LABEL not in content:
                continue
            for prev_object in reversed(objects[:index]):
                plain = _plain_mtext(_raw_text_content_from_object(prev_object)).strip()
                if not re.fullmatch(r"\d+(?:-\d+)?", plain):
                    continue
                pairs, tail = _split_object_pairs(prev_object)
                for pair in pairs:
                    if pair[0].strip() in {"1", "3"}:
                        pair[1] = route_sheet
                rebuilt = rebuilt.replace(
                    prev_object,
                    _rebuild_dxf_object("MTEXT", pairs, tail, prev_object),
                    1,
                )
                break
        return rebuilt

    return block_pattern.sub(fix_block, text)


def _replace_stamp_total_sheets_raw(text: str, total_sheets: str) -> str:
    if not total_sheets:
        return text
    lines = text.splitlines()
    insert_positions: list[tuple[int, float, float]] = []
    for index, line in enumerate(lines):
        if line.strip() != "INSERT":
            continue
        name = ""
        x_value = None
        y_value = None
        for offset in range(1, 30):
            if index + offset >= len(lines):
                break
            code = lines[index + offset].strip()
            if code == "2" and not name:
                name = lines[index + offset + 1].strip()
            if code == "10":
                x_value = float(lines[index + offset + 1].strip())
            if code == "20":
                y_value = float(lines[index + offset + 1].strip())
                break
        if name in STAMP_BLOCK_NAMES and x_value is not None and y_value is not None:
            insert_positions.append((index, x_value, y_value))

    text_entities: list[tuple[int, float, float, str]] = []
    for index, line in enumerate(lines):
        if line.strip() != "TEXT":
            continue
        x_value = None
        y_value = None
        text_value = ""
        for offset in range(1, 20):
            if index + offset >= len(lines):
                break
            code = lines[index + offset].strip()
            if code == "10":
                x_value = float(lines[index + offset + 1].strip())
            elif code == "20":
                y_value = float(lines[index + offset + 1].strip())
            elif code == "1":
                text_value = lines[index + offset + 1]
                break
        if x_value is None or y_value is None or not text_value.strip().isdigit():
            continue
        text_entities.append((index, x_value, y_value, text_value.strip()))

    changed = False
    for _, insert_x, insert_y in insert_positions:
        target_x = insert_x + STAMP_TOTAL_SHEETS_OFFSET[0]
        target_y = insert_y + STAMP_TOTAL_SHEETS_OFFSET[1]
        best = None
        best_distance = None
        for text_index, x_value, y_value, current_value in text_entities:
            distance = abs(x_value - target_x) + abs(y_value - target_y)
            if distance > sum(STAMP_FIELD_TOLERANCE):
                continue
            if best_distance is None or distance < best_distance:
                best = (text_index, current_value)
                best_distance = distance
        if best is None:
            continue
        text_index, current_value = best
        if current_value == total_sheets:
            continue
        value_line_index = text_index + 1
        while value_line_index < len(lines) and lines[value_line_index].strip() != "1":
            value_line_index += 1
        if value_line_index + 1 < len(lines):
            lines[value_line_index + 1] = total_sheets
            changed = True

    return "\n".join(lines) if changed else text


def _fix_labeled_spec_table_values_raw(path: Path, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return
    replacements = {
        ZP6_TABLE_LABEL: replacement_map.get("{{ZP6}}", ""),
    }
    replacements = {label: value for label, value in replacements.items() if value}
    if not replacements:
        return

    original_text = path.read_text(encoding="utf-8", errors="replace")
    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if not _is_project_table_text(table_text):
            return table_text
        pairs, tail = _split_object_pairs(table_text)
        label_indexes = [
            index
            for index, (code, raw_value) in enumerate(pairs)
            if code.strip() in {"1", "302"} and any(label in _plain_mtext(raw_value) for label in replacements)
        ]
        if not label_indexes:
            return table_text
        for label_index in label_indexes:
            label_plain = _plain_mtext(pairs[label_index][1]).strip()
            replacement = next(
                (value for marker, value in replacements.items() if marker in label_plain),
                "",
            )
            if not replacement:
                continue
            for index in range(label_index + 1, min(len(pairs), label_index + 40)):
                code, raw_value = pairs[index]
                if code.strip() not in {"1", "302"}:
                    continue
                plain = _plain_mtext(raw_value).replace(",", ".").strip()
                if not re.fullmatch(r"\d+(?:\.\d+)?", plain):
                    continue
                pairs[index][1] = replacement
                height_index = _previous_cell_height_pair(pairs, index - 1)
                if height_index is not None:
                    pairs[height_index][1] = _min_height_value(pairs[height_index][1], BODY_TEXT_HEIGHT)
                break
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    updated = table_pattern.sub(fix_table, original_text)
    if updated != original_text:
        path.write_text(updated, encoding="utf-8")


def _resolve_sip4_spec_table_values(replacement_map: dict[str, str]) -> tuple[str, str] | None:
    sech_sip4 = replacement_map.get("{{SECH_SIP4}}", "")
    sip4_kg = format_sip4_spec_table_kg(sech_sip4)
    if not sech_sip4 or not sip4_kg:
        return None
    return SIP4_SPEC_TABLE_KM_DISPLAY, sip4_kg


def _is_spec_certificate_text(raw_value: str) -> bool:
    collapsed = re.sub(r"\\[Pp]", " ", raw_value)
    plain = _plain_mtext(collapsed)
    if SPEC_CERTIFICATE_PPD_PATTERN.search(plain) or SPEC_CERTIFICATE_PPD_PATTERN.search(raw_value):
        return bool(
            SPEC_CERTIFICATE_DATE_PATTERN.search(collapsed)
            or SPEC_CERTIFICATE_DATE_PATTERN.search(plain)
            or SPEC_CERTIFICATE_DATE_PATTERN.search(raw_value)
        )
    if "по" not in plain.lower():
        return False
    return bool(SPEC_CERTIFICATE_TEXT_PATTERN.search(plain))


def _normalize_certificate_text_content(raw_value: str) -> str:
    return re.sub(r"\\T[\d.]+;", "", raw_value)


def _apply_sip4_numeric_width_to_text(text_value: str) -> str:
    stripped = text_value.strip()
    inner = stripped.lstrip("{").rstrip("}")
    if r"\W" in inner:
        return text_value
    inner = re.sub(r"\\T[\d.]+;", "", inner)
    formatted = rf"\W{SIP4_NUMERIC_WIDTH_FACTOR:.5f};{inner}"
    if stripped.startswith("{"):
        suffix = "}" if stripped.endswith("}") else ""
        return "{" + formatted + suffix
    return formatted


def _is_sip4_spec_row_label(raw_value: str) -> bool:
    collapsed = re.sub(r"\\[Pp]", " ", raw_value)
    plain = _plain_mtext(collapsed)
    return all(marker in plain for marker in SIP4_TABLE_ROW_MARKERS) and "СИП2" not in plain


def _preserve_braced_table_cell(raw_value: str, new_plain: str) -> str:
    stripped = raw_value.strip()
    if stripped.startswith("{"):
        suffix = "}" if stripped.endswith("}") else ""
        return "{" + new_plain + suffix
    return new_plain



def _mtext_owner_handle(object_text: str) -> str:
    pairs, _ = _split_object_pairs(object_text)
    for code, value in pairs:
        if code.strip() == "330":
            return value.strip()
    return ""


def _mtext_text_pair_index(pairs: list[list[str]]) -> int | None:
    for index, (code, _) in enumerate(pairs):
        if code.strip() == "1":
            return index
    return None


def _is_numeric_table_cell(raw_value: str) -> bool:
    plain = _plain_mtext(raw_value).replace(",", ".").strip()
    plain = plain.lstrip("{").rstrip("}")
    return _is_numeric_quantity_cell_text(plain)


def _format_table_number_like_old(old_raw: str, new_value: str) -> str:
    raw_plain = old_raw.strip().lstrip("{").rstrip("}")
    formatted = new_value.replace(".", ",") if "," in raw_plain else new_value
    return _preserve_braced_table_cell(old_raw, formatted)


def _fix_sip4_acad_table_pairs_text(text: str, km_display: str, sip4_kg: str) -> str:
    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if not _is_project_table_text(table_text):
            return table_text
        pairs, tail = _split_object_pairs(table_text)
        label_indexes = [
            index
            for index, (code, raw_value) in enumerate(pairs)
            if code.strip() in {"1", "302"} and _is_sip4_spec_row_label(raw_value)
        ]
        if not label_indexes:
            return table_text
        for label_index in label_indexes:
            for index in range(label_index + 1, min(len(pairs), label_index + 80)):
                code, raw_value = pairs[index]
                if code.strip() not in {"1", "302"}:
                    continue
                if _plain_mtext(raw_value).strip() != "км":
                    continue
                updated = 0
                for value_index in range(index + 1, min(len(pairs), index + 80)):
                    value_code, value_raw = pairs[value_index]
                    if value_code.strip() not in {"1", "302"}:
                        continue
                    if not _is_numeric_table_cell(value_raw):
                        continue
                    new_plain = km_display if updated == 0 else sip4_kg
                    pairs[value_index][1] = _format_table_number_like_old(value_raw, new_plain)
                    height_index = _previous_cell_height_pair(pairs, value_index - 1)
                    if height_index is not None:
                        pairs[height_index][1] = _min_height_value(pairs[height_index][1], BODY_TEXT_HEIGHT)
                    updated += 1
                    if updated == 2:
                        break
                break
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    return table_pattern.sub(fix_table, text)


def _fix_sip4_spec_table_values_raw(path: Path, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map:
        return
    resolved = _resolve_sip4_spec_table_values(replacement_map)
    if resolved is None:
        return

    km_display, sip4_kg = resolved
    mtext_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)
    original_text = path.read_text(encoding="utf-8", errors="replace")

    def fix_text(text: str) -> str:
        matches = list(mtext_pattern.finditer(text))
        if not matches:
            return text

        objects: list[dict[str, Any]] = []
        for match in matches:
            object_text = match.group(1)
            pairs, tail = _split_object_pairs(object_text)
            text_pair_index = _mtext_text_pair_index(pairs)
            if text_pair_index is None:
                continue
            objects.append(
                {
                    "object_text": object_text,
                    "pairs": pairs,
                    "tail": tail,
                    "text_pair_index": text_pair_index,
                    "text": pairs[text_pair_index][1],
                    "owner": _mtext_owner_handle(object_text),
                }
            )

        replacements: list[tuple[str, str]] = []
        for index, item in enumerate(objects):
            if not _is_sip4_spec_row_label(item["text"]):
                continue
            owner = item["owner"]
            for next_index in range(index + 1, min(len(objects), index + 15)):
                next_item = objects[next_index]
                if owner and next_item["owner"] != owner:
                    break
                if _plain_mtext(next_item["text"]).strip() != "км":
                    continue
                updated = 0
                for value_index in range(next_index + 1, min(len(objects), next_index + 8)):
                    value_item = objects[value_index]
                    if owner and value_item["owner"] != owner:
                        break
                    if not _is_numeric_table_cell(value_item["text"]):
                        continue
                    new_plain = km_display if updated == 0 else sip4_kg
                    value_item["pairs"][value_item["text_pair_index"]][1] = _format_table_number_like_old(
                        value_item["text"],
                        new_plain,
                    )
                    new_object = _rebuild_dxf_object(
                        "MTEXT",
                        value_item["pairs"],
                        value_item["tail"],
                        value_item["object_text"],
                    )
                    replacements.append((value_item["object_text"], new_object))
                    updated += 1
                    if updated == 2:
                        break
                break

        if not replacements:
            return text

        result = text
        for old_object, new_object in replacements:
            result = result.replace(old_object, new_object, 1)
        return result

    updated = fix_text(original_text)
    updated = _fix_sip4_acad_table_pairs_text(updated, km_display, sip4_kg)
    if updated != original_text:
        path.write_text(updated, encoding="utf-8")


def _cell_value_index_before_pair(pairs: list[list[str]], pair_index: int) -> int | None:
    for index in range(pair_index, max(-1, pair_index - 30), -1):
        code, value = pairs[index]
        if code.strip() == "301" and value == "CELL_VALUE":
            return index
    return None


def _apply_sip4_numeric_width_to_mtext_text(text: str) -> str:
    mtext_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)
    matches = list(mtext_pattern.finditer(text))
    if not matches:
        return text

    objects: list[dict[str, Any]] = []
    for match in matches:
        object_text = match.group(1)
        pairs, tail = _split_object_pairs(object_text)
        text_pair_index = _mtext_text_pair_index(pairs)
        if text_pair_index is None:
            continue
        objects.append(
            {
                "object_text": object_text,
                "pairs": pairs,
                "tail": tail,
                "text_pair_index": text_pair_index,
                "text": pairs[text_pair_index][1],
                "owner": _mtext_owner_handle(object_text),
            }
        )

    replacements: list[tuple[str, str]] = []
    for index, item in enumerate(objects):
        if not _is_sip4_spec_row_label(item["text"]):
            continue
        owner = item["owner"]
        for next_index in range(index + 1, min(len(objects), index + 15)):
            next_item = objects[next_index]
            if owner and next_item["owner"] != owner:
                break
            if _plain_mtext(next_item["text"]).strip() != "км":
                continue
            updated = 0
            for value_index in range(next_index + 1, min(len(objects), next_index + 8)):
                value_item = objects[value_index]
                if owner and value_item["owner"] != owner:
                    break
                if not _is_numeric_table_cell(value_item["text"]):
                    continue
                value_item["pairs"][value_item["text_pair_index"]][1] = _apply_sip4_numeric_width_to_text(
                    value_item["pairs"][value_item["text_pair_index"]][1]
                )
                new_object = _rebuild_dxf_object(
                    "MTEXT",
                    value_item["pairs"],
                    value_item["tail"],
                    value_item["object_text"],
                )
                replacements.append((value_item["object_text"], new_object))
                updated += 1
                if updated == 2:
                    break
            break

    result = text
    for old_object, new_object in replacements:
        result = result.replace(old_object, new_object, 1)
    return result


def _apply_sip4_numeric_width_to_acad_table_text(text: str) -> str:
    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if not _is_project_table_text(table_text):
            return table_text
        pairs, tail = _split_object_pairs(table_text)
        label_indexes = [
            index
            for index, (code, raw_value) in enumerate(pairs)
            if code.strip() in {"1", "302"} and _is_sip4_spec_row_label(raw_value)
        ]
        if not label_indexes:
            return table_text
        for label_index in label_indexes:
            for index in range(label_index + 1, min(len(pairs), label_index + 80)):
                code, raw_value = pairs[index]
                if code.strip() not in {"1", "302"}:
                    continue
                if _plain_mtext(raw_value).strip() != "км":
                    continue
                updated = 0
                for value_index in range(index + 1, min(len(pairs), index + 80)):
                    value_code, value_raw = pairs[value_index]
                    if value_code.strip() not in {"1", "302"}:
                        continue
                    if not _is_numeric_table_cell(value_raw):
                        continue
                    pairs[value_index][1] = _apply_sip4_numeric_width_to_text(value_raw)
                    updated += 1
                    if updated == 2:
                        break
                break
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    return table_pattern.sub(fix_table, text)


def _fix_sip4_numeric_width_raw(path: Path, replacement_map: dict[str, str] | None) -> None:
    if not replacement_map or _resolve_sip4_spec_table_values(replacement_map) is None:
        return

    original_text = path.read_text(encoding="utf-8", errors="replace")
    updated = _apply_sip4_numeric_width_to_mtext_text(original_text)
    updated = _apply_sip4_numeric_width_to_acad_table_text(updated)
    if updated != original_text:
        path.write_text(updated, encoding="utf-8")


def _fix_spec_certificate_text_in_acad_table_text(text: str) -> str:
    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if not _is_project_table_text(table_text):
            return table_text
        pairs, tail = _split_object_pairs(table_text)
        changed = False
        for index, (code, raw_value) in enumerate(pairs):
            if code.strip() not in {"1", "302"}:
                continue
            if not _is_spec_certificate_text(raw_value):
                continue
            pairs[index][1] = _normalize_certificate_text_content(raw_value)
            cell_value_index = _cell_value_index_before_pair(pairs, index)
            if cell_value_index is not None:
                height_index = _cell_text_height_pair_before_cell_value(pairs, cell_value_index)
                if height_index is None:
                    align_index = _cell_alignment_pair_index_before_cell_value(pairs, cell_value_index)
                    insert_at = align_index + 1 if align_index is not None else cell_value_index
                    pairs.insert(insert_at, ["140", f"{SPEC_CERTIFICATE_TEXT_HEIGHT:.1f}"])
                else:
                    pairs[height_index][1] = f"{SPEC_CERTIFICATE_TEXT_HEIGHT:.1f}"
            changed = True
        if not changed:
            return table_text
        return _rebuild_dxf_object("ACAD_TABLE", pairs, tail, table_text)

    return table_pattern.sub(fix_table, text)


def _fix_spec_certificate_text_heights_raw(path: Path) -> None:
    original_text = path.read_text(encoding="utf-8", errors="replace")
    mtext_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_mtext(match: re.Match[str]) -> str:
        object_text = match.group(1)
        pairs, tail = _split_object_pairs(object_text)
        text_pair_index = _mtext_text_pair_index(pairs)
        if text_pair_index is None:
            return object_text
        text = pairs[text_pair_index][1]
        if not _is_spec_certificate_text(text):
            return object_text
        for pair in pairs:
            if pair[0].strip() == "40":
                pair[1] = f"{SPEC_CERTIFICATE_TEXT_HEIGHT:.1f}"
        pairs[text_pair_index][1] = _normalize_certificate_text_content(text)
        return _rebuild_dxf_object("MTEXT", pairs, tail, object_text)

    updated = mtext_pattern.sub(fix_mtext, original_text)
    updated = _fix_spec_certificate_text_in_acad_table_text(updated)
    if updated != original_text:
        path.write_text(updated, encoding="utf-8")


def _left_anchor_mtext_if_needed(entity: Any) -> None:
    attachment_point = getattr(entity.dxf, "attachment_point", None)
    if attachment_point not in {2, 5, 8}:
        return

    width = float(getattr(entity.dxf, "width", 0) or 0)
    if width <= 0:
        return

    insert = entity.dxf.insert
    entity.dxf.insert = (insert.x - width / 2, insert.y, insert.z)
    entity.dxf.attachment_point = {2: 1, 5: 4, 8: 7}[attachment_point]


def _is_equipment_footnote_mtext(text: str) -> bool:
    return EQUIPMENT_FOOTNOTE_MARKER in _plain_mtext(text)


def _format_equipment_footnote_text(text: str) -> str:
    stripped = text.lstrip()
    if stripped.startswith(r"\px"):
        return text
    return rf"\pxql;{stripped}"


def _left_align_equipment_footnote_entities(document: Any) -> None:
    for entity in _iter_text_entities(document):
        if entity.dxftype() != "MTEXT":
            continue
        text = _get_text(entity)
        if not _is_equipment_footnote_mtext(text):
            continue
        attachment = int(entity.dxf.attachment_point)
        width = float(getattr(entity.dxf, "width", 0) or 0)
        if attachment == 4 and width > 0:
            insert = entity.dxf.insert
            entity.dxf.attachment_point = 5
            entity.dxf.insert = (insert.x + width / 2, insert.y, insert.z)
        fixed_text = _format_equipment_footnote_text(text)
        if fixed_text != text:
            _set_text(entity, fixed_text)


def _left_align_equipment_footnote_raw(path: Path) -> None:
    object_pattern = re.compile(r"(^  0\nMTEXT\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)
    original_text = path.read_text(encoding="utf-8", errors="replace")

    def fix_object(match: re.Match[str]) -> str:
        object_text = match.group(1)
        raw_text = _raw_text_content_from_object(object_text)
        if not _is_equipment_footnote_mtext(raw_text):
            return object_text

        pairs, tail = _split_object_pairs(object_text)
        width = 0.0
        insert_index: int | None = None
        attachment_index: int | None = None
        text_indexes = [
            index for index, (code, _) in enumerate(pairs) if code.strip() in {"1", "3"}
        ]
        changed = False
        for index, (code, value) in enumerate(pairs):
            stripped = code.strip()
            if stripped == "41":
                width = float(value or 0)
            elif stripped == "10":
                insert_index = index
            elif stripped == "71":
                attachment_index = index

        if attachment_index is not None and insert_index is not None:
            attachment = int(float(pairs[attachment_index][1] or 0))
            if attachment == 4 and width > 0:
                current_x = float(pairs[insert_index][1])
                pairs[attachment_index][1] = "5"
                pairs[insert_index][1] = str(current_x + width / 2)
                changed = True

        fixed_text = _format_equipment_footnote_text(raw_text)
        if fixed_text != raw_text and text_indexes:
            _assign_mtext_dxf_chunks(pairs, fixed_text)
            changed = True

        if not changed:
            return object_text
        return _rebuild_dxf_object("MTEXT", pairs, tail, object_text)

    updated = object_pattern.sub(fix_object, original_text)
    if updated != original_text:
        path.write_text(updated, encoding="utf-8")


def _move_climate_table_down(document: Any) -> None:
    for entity in document.modelspace():
        if entity.dxftype() != "ACAD_TABLE":
            continue
        insert = getattr(entity.dxf, "insert", None)
        if insert is None:
            continue
        if not 3300 <= insert.x <= 3600:
            continue
        if 2020 <= insert.y <= 2045:
            entity.dxf.insert = (insert.x, insert.y + CLIMATE_TABLE_SHIFT_Y, insert.z)
        elif 1995 <= insert.y <= 2019:
            entity.dxf.insert = (insert.x, insert.y + CLIMATE_TABLE_FINE_SHIFT_Y, insert.z)


def _move_climate_table_down_raw(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    table_pattern = re.compile(r"(^  0\nACAD_TABLE\n.*?)(?=^  0\n[A-Z_]+|\Z)", re.DOTALL | re.MULTILINE)

    def fix_table(match: re.Match[str]) -> str:
        table_text = match.group(1)
        if not _is_climate_table_text(table_text):
            return table_text
        coords = re.search(
            r" 10\n([-+]?\d+(?:\.\d+)?)\n 20\n([-+]?\d+(?:\.\d+)?)(\n 30\n)",
            table_text,
        )
        if not coords:
            return table_text
        x = float(coords.group(1))
        y = float(coords.group(2))
        shift = 0.0
        if 3300 <= x <= 3600 and 2020 <= y <= 2045:
            shift = CLIMATE_TABLE_SHIFT_Y
        elif 3300 <= x <= 3600 and 1995 <= y <= 2019:
            shift = CLIMATE_TABLE_FINE_SHIFT_Y
        if not shift:
            return table_text
        new_y = y + shift
        replacement = f" 10\n{coords.group(1)}\n 20\n{new_y}{coords.group(3)}"
        return table_text.replace(coords.group(0), replacement, 1)

    moved_text = table_pattern.sub(fix_table, text)
    if moved_text != text:
        path.write_text(moved_text, encoding="utf-8")


def _move_reference_docs_table_down(document: Any) -> None:
    for entity in document.modelspace():
        if entity.dxftype() != "ACAD_TABLE":
            continue
        insert = getattr(entity.dxf, "insert", None)
        if insert is None:
            continue
        if 3000 <= insert.x <= 3100 and 2048 <= insert.y <= 2054:
            entity.dxf.insert = (insert.x, insert.y + REFERENCE_DOCS_TABLE_SHIFT_Y, insert.z)


def _move_reference_docs_table_down_raw(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(
        r"(  0\nACAD_TABLE\n.*? 10\n([-+]?\d+(?:\.\d+)?)\n 20\n)([-+]?\d+(?:\.\d+)?)(\n 30\n)",
        re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        x = float(match.group(2))
        y = float(match.group(3))
        if 3000 <= x <= 3100 and 2048 <= y <= 2054:
            return f"{match.group(1)}{y + REFERENCE_DOCS_TABLE_SHIFT_Y}{match.group(4)}"
        return match.group(0)

    moved_text, count = pattern.subn(replace, text)
    if count:
        path.write_text(moved_text, encoding="utf-8")


def _iter_text_entities(document: Any):
    for layout in document.layouts:
        for entity in layout:
            if entity.dxftype() in {"TEXT", "MTEXT"}:
                yield entity

    for block in document.blocks:
        for entity in block:
            if entity.dxftype() in {"TEXT", "MTEXT"}:
                yield entity


def _get_text(entity: Any) -> str:
    if entity.dxftype() == "MTEXT":
        return entity.text
    return entity.dxf.text


def _set_text(entity: Any, text: str) -> None:
    if entity.dxftype() == "MTEXT":
        entity.text = text
    else:
        entity.dxf.text = text


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]
