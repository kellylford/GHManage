@echo off
REM ── GHManage build script ─────────────────────────────────────────────
REM Run from the repo root. Creates dist\ghmanage.exe (standalone .exe).
REM
REM Usage:
REM   build.bat            — build the .exe
REM   build.bat clean      — clean build artifacts first, then build
REM ─────────────────────────────────────────────────────────────────────

setlocal

REM Check Python is available
where python >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found on PATH. Install Python 3.9+ and retry.
    exit /b 1
)

REM Optional clean
if /i "%1"=="clean" (
    echo Cleaning build artifacts...
    if exist dist rmdir /s /q dist
    if exist build rmdir /s /q build
    if exist ghmanage.spec del /q ghmanage.spec
    echo Done.
)

REM Create venv if it doesn't exist
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment.
        exit /b 1
    )
)

REM Activate venv (verify the activate script exists first)
if not exist .venv\Scripts\activate.bat (
    echo Error: .venv\Scripts\activate.bat not found. The venv is broken.
    exit /b 1
)
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment.
    exit /b 1
)

REM Confirm activation took effect (VIRTUAL_ENV should be set)
if not defined VIRTUAL_ENV (
    echo Error: Virtual environment activation did not take effect.
    exit /b 1
)
echo Using venv: %VIRTUAL_ENV%

REM Install dependencies (use venv's python explicitly to be safe)
echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install project dependencies.
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 (
    echo Error: Failed to install PyInstaller.
    exit /b 1
)

REM Build the .exe (use venv's pyinstaller explicitly)
echo Building ghmanage.exe...
".venv\Scripts\python.exe" -m PyInstaller --noconsole --onefile --name ghmanage ghviewer.py
if errorlevel 1 (
    echo Error: PyInstaller build failed.
    exit /b 1
)

REM Done
echo.
echo Build complete: dist\ghmanage.exe
endlocal