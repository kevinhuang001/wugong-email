@echo off
REM Wugong Email Windows Wrapper Script
REM This script determines its own location and runs the CLI using the local venv

SET "INSTALL_DIR=%~dp0"
SET "INSTALL_DIR=%INSTALL_DIR:~0,-1%"

REM Configuration paths (consistent with install.ps1/upgrade.ps1)
SET "CONFIG_DIR=%USERPROFILE%\.config\wugong"
SET "CONFIG_FILE=%CONFIG_DIR%\config.toml"

REM Activate virtual environment
IF EXIST "%INSTALL_DIR%\.venv\Scripts\python.exe" (
    SET "PYTHON_EXE=%INSTALL_DIR%\.venv\Scripts\python.exe"
) ELSE (
    echo Error: Virtual environment not found at %INSTALL_DIR%\.venv
    exit /b 1
)

REM Set environment variables
SET "WUGONG_CONFIG=%CONFIG_FILE%"
SET "PYTHONPATH=%INSTALL_DIR%;%PYTHONPATH%"

REM Run the CLI
"%PYTHON_EXE%" "%INSTALL_DIR%\main.py" %*
