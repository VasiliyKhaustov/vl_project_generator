#!/bin/bash
# Тонкая обёртка: сам сервер живёт вне iCloud.
APP="${HOME}/Library/Application Support/PRO-VL/app"
if [ ! -x "$APP/start.sh" ]; then
  echo "Нет локальной копии: $APP"
  echo "Откройте Cursor и попросите снова установить запуск."
  exit 1
fi
exec /bin/bash "$APP/start.sh"
