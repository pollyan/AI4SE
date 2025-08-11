@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   Testing Node.js Detection
echo ========================================

REM Check Node.js
echo [1/3] Checking Node.js environment...
node --version >nul 2>&1
if !errorlevel! neq 0 (
    echo X Error: Node.js not detected
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
    echo + Node.js version: !NODE_VERSION!
)

REM Check npm
echo [2/3] Checking npm...
npm --version >nul 2>&1
if !errorlevel! neq 0 (
    echo X Error: npm not found
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('npm --version') do set NPM_VERSION=%%i
    echo + npm version: !NPM_VERSION!
)

echo [3/3] Environment check completed successfully!
echo.
echo Script executed without stopping - fix confirmed!
echo.