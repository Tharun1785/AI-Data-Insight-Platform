@echo off
setlocal

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_CMD=py"
    ) else (
        echo Python is not installed or not available on PATH.
        echo Install Python 3.11+ and rerun this script.
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv || exit /b 1
)

call .venv\Scripts\activate.bat || exit /b 1
python -m pip install -r requirements.txt || exit /b 1
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
