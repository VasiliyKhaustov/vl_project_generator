from __future__ import annotations

import re

CADASTRAL_NUMBER_RE = re.compile(r"\b(\d{2}:\d{2}:\d{5,10}:\d+)\b")


def extract_cadastral_numbers(tu_text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in CADASTRAL_NUMBER_RE.finditer(tu_text):
        number = re.sub(r"\s+", "", match.group(1))
        if number in seen:
            continue
        seen.add(number)
        found.append(number)
    return found
