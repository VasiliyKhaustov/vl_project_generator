#!/bin/bash
# Запуск PRO на Linux. Открывает браузер, когда сервер уже отвечает.
set -euo pipefail
cd "$(dirname "$0")"
VENV="${XDG_DATA_HOME:-$HOME/.local/share}/PRO-VL/venv"
PY="$VENV/bin/python"
open_page() {
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://127.0.0.1:8003" >/dev/null 2>&1 || true
  fi
}
if [ ! -x "$PY" ]; then
  echo "Создаю окружение Python..."
  if command -v python3.12 >/dev/null 2>&1; then
    python3.12 -m venv "$VENV"
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m venv "$VENV"
  else
    echo "Не найден Python 3.11+. Установите пакеты python3 и python3-venv."
    exit 1
  fi
  "$PY" -m pip install -U pip
  "$PY" -m pip install -r requirements.txt
fi
if "$PY" -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8003/health", timeout=2)' >/dev/null 2>&1; then
  open_page
  echo "PRO уже запущена: http://127.0.0.1:8003"
  exit 0
fi
"$PY" -m uvicorn backend.main:app --host 127.0.0.1 --port 8003 &
PID=$!
trap 'kill "$PID" >/dev/null 2>&1 || true' INT TERM
if ! "$PY" -c 'import time, urllib.request, sys
for _ in range(90):
    try:
        urllib.request.urlopen("http://127.0.0.1:8003/health", timeout=1)
        sys.exit(0)
    except Exception:
        time.sleep(0.5)
sys.exit(1)'; then
  echo "Сервер не открылся."
  kill "$PID" >/dev/null 2>&1 || true
  exit 1
fi
open_page
echo "PRO: http://127.0.0.1:8003"
echo "Остановка: Ctrl+C"
wait "$PID"
