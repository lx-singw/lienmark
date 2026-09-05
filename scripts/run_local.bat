@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo  ^>^> LIENMARK CLEARANCE CHANGE CONTROL - LOCAL SERVER
echo     Google AntiGravity: Agentic Cinema Hackathon
echo ======================================================================

REM Navigate to project root directory
cd /d "%~dp0.."

REM Verify python is installed
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in PATH. Please install Python 3.11+.
    pause
    exit /b 1
)

REM Create .env from .env.example if missing
if not exist .env (
    if exist .env.example (
        echo [INFO] .env not found. Initializing from .env.example...
        copy .env.example .env >nul
        echo [INFO] Created .env successfully.
    )
)

REM Set PYTHONPATH to repository root
set PYTHONPATH=%CD%

echo.
echo Server starting on:
echo   - Local UI ^& Health: http://127.0.0.1:8000/
echo   - Interactive API Docs: http://127.0.0.1:8000/docs
echo   - Health Check: http://127.0.0.1:8000/health
echo.
echo Press Ctrl+C to terminate the server.
echo ======================================================================
echo.

REM Launch uvicorn with hot reload on port 8000
where uvicorn >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    uvicorn backend.main:app --reload --port 8000
) else (
    echo [INFO] Direct 'uvicorn' binary not in PATH, launching via 'python -m uvicorn'...
    python -m uvicorn backend.main:app --reload --port 8000
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server terminated with error code %ERRORLEVEL%.
    pause
)
