@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "VENV=%LOCALAPPDATA%\PRO-VL\venv"
set "PY=%VENV%\Scripts\python.exe"
if not exist "%PY%" (
  echo Создаю окружение Python...
  where py >nul 2>&1 && py -3.12 -m venv "%VENV%"
  if not exist "%PY%" where py >nul 2>&1 && py -3 -m venv "%VENV%"
  if not exist "%PY%" where python >nul 2>&1 && python -m venv "%VENV%"
  if not exist "%PY%" (
    echo Не найден Python 3.11 или новее.
    echo Установите Python с https://www.python.org/downloads/
    echo и отметьте пункт Add python.exe to PATH.
    pause
    exit /b 1
  )
  "%PY%" -m pip install -U pip
  "%PY%" -m pip install -r "%~dp0requirements.txt"
  "%PY%" -m pip install pywin32
)
powershell -NoProfile -Command "try { if ((Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8003/health -TimeoutSec 2).StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
if not errorlevel 1 (
  start "" "http://127.0.0.1:8003"
  exit /b 0
)
echo Запускаю PRO. Окно сервера не закрывайте.
start "PRO" "%~dp0run_server.bat"
powershell -NoProfile -Command "$ok=$false; for($i=0;$i -lt 90;$i++){ try { $r=Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8003/health -TimeoutSec 2; if($r.StatusCode -eq 200){ $ok=$true; break } } catch {}; Start-Sleep -Milliseconds 500 }; if(-not $ok){ exit 1 }; Start-Process 'http://127.0.0.1:8003'"
if errorlevel 1 (
  echo Страница не открылась. Посмотрите текст в окне PRO.
  pause
  exit /b 1
)
