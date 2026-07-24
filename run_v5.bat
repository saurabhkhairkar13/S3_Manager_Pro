@echo off
title S3 Manager Pro v5.0
echo.
echo   ====================================
echo    S3 Manager Pro v5.0 - Starting...
echo   ====================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install dependencies if needed
python -c "import boto3" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing boto3...
    pip install boto3
)

python -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing customtkinter...
    pip install customtkinter
)

python -c "import keyring" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing keyring...
    pip install keyring
)

:: Run the app
cd /d "%~dp0"
python -m s3_manager_pro_v5

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Application crashed. Check s3_manager_pro.log for details.
    pause
)
