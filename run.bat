@echo off
title Network Path and Delay Analyzer
echo ========================================================
echo   Starting Network Path and Delay Analyzer (FastAPI)
echo ========================================================
echo.

set "PYTHON_CMD="

:: 1. Check known real installation directories first
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :found
)
if exist "C:\Python313\python.exe" (
    set "PYTHON_CMD=C:\Python313\python.exe"
    goto :found
)
if exist "C:\Program Files\Python313\python.exe" (
    set "PYTHON_CMD=C:\Program Files\Python313\python.exe"
    goto :found
)

:: 2. Check py launcher
py -3.13 --version >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3.13"
    goto :found
)
py -3 --version >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3"
    goto :found
)

:: 3. Test if global 'python' actually works (not the MS Store stub)
python -c "import sys; sys.exit(0)" >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    goto :found
)

echo [ERROR] No working Python installation was found.
echo Please install Python from https://www.python.org/downloads/
pause
exit /b 1

:found
echo Using Python: %PYTHON_CMD%
echo.
echo ========================================================
echo   Web Server starting at: http://localhost:8000
echo   Open your browser and navigate to http://localhost:8000
echo   Press Ctrl+C to stop the server.
echo ========================================================
echo.

"%PYTHON_CMD%" -m app.main
if %errorlevel% neq 0 (
    echo.
    echo Server exited with error code %errorlevel%.
)
pause
