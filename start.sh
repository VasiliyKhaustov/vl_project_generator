#!/bin/bash
# Тонкая обёртка: сам сервер живёт вне iCloud.
APP="${HOME}/Library/Application Support/PRO-VL/app"
if [ ! -x "$APP/start.sh" ]; then
  echo "Нет локальной копии: $APP"
  echo "Локальный запуск не установлен. Запустите установку ещё раз."
  exit 1
fi
exec /bin/bash "$APP/start.sh"
