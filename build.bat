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

REM Activate venv
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
if errorlevel 1 (
    echo Error: Failed to install dependencies.
    exit /b 1
)

REM Build the .exe
echo Building ghmanage.exe...
pyinstaller --noconsole --onefile --name ghmanage ghviewer.py
if errorlevel 1 (
    echo Error: PyInstaller build failed.
    exit /b 1
)

REM Done
echo.
echo Build complete: dist\ghmanage.exe
endlocal