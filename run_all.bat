@echo off
REM Smart Portfolio Advisor - Run All Services
REM This script starts the Analytics Engine and Frontend

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo Starting Smart Portfolio Advisor...
echo.

REM Start Analytics Engine (Python FastAPI)
echo [1/2] Starting Analytics Engine on port 8000...
start "Analytics Engine" cmd /c call "%~dp0run_analytics.bat"
timeout /t 3 /nobreak

REM Start Frontend (React/Vite)
echo [2/2] Starting Frontend on port 5173...
start "Frontend" cmd /c call "%~dp0run_frontend.bat"

echo.
echo All services are starting...
echo Frontend:  http://localhost:5173
echo Analytics: http://localhost:8000
echo Backend:   Supabase (cloud-hosted)
echo.
pause
