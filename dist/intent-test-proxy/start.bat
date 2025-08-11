@echo off
chcp 65001 >nul
title Intent Test Framework - Local Proxy Server
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Intent Test Framework Local Proxy
echo ========================================
echo.

REM Check Node.js
echo [1/4] Checking Node.js environment...
node --version >nul 2>&1
if !errorlevel! neq 0 (
    echo X Error: Node.js not detected
    echo.
    echo Please install Node.js first:
    echo https://nodejs.org/
    echo.
    echo Recommend LTS version ^(16.x or higher^)
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo + Node.js version: !NODE_VERSION!

REM Check npm
npm --version >nul 2>&1
if !errorlevel! neq 0 (
    echo X Error: npm not found
    pause
    exit /b 1
)

REM Check and install dependencies
echo.
echo [2/4] Checking dependencies...

REM Check key dependencies
set PLAYWRIGHT_TEST_MISSING=false
set AXIOS_MISSING=false

if not exist "node_modules\@playwright\test" (
    set PLAYWRIGHT_TEST_MISSING=true
)

if not exist "node_modules\axios" (
    set AXIOS_MISSING=true
)

REM Install dependencies if missing or node_modules doesn't exist
if not exist "node_modules" (
    goto install_deps
)
if "!PLAYWRIGHT_TEST_MISSING!"=="true" (
    goto install_deps
)
if "!AXIOS_MISSING!"=="true" (
    goto install_deps
)

echo + Dependencies already exist
goto check_config

:install_deps
echo ^ Installing/updating dependencies...
echo This may take several minutes, please wait...

REM Clean old dependencies
if exist "node_modules" (
    echo ^ Cleaning old dependencies...
    rmdir /s /q "node_modules"
    if exist "package-lock.json" (
        del "package-lock.json"
    )
)

REM Install dependencies
npm install
if !errorlevel! neq 0 (
    echo X Dependencies installation failed
    echo.
    echo Possible solutions:
    echo 1. Check network connection
    echo 2. Clean npm cache: npm cache clean --force
    echo 3. Use China mirror: npm config set registry https://registry.npmmirror.com
    pause
    exit /b 1
)

REM Verify key dependencies
if not exist "node_modules\@playwright\test" (
    echo X @playwright/test dependency installation failed
    pause
    exit /b 1
)

if not exist "node_modules\axios" (
    echo X axios dependency installation failed
    pause
    exit /b 1
)

echo + Dependencies installation completed

:check_config

REM Check configuration file
echo.
echo [3/4] Checking configuration file...
if not exist ".env" (
    echo ^ First run, creating configuration file...
    copy ".env.example" ".env" >nul
    echo.
    echo ! Important: Please configure AI API key
    echo.
    echo Configuration file created: .env
    echo Please edit this file and add your AI API key
    echo.
    echo After configuration, please run this script again
    echo.
    start notepad ".env"
    pause
    exit /b 0
)

echo + Configuration file exists

REM Start server
echo.
echo [4/4] Starting server...
echo.
echo ^ Starting Intent Test Framework Local Proxy Server...
echo.
echo After successful startup, please return to the Web interface
echo and select "Local Proxy Mode"
echo Press Ctrl+C to stop the server
echo.

node midscene_server.js

echo.
echo Server stopped
pause