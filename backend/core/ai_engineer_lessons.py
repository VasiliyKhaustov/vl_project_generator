"""Уроки AI Engineer: файл вопросов и ответов и поиск ближайшего примера.

Обучение — это не страница сайта. Инженер пишет пары в examples/ai_engineer/уроки.md,
затем train_lessons() строит поисковую модель по словам и тройкам букв.
Чат подмешивает ближайшие уроки в ответ и не меняет проект.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from backend.core.app_paths import app_data_dir

_PLACEHOLDER = re.compile(r"\(напишите|\(следующ|\(ответ\)", re.IGNORECASE)
_TOKEN = re.compile(r"[a-zа-я0-9*]{2,}", re.IGNORECASE)


def lessons_path(root: Path | None = None) -> Path:
    if root is not None:
        return Path(root) / "examples" / "ai_engineer" / "уроки.md"
    return Path(__file__).resolve().parents[2] / "examples" / "ai_engineer" / "уроки.md"


def model_path() -> Path:
    return app_data_dir() / "ai_engineer" / "model.json"


def parse_lessons(text: str) -> list[dict[str, str]]:
    """Достаёт пары «вопрос / ответ». Пустые заготовки пропускает.

    Число пар не ограничено. Строка --- не обязательна: новая пара начинается
    со слова «Вопрос». Заголовок «Ответ» можно писать и без решёток.
    """
    lessons: list[dict[str, str]] = []
    normalized = str(text or "").replace("\r\n", "\n")
    for question, answer in _iter_pairs(normalized):
        if not question or not answer:
            continue
        if _PLACEHOLDER.search(question) or _PLACEHOLDER.search(answer):
            continue
        if len(question) < 4 or len(answer) < 8:
            continue
        lessons.append({"question": question, "answer": answer})
    return lessons


def load_lessons(path: Path | None = None) -> list[dict[str, str]]:
    file_path = path or lessons_path()
    if not file_path.exists():
        return []
    try:
        return parse_lessons(file_path.read_text(encoding="utf-8"))
    except OSError:
        return []


def train_lessons(path: Path | None = None, *, destination: Path | None = None) -> dict[str, Any]:
    """Строит модель ближайших вопросов и сохраняет её рядом с данными программы."""
    lessons = load_lessons(path)
    if not lessons:
        raise ValueError("В уроках нет готовых пар. Заполните вопрос и ответ и уберите текст в скобках.")
    documents = [_tokens(item["question"]) for item in lessons]
    idf = _idf(documents)
    vectors = [_unit(_tfidf(tokens, idf)) for tokens in documents]
    payload = {
        "version": 1,
        "count": len(lessons),
        "idf": idf,
        "lessons": [
            {"question": item["question"], "answer": item["answer"], "vector": vector}
            for item, vector in zip(lessons, vectors)
        ],
    }
    target = destination or model_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {"ok": True, "count": len(lessons), "path": str(target)}


def similar_lessons(question: str, *, limit: int = 3, model: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Ближайшие уроки к вопросу. Пустой список, если модель ещё не обучена."""
    payload = model if model is not None else _cached_model()
    if not payload:
        return []
    idf = payload.get("idf") or {}
    query = _unit(_tfidf(_tokens(question), idf))
    if not query:
        return []
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in payload.get("lessons") or []:
        if not isinstance(item, dict):
            continue
        score = _dot(query, item.get("vector") or {})
        if score <= 0:
            continue
        ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    result: list[dict[str, Any]] = []
    for score, item in ranked[:limit]:
        result.append(
            {
                "score": round(score, 4),
                "question": str(item.get("question") or ""),
                "answer": str(item.get("answer") or ""),
            }
        )
    return result


def lesson_prompt(question: str, *, limit: int = 3, model: dict[str, Any] | None = None) -> str:
    """Примеры инженера для любого вопроса, не только для тех, что он записал."""
    payload = model if model is not None else _cached_model()
    stored = [item for item in (payload or {}).get("lessons") or [] if isinstance(item, dict)]
    if not stored:
        return ""
    hits = similar_lessons(question, limit=limit, model=payload)
    lines = [
        "Примеры ниже показывают, как инженер объясняет проект. Это не список вопросов, на которые можно отвечать.",
        "Отвечай на любой вопрос по этому проекту: опоры, которых нет, арматуру, которой нет, климат, 0,4 кВ и 10 кВ.",
        "Из примера бери способ рассуждать и тон. Числа, опоры и позиции ведомости бери только из фактов этого проекта.",
        "Если в примере другие штуки, не переноси их сюда. Не говори, что такого вопроса не было.",
        "",
        "Ближе всего к текущему вопросу:",
    ]
    if hits:
        for index, item in enumerate(hits, start=1):
            lines.append(f"Пример {index}. Вопрос: {item['question']}")
            lines.append(f"Как он объяснял: {item['answer']}")
    else:
        lines.append("Прямого примера нет. Ответь по фактам проекта тем же способом.")
    lines.append("")
    lines.append("Все примеры инженера:")
    for item in stored:
        lines.append(f"Вопрос: {item.get('question') or ''}")
        lines.append(f"Как он объяснял: {item.get('answer') or ''}")
    return "\n".join(lines)


def taught_reply(question: str, *, local_reply: str) -> str:
    """Готовый текст урока не подменяет ответ: числа в нём от другого проекта."""
    del question, local_reply
    return ""


_MODEL_CACHE: dict[str, Any] = {"stamp": None, "payload": None}


def _cached_model() -> dict[str, Any] | None:
    path = model_path()
    if not path.exists():
        fallback = lessons_path().with_name("model.json")
        path = fallback if fallback.exists() else path
    if not path.exists():
        return None
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return None
    if _MODEL_CACHE["stamp"] == stamp and isinstance(_MODEL_CACHE["payload"], dict):
        return _MODEL_CACHE["payload"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    _MODEL_CACHE["stamp"] = stamp
    _MODEL_CACHE["payload"] = payload
    return payload


def _iter_pairs(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"(?:^|\n)(?:##\s*)?Вопрос[^\n]*\n(.*?)(?:^|\n)(?:##\s*)?Ответ[^\n]*\n(.*?)(?=(?:\n(?:##\s*)?Вопрос[^\n]*\n)|\Z)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    return [(_clean(match.group(1)), _clean(match.group(2))) for match in pattern.finditer(text)]


def _clean(text: str) -> str:
    cleaned = re.sub(r"\n{3,}", "\n\n", str(text or "").strip())
    return re.sub(r"\s*---\s*$", "", cleaned).strip()


def _tokens(text: str) -> list[str]:
    lowered = str(text or "").lower().replace("ё", "е")
    words = _TOKEN.findall(lowered)
    grams: list[str] = []
    for word in words:
        padded = f" {word} "
        grams.extend(padded[index : index + 3] for index in range(len(padded) - 2))
    return words + grams


def _idf(documents: list[list[str]]) -> dict[str, float]:
    counts: Counter[str] = Counter()
    for tokens in documents:
        counts.update(set(tokens))
    total = len(documents)
    return {token: math.log((1 + total) / (1 + seen)) + 1.0 for token, seen in counts.items()}


def _tfidf(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(tokens)
    return {
        token: (1.0 + math.log(count)) * idf.get(token, 0.0)
        for token, count in counts.items()
        if idf.get(token, 0.0)
    }


def _unit(vector: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm <= 0:
        return {}
    return {token: value / norm for token, value in vector.items()}


def _dot(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(token, 0.0) for token, value in left.items())


def _local_is_generic(reply: str) -> bool:
    text = str(reply or "").strip()
    return (
        not text
        or text.startswith("Напишите вопрос")
        or text.startswith("Не совсем понял")
        or text.startswith("План чертите вы")
        or text.startswith("Могу ответить по нормам")
    )
