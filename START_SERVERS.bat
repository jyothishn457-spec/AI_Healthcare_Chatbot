@echo off
REM ============================================================
REM  AI Healthcare Assistant - Start Backend + Frontend
REM  Double-click this file to launch both local servers.
REM  Open http://localhost:5173  (login: admin / admin123)
REM ============================================================
title MediCare AI - Local Servers
cd /d "%~dp0"

echo Starting backend on http://localhost:8000 ...
start "MediCare Backend" cmd /k "cd backend && .venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo Starting frontend on http://localhost:5173 ...
start "MediCare Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are launching...
echo   Frontend: http://localhost:5173  (login: admin / admin123)
echo   Backend : http://localhost:8000
echo.
pause
