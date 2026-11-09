from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import ezdxf

from backend.cad.oda_dwg_adapter import (
    ROUTE_PLAN_SHEET_LABEL,
    STAMP_BLOCK_NAMES,
    STAMP_FIELD_TOLERANCE,
    STAMP_TOTAL_SHEETS_OFFSET,
    WORK_TABLE_SUPPORT_MARKERS,
    _get_text,
    _iter_text_entities,
    _plain_mtext,
    _work_table_support_placeholder,
    convert_dwg_to_dxf_with_oda,
    find_placeholders_in_dwg_file,
)
from backend.core.cable_format import format_cable_section_display


PHASE_VALUES = ("трехфазный", "однофазный", "трёхфазный", "однофазный")
ARMATURE_ROW_LABELS = {
    "F207": ("F207",),
    "NC20": ("NC20",),
    "ES15": ("ES15", "ES1500E"),
    "CS10": ("CS10", "CS10.3"),
    "PA15": ("PA15", "PA1500"),
    "CD35": ("CD35",),
    "E778": ("E778",),
    "P72": ("P72",),
    "P95": ("P95",),
    "P645": ("P645",),
    "GR": ("GR",),
}


def load_note_document(note_path: Path, work_dir: Path) -> Any:
    note_path = Path(note_path)
    work_dir = Path(work_dir)
    if note_path.suffix.lower() == ".dxf":
        return ezdxf.readfile(note_path)
    dxf_path = work_dir / "temp" / f"{note_path.stem}_validate.dxf"
    dxf_path.parent.mkdir(parents=True, exist_ok=True)
    convert_dwg_to_dxf_with_oda(note_path, dxf_path, work_dir)
    return ezdxf.readfile(dxf_path)


def collect_plain_corpus(document: Any) -> str:
    chunks: list[str] = []
    for entity in _iter_text_entities(document):
        plain = _plain_mtext(_get_text(entity)).strip()
        if plain:
            chunks.append(plain)
    return _normalize_corpus(" ".join(chunks))


def validate_filled_note(
    note_path: Path,
    work_dir: Path,
    replacement_map: dict[str, str],
    tu_data: dict[str, Any],
    project_number: str,
) -> list[Any]:
    from backend.core.validation import NOTE_FIELD_LOCATIONS, ValidationIssue

    issues: list[Any] = []
    document = load_note_document(note_path, work_dir)
    corpus = collect_plain_corpus(document)

    unresolved = find_placeholders_in_dwg_file(note_path, work_dir)
    if unresolved:
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_UNRESOLVED_PLACEHOLDERS",
                message="Не заменены placeholders: " + ", ".join(unresolved),
                location="по тексту записки",
            )
        )

    if not project_number:
        issues.append(
            ValidationIssue(
                category="project",
                severity="warning",
                code="PROJECT_NUMBER_EMPTY",
                message="Укажите номер проекта в основной форме для проверки титульного листа.",
                field="PROJNUMB",
                location=NOTE_FIELD_LOCATIONS["PROJNUMB"],
            )
        )
    else:
        expected = replacement_map.get("{{PROJNUMB}}", "")
        if expected and not _value_matches(corpus, expected):
            issues.append(_mismatch_issue("PROJNUMB", expected, _find_in_corpus(corpus, expected) or "не найдено"))

    text_checks = (
        ("APPLICANT", "{{APPLICANT}}"),
        ("ADRESS", "{{ADRESS}}"),
        ("KADNUMBER", "{{KADNUMBER}}"),
        ("DATE", "{{DATE}}"),
        ("OTKUDASTROIT", "{{OTKUDASTROIT}}"),
        ("TP_NAME", "{{TP_NAME}}"),
        ("BRANCH_ARMATURE_LINE", "{{BRANCH_ARMATURE_LINE}}"),
    )
    for field, placeholder in text_checks:
        expected = str(replacement_map.get(placeholder, "") or "").strip()
        if not expected:
            continue
        if field == "ADRESS":
            ok = _address_matches(corpus, expected)
        elif field == "BRANCH_ARMATURE_LINE":
            ok = _branch_line_matches(corpus, expected)
        else:
            ok = _value_matches(corpus, expected)
        if not ok:
            issues.append(_mismatch_issue(field, expected, "не найдено в записке"))

    issues.extend(_validate_phase(corpus, replacement_map))
    issues.extend(_validate_cable_section(corpus, replacement_map))
    issues.extend(_validate_komapparat(corpus, replacement_map, tu_data))
    issues.extend(_validate_structured_tables(document, replacement_map))
    return issues


def _validate_phase(corpus: str, replacement_map: dict[str, str]) -> list[Any]:
    from backend.core.validation import NOTE_FIELD_LOCATIONS, ValidationIssue

    expected = str(replacement_map.get("{{FAZE}}", "") or "").strip().lower()
    if not expected:
        return []
    if _value_matches(corpus, expected):
        return []
    wrong = None
    for candidate in PHASE_VALUES:
        norm = candidate.lower()
        if norm == expected:
            continue
        if norm in corpus and "счетчик" in corpus:
            wrong = candidate
            break
    if wrong:
        return [
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_VALUE_WRONG_FAZE",
                message=f"Указана фазность «{wrong}», должно быть «{expected}».",
                field="FAZE",
                location=NOTE_FIELD_LOCATIONS["FAZE"],
            )
        ]
    return [
        ValidationIssue(
            category="note",
            severity="error",
            code="NOTE_VALUE_MISSING_FAZE",
            message=f"Не найдена фазность «{expected}».",
            field="FAZE",
            location=NOTE_FIELD_LOCATIONS["FAZE"],
        )
    ]


def _validate_cable_section(corpus: str, replacement_map: dict[str, str]) -> list[Any]:
    from backend.core.validation import NOTE_FIELD_LOCATIONS, ValidationIssue

    expected = str(replacement_map.get("{{SECH_KABEL}}", "") or "").strip()
    if not expected:
        return []
    if _cable_matches(corpus, expected):
        return []
    return [
        ValidationIssue(
            category="note",
            severity="error",
            code="NOTE_VALUE_MISSING_SECH_KABEL",
            message=f"Не найдено сечение кабеля «{format_cable_section_display(expected)}».",
            field="SECH_KABEL",
            location=NOTE_FIELD_LOCATIONS["SECH_KABEL"],
        )
    ]


def _validate_komapparat(
    corpus: str,
    replacement_map: dict[str, str],
    tu_data: dict[str, Any],
) -> list[Any]:
    from backend.core.validation import NOTE_FIELD_LOCATIONS, ValidationIssue

    if not tu_data.get("requires_komapparat_template"):
        return []
    branch = str(replacement_map.get("{{BRANCH_ARMATURE_LINE}}", "") or "").strip()
    if branch and _branch_line_matches(corpus, branch):
        return []
    if "коммутационного аппарата" not in corpus:
        return [
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_KOMAPPARAT_MISSING",
                message="В ТУ нужен коммутационный аппарат, но в записке нет строки про него.",
                field="BRANCH_ARMATURE_LINE",
                location=NOTE_FIELD_LOCATIONS["BRANCH_ARMATURE_LINE"],
            )
        ]
    if branch:
        return [
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_KOMAPPARAT_TEXT",
                message=f"Строка ответвительной арматуры не совпадает. Ожидалось: «{branch}».",
                field="BRANCH_ARMATURE_LINE",
                location=NOTE_FIELD_LOCATIONS["BRANCH_ARMATURE_LINE"],
            )
        ]
    return []


def _validate_structured_tables(document: Any, replacement_map: dict[str, str]) -> list[Any]:
    from backend.core.validation import NOTE_FIELD_LOCATIONS, ValidationIssue

    issues: list[Any] = []
    found_route = _read_route_plan_sheet(document)
    expected_route = str(replacement_map.get("{{ROUTE_PLAN_SHEET}}", "") or "").strip()
    if expected_route and found_route and found_route != expected_route:
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_VALUE_WRONG_ROUTE_PLAN_SHEET",
                message=f"В содержании указан лист «{found_route}», должно быть «{expected_route}».",
                field="ROUTE_PLAN_SHEET",
                location=NOTE_FIELD_LOCATIONS["ROUTE_PLAN_SHEET"],
            )
        )
    elif expected_route and not found_route:
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_VALUE_MISSING_ROUTE_PLAN_SHEET",
                message=f"Не найден номер листа плана трассы «{expected_route}».",
                field="ROUTE_PLAN_SHEET",
                location=NOTE_FIELD_LOCATIONS["ROUTE_PLAN_SHEET"],
            )
        )

    found_total = _read_total_sheets_stamp(document)
    expected_total = str(replacement_map.get("{{TOTAL_SHEETS}}", "") or "").strip()
    if expected_total and found_total and found_total != expected_total:
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_VALUE_WRONG_TOTAL_SHEETS",
                message=f"В штампе указано листов «{found_total}», должно быть «{expected_total}».",
                field="TOTAL_SHEETS",
                location=NOTE_FIELD_LOCATIONS["TOTAL_SHEETS"],
            )
        )

    work_values = _read_work_table_quantities(document)
    for placeholder, field in (
        ("{{P23}}", "P23"),
        ("{{A23}}", "A23"),
        ("{{YA23}}", "YA23"),
        ("{{K21}}", "K21"),
        ("{{GROUND}}", "GROUND"),
    ):
        expected = str(replacement_map.get(placeholder, "") or "").strip()
        if not expected:
            continue
        found = work_values.get(placeholder, "")
        if found and found != expected:
            issues.append(
                ValidationIssue(
                    category="note",
                    severity="error",
                    code=f"NOTE_VALUE_WRONG_{field}",
                    message=f"В таблице объёмов для {field}: указано «{found}», должно быть «{expected}».",
                    field=field,
                    location=ARMATURE_FIELD_LABELS.get(field, field),
                )
            )

    armature_values = _read_armature_table_quantities(document)
    for field, labels in ARMATURE_ROW_LABELS.items():
        placeholder = f"{{{{{field}}}}}"
        expected = str(replacement_map.get(placeholder, "") or "").strip()
        if not expected:
            continue
        found = ""
        for label in labels:
            found = armature_values.get(label, "")
            if found:
                break
        if found and not _numbers_equal(found, expected):
            issues.append(
                ValidationIssue(
                    category="note",
                    severity="error",
                    code=f"NOTE_VALUE_WRONG_{field}",
                    message=f"В таблице «Линейная арматура» {field}: указано «{found}», должно быть «{expected}».",
                    field=field,
                    location=NOTE_FIELD_LOCATIONS.get(field, "таблица арматуры"),
                )
            )

    supports_note = _read_supports_install_note(document)
    expected_note = str(replacement_map.get("{{SUPPORTS_INSTALL_NOTE}}", "") or "").strip()
    if expected_note and supports_note and supports_note.lower() != expected_note.lower():
        issues.append(
            ValidationIssue(
                category="note",
                severity="error",
                code="NOTE_VALUE_WRONG_SUPPORTS_INSTALL_NOTE",
                message=f"В спецификации указано «{supports_note}», должно быть «{expected_note}».",
                field="SUPPORTS_INSTALL_NOTE",
                location=NOTE_FIELD_LOCATIONS["SUPPORTS_INSTALL_NOTE"],
            )
        )
    return issues


ARMATURE_FIELD_LABELS = {
    "P23": "таблица объёмов, опоры П23",
    "A23": "таблица объёмов, опоры А23",
    "YA23": "таблица объёмов, опоры УА23*",
    "K21": "таблица объёмов, опоры К21",
    "GROUND": "таблица объёмов, заземления",
}


def _read_route_plan_sheet(document: Any) -> str | None:
    for block in document.blocks:
        entities = [entity for entity in block if entity.dxftype() in {"TEXT", "MTEXT", "ATTRIB"}]
        for index, entity in enumerate(entities):
            text = _get_text(entity)
            if not text or ROUTE_PLAN_SHEET_LABEL not in text:
                continue
            for prev in reversed(entities[:index]):
                plain = _plain_mtext(_get_text(prev)).strip()
                if re.fullmatch(r"\d+(?:-\d+)?", plain):
                    return plain
    return None


def _read_total_sheets_stamp(document: Any) -> str | None:
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
            return best_entity.dxf.text.strip()
    return None


def _read_work_table_quantities(document: Any) -> dict[str, str]:
    found: dict[str, str] = {}
    for block in document.blocks:
        if not block.name.startswith("*T"):
            continue
        entities = [entity for entity in block if entity.dxftype() == "MTEXT"]
        for index, entity in enumerate(entities):
            marker = _plain_mtext(_get_text(entity)).strip()
            placeholder = _work_table_support_placeholder(marker)
            if not placeholder:
                continue
            for next_entity in entities[index + 1 :]:
                plain = _plain_mtext(_get_text(next_entity)).replace(",", ".").strip()
                if plain in {"шт", "м", "км", "м³", "км/кг", "шт/ м³"}:
                    continue
                if re.fullmatch(r"\d+(?:\.\d+)?", plain):
                    found[placeholder] = plain
                    break
    return found


def _read_armature_table_quantities(document: Any) -> dict[str, str]:
    found: dict[str, str] = {}
    unit_tokens = {"шт", "м", "км", "м³", "км/кг", "шт/ м³"}
    for block in document.blocks:
        if not block.name.startswith("*T"):
            continue
        entities = [entity for entity in block if entity.dxftype() == "MTEXT"]
        for index, entity in enumerate(entities):
            plain = _plain_mtext(_get_text(entity)).strip()
            for labels in ARMATURE_ROW_LABELS.values():
                if not any(label == plain or (label in plain and len(plain) <= len(label) + 2) for label in labels):
                    continue
                for next_entity in entities[index + 1 : index + 8]:
                    next_plain = _plain_mtext(_get_text(next_entity)).replace(",", ".").strip()
                    if next_plain in unit_tokens:
                        continue
                    if re.fullmatch(r"\d+(?:\.\d+)?", next_plain):
                        found[labels[0]] = next_plain
                        break
    return found


def _read_supports_install_note(document: Any) -> str | None:
    for block in document.blocks:
        if not block.name.startswith("*T"):
            continue
        for entity in block:
            if entity.dxftype() != "MTEXT":
                continue
            text = _plain_mtext(_get_text(entity))
            match = re.search(r"по\s+\d+\s+опорам", text, flags=re.IGNORECASE)
            if match:
                return match.group(0)
    return None


def _mismatch_issue(field: str, expected: Any, found: str) -> Any:
    from backend.core.validation import NOTE_FIELD_LOCATIONS, ValidationIssue

    label = NOTE_FIELD_LOCATIONS.get(field, field)
    return ValidationIssue(
        category="note",
        severity="error",
        code=f"NOTE_VALUE_WRONG_{field}",
        message=f"Ожидалось «{expected}», найдено: {found}.",
        field=field,
        location=label,
    )


def _normalize_corpus(text: str) -> str:
    result = text.lower().replace("\u00a0", " ")
    result = result.replace("×", "x").replace("х", "x").replace("*", "x")
    result = re.sub(r"\s+", " ", result)
    return result.strip()


def _value_matches(corpus: str, expected: Any) -> bool:
    for candidate in _value_candidates(expected):
        if candidate and candidate in corpus:
            return True
    return False


def _value_candidates(value: Any) -> list[str]:
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    normalized = [_normalize_corpus(text)]
    normalized.append(_normalize_corpus(text.replace("№", "No")))
    if isinstance(value, float):
        rounded = round(value, 3)
        if rounded.is_integer():
            normalized.append(str(int(rounded)))
    compact = re.sub(r"\s+", "", _normalize_corpus(text))
    if compact:
        normalized.append(compact)
    return list(dict.fromkeys(item for item in normalized if item))


def _cable_matches(corpus: str, expected: str) -> bool:
    display = format_cable_section_display(expected)
    patterns = [
        _normalize_corpus(display),
        _normalize_corpus(display.replace("+", "+")),
        _normalize_corpus(display.replace("х", "x")),
        r"3\s*x\s*70\s*\+\s*1\s*x\s*70",
        r"3\s*x\s*50\s*\+\s*1\s*x\s*50",
    ]
    for pattern in patterns:
        if re.search(pattern, corpus):
            return True
    return _value_matches(corpus, display)


def _address_matches(corpus: str, expected: str) -> bool:
    if _value_matches(corpus, expected):
        return True
    for part in re.split(r"[,;]", expected):
        cleaned = part.strip().strip("«»")
        if len(cleaned) >= 8 and _value_matches(corpus, cleaned):
            return True
    return False


def _branch_line_matches(corpus: str, expected: str) -> bool:
    if _value_matches(corpus, expected):
        return True
    compact_expected = re.sub(r"\s+", "", _normalize_corpus(expected))
    compact_corpus = re.sub(r"\s+", "", corpus)
    return compact_expected in compact_corpus


def _find_in_corpus(corpus: str, expected: Any) -> str | None:
    for candidate in _value_candidates(expected):
        if candidate in corpus:
            return candidate
    return None


def _numbers_equal(left: str, right: str) -> bool:
    try:
        return abs(float(left.replace(",", ".")) - float(right.replace(",", "."))) < 0.01
    except ValueError:
        return left.strip() == right.strip()
