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
echo [1/5] Checking Node.js environment...
node --version >nul 2>&1
if !errorlevel! neq 0 (
    echo X Error: Node.js not detected
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo + Node.js version: !NODE_VERSION!

REM Check npm
echo.
echo [2/5] Checking npm...
echo + npm: Available ^(will be verified during installation^)

REM Check and install dependencies
echo.
echo [3/5] Checking dependencies...

if not exist "node_modules" (
    echo ^ node_modules folder not found
    goto install_deps
)

if exist "node_modules\@playwright\test" (
    if exist "node_modules\axios" (
        echo + Dependencies already exist
        goto check_playwright
    )
)

echo ^ Some dependencies missing

:install_deps
echo.
echo ^ Installing dependencies...
echo This may take several minutes, please wait...
echo.

REM Clean if exists
if exist "node_modules" rmdir /s /q "node_modules" 2>nul
if exist "package-lock.json" del "package-lock.json" 2>nul

echo ^ Running npm install...
echo.

npm install --no-audit --no-fund

if !errorlevel! neq 0 (
    echo.
    echo X npm install failed
    echo Solutions: 1) Run as administrator 2) Check network 3) npm cache clean --force
    pause
    exit /b 1
)

echo.
echo + npm install completed successfully!

:check_playwright
echo.
echo [4/5] Installing Playwright browsers...
echo ^ Installing Chromium browser...
echo.

npx playwright install chromium

if !errorlevel! neq 0 (
    echo ^ Warning: Playwright browser installation had issues
    echo You can install manually later: npx playwright install chromium
    echo Continuing with server startup...
) else (
    echo + Playwright browsers installed successfully
)

:check_config
echo.
echo [5/5] Configuration setup...

if not exist ".env" (
    echo ^ Creating configuration file...
    
    if exist ".env.example" (
        copy ".env.example" ".env" >nul 2>&1
        echo + Configuration created from template
    ) else (
        echo OPENAI_API_KEY=your-api-key-here > .env
        echo OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 >> .env
        echo MIDSCENE_MODEL_NAME=qwen-vl-max-latest >> .env
        echo PORT=3001 >> .env
        echo + Basic configuration created
    )
    
    echo.
    echo IMPORTANT: Please edit .env file and set your API key
    echo Opening notepad for editing...
    start notepad .env 2>nul
    echo.
    echo After editing, run this script again.
    pause
    exit /b 0
)

echo + Configuration file exists

REM Check if API key is set
findstr /c:"your-api-key-here" .env >nul
if !errorlevel! equ 0 (
    echo.
    echo X Please edit .env file and set your actual API key
    start notepad .env 2>nul
    pause
    exit /b 0
)

echo + API key appears to be configured

REM Start server
echo.
echo ========================================
echo   STARTING SERVER
echo ========================================
echo.
echo + Starting Intent Test Framework Local Proxy Server...
echo.
echo Success indicators:
echo - "Server listening" = Server started successfully
echo - "WebSocket server ready" = Ready for connections
echo.
echo After successful startup, go to Web interface and select "Local Proxy Mode"
echo Press Ctrl+C to stop the server
echo.

node midscene_server.js

echo.
echo ========================================
echo Server stopped ^(exit code: !errorlevel!^)

if !errorlevel! neq 0 (
    echo.
    echo Common issues:
    echo 1. Check API key in .env file
    echo 2. Port 3001 may be in use
    echo 3. Check network connection
    echo 4. Try running as administrator
)

echo.
pause