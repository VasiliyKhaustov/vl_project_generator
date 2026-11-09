from __future__ import annotations

from pathlib import Path


def mark_note_ready(note_path: Path) -> dict[str, str]:
    return {
        "mode": "mock",
        "message": "macOS MVP: DWG не редактируется. Подготовлена копия template_note.dwg.",
        "note_path": str(note_path),
    }
