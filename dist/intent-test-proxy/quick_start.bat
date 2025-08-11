@echo off
chcp 65001 >nul
title Intent Test Framework - Quick Start
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Intent Test Framework - Quick Start
echo ========================================
echo   Bypass dependency installation
echo ========================================
echo.

echo This script will attempt to start the server without checking dependencies.
echo Use this if npm install keeps failing or taking too long.
echo.

REM Basic checks only
echo [1/2] Basic environment check...
node --version >nul 2>&1
if !errorlevel! neq 0 (
    echo X Node.js not found
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VER=%%i
echo + Node.js !NODE_VER! detected

echo.
echo [2/2] Configuration check...
if not exist ".env" (
    echo + Creating configuration file...
    echo OPENAI_API_KEY=your-api-key-here > .env
    echo OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 >> .env
    echo MIDSCENE_MODEL_NAME=qwen-vl-max-latest >> .env
    echo PORT=3001 >> .env
    echo.
    echo REQUIRED: Please edit .env and set your API key
    echo Opening file for editing...
    start notepad .env
    echo.
    echo After editing, run this script again.
    pause
    exit /b 0
)

findstr /c:"your-api-key-here" .env >nul
if !errorlevel! equ 0 (
    echo.
    echo WARNING: Default API key detected
    echo Please edit .env file and set your actual API key
    echo.
    echo Opening .env for editing...
    start notepad .env
    echo.
    echo After editing, run this script again.
    pause
    exit /b 0
)

echo + Configuration appears ready

echo.
echo ========================================
echo   ATTEMPTING SERVER START
echo ========================================
echo.
echo Note: If dependencies are missing, you'll see error messages.
echo In that case, run: npm install
echo.
echo Starting server...
echo.

node midscene_server.js

echo.
echo Server exited with code: !errorlevel!
echo.
if !errorlevel! neq 0 (
    echo If you see "Cannot find module" errors:
    echo   1. Run: npm install
    echo   2. Or use the full start.bat script
    echo.
)
pause