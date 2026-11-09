@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY=%LOCALAPPDATA%\PRO-VL\venv\Scripts\python.exe"
echo PRO: http://127.0.0.1:8003
echo Закройте это окно, чтобы остановить программу.
"%PY%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8003
echo.
echo Сервер остановился.
pause
