@echo off
REM Start Frontend Only
cd /d "%~dp0frontend"
echo Starting Frontend...
if not exist "node_modules" (
  echo Installing frontend dependencies...
  call npm install --legacy-peer-deps
  if errorlevel 1 exit /b 1
)
call npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
pause
