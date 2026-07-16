#!/bin/bash
cd "$(dirname "$0")"
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
source .venv/bin/activate
echo "Запуск PRO (0,4 кВ + 10 кВ): http://127.0.0.1:8003"
echo "Остановить: Ctrl+C"
exec python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8003
