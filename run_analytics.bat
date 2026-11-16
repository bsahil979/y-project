@echo off
REM Start Analytics Engine Only (FastAPI)
cd /d "%~dp0analytics-engine"
echo Starting Analytics Engine API on port 8000...
if not exist "venv\Scripts\python.exe" (
  echo Python environment missing. Run python -m venv venv in analytics-engine,
  echo then venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
"venv\Scripts\python.exe" -m uvicorn api:app --host 127.0.0.1 --port 8000
pause
