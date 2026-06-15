from __future__ import annotations

import re


def normalize_tu_text(text: str) -> str:
    normalized = text.lower().replace("ё", "е")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()
