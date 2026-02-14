@echo off
setlocal enabledelayedexpansion
title FIWB AI - Local Development Launcher

echo ===================================
echo   FIWB AI: Starting Locally
echo ===================================

:: 1. Backend Setup & Run
echo.
echo [1/3] Starting Backend Server...
cd fiwb-backend
if not exist venv (
    echo    Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate
if not exist venv\Lib\site-packages\fastapi (
    echo    Installing dependencies...
    pip install -r requirements.txt
)
echo    Backend running on http://127.0.0.1:8001
start "FIWB Backend" cmd /k "venv\Scripts\activate && python -m uvicorn app.main:app --reload --port 8001"

:: 2. Configure Frontend for Localhost
echo.
echo [2/3] Configuring Frontend...
cd ..\fiwb-frontend
echo NEXT_PUBLIC_API_URL=http://127.0.0.1:8001 > .env.local
echo    Updated .env.local to point to localhost.

:: 3. Frontend Setup & Run
echo.
echo [3/3] Starting Frontend Server...
if not exist node_modules (
    echo    Installing dependencies...
    call npm install
)
echo    Frontend running on http://localhost:3000
start "FIWB Frontend" cmd /k "npm run dev"

echo.
echo ===================================
echo   SYSTEM RUNNING LOCALLY
echo ===================================
echo.
echo Backend:  http://127.0.0.1:8001
echo Frontend: http://localhost:3000
echo.
echo Note: Ensure 'http://localhost:3000' is added to your Google Cloud Console Authorized JavaScript origins.
echo.
pause
