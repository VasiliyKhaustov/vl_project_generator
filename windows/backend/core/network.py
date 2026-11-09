from __future__ import annotations

import socket
import threading
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def internet_reachable(timeout_s: float = 0.4) -> bool:
    """Быстрая проверка сети. Поток daemon: офлайн не блокирует обработку."""
    result = {"ok": False}

    def probe() -> None:
        for host, port in (("1.1.1.1", 443), ("8.8.8.8", 53)):
            try:
                with socket.create_connection((host, port), timeout=timeout_s):
                    result["ok"] = True
                    return
            except OSError:
                continue

    thread = threading.Thread(target=probe, daemon=True)
    thread.start()
    thread.join(timeout_s + 0.3)
    return bool(result["ok"])


def run_with_timeout(func: Callable[[], T], timeout_s: float) -> T:
    """Запускает функцию с дедлайном. По истечении не ждёт зависший сокет."""
    box: dict[str, object] = {}

    def worker() -> None:
        try:
            box["result"] = func()
        except Exception as exc:  # noqa: BLE001 — пробрасываем исходную ошибку вызывающему
            box["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout_s)
    if thread.is_alive():
        raise TimeoutError(f"операция не завершилась за {timeout_s:.0f} с")
    if "error" in box:
        raise box["error"]  # type: ignore[misc]
    return box["result"]  # type: ignore[return-value]
