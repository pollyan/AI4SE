@echo off
chcp 65001 >nul
title Intent Test Framework - Local Proxy Server
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Intent Test Framework Local Proxy
echo ========================================
echo   Minimal startup version
echo ========================================
echo.

REM Basic environment check
echo [1/3] Environment check...
node --version >nul 2>&1
if !errorlevel! neq 0 (
    echo X Node.js not found - please install from https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VER=%%i
echo + Node.js: !NODE_VER!

REM Configuration check
echo.
echo [2/3] Configuration check...
if not exist ".env" (
    echo + Creating basic configuration...
    echo OPENAI_API_KEY=your-api-key-here > .env
    echo OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 >> .env
    echo MIDSCENE_MODEL_NAME=qwen-vl-max-latest >> .env
    echo PORT=3001 >> .env
    echo.
    echo ! IMPORTANT: Edit .env file and add your API key
    echo   Current file contains placeholder: your-api-key-here
    echo.
    start notepad .env 2>nul
    echo After editing, run this script again.
    pause
    exit /b 0
)

findstr /c:"your-api-key-here" .env >nul 2>&1
if !errorlevel! equ 0 (
    echo X Please edit .env and replace placeholder API key
    echo.
    start notepad .env 2>nul
    pause
    exit /b 0
)

echo + Configuration ready

REM Dependency check (inform only, don't install)
echo.
echo [3/3] Dependency status...
if not exist "node_modules" (
    echo ! Dependencies not installed
    echo   To install: npm install
    echo   Note: Installation may take 5-15 minutes
    echo.
    echo Would you like to try starting anyway? ^(y/n^)
    set /p user_choice="Choice: "
    if /i "!user_choice!"=="n" (
        echo.
        echo Please run: npm install
        echo Then restart this script
        pause
        exit /b 0
    )
) else (
    echo + Dependencies folder exists
)

REM Start server
echo.
echo ========================================
echo   STARTING SERVER
echo ========================================
echo.
echo + Attempting to start server...
echo   If this fails, you may need to run: npm install
echo.

node midscene_server.js

echo.
echo Server stopped ^(exit code: !errorlevel!^)
pause