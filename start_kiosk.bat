@echo off
rem ---- Mission Control launcher (fullscreen kiosk via Edge) ----
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py
%PY% --version >nul 2>nul || (
  echo Python was not found. Install it from https://python.org
  echo ^(check "Add python.exe to PATH" during install^), then run this again.
  pause
  exit /b 1
)
%PY% -c "import psutil" 2>nul || (
  echo Installing psutil ^(one-time^)...
  %PY% -m pip install psutil
)
start "Mission Control Server" /min %PY% server.py
timeout /t 2 /nobreak >nul
start "" msedge --kiosk "http://localhost:8350" --edge-kiosk-type=fullscreen --no-first-run
if errorlevel 1 start "" "http://localhost:8350"
