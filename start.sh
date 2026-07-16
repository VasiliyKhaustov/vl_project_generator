#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
echo "Запуск PRO (0,4 кВ + 10 кВ): http://127.0.0.1:8003"
exec python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8003
