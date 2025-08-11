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
echo.
echo [2/5] Checking npm...

REM Try npm directly - simpler approach
npm --version >nul 2>&1
if !errorlevel! neq 0 (
    echo X Error: npm not available
    echo.
    echo npm is required but not found or not working properly.
    echo This usually means:
    echo   1. Node.js was installed without npm
    echo   2. npm was corrupted during installation
    echo   3. PATH environment variable needs refresh
    echo.
    echo Solutions:
    echo   1. Download and reinstall Node.js from https://nodejs.org/
    echo   2. Restart your command prompt after Node.js installation
    echo   3. If problem persists, try running as administrator
    echo.
    pause
    exit /b 1
)

REM Get npm version if available
for /f "tokens=*" %%i in ('npm --version 2^>nul') do set NPM_VERSION=%%i
if "!NPM_VERSION!"=="" (
    echo ^ npm is available but version detection failed
    echo + npm: OK (version unknown)
) else (
    echo + npm version: !NPM_VERSION!
)

REM Check and install dependencies
echo.
echo [3/5] Checking dependencies...

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
goto check_playwright

:install_deps
echo ^ Installing/updating dependencies...
echo This may take several minutes, please wait...

REM Clean old dependencies
if exist "node_modules" (
    echo ^ Cleaning old dependencies...
    rmdir /s /q "node_modules" 2>nul
    if exist "package-lock.json" (
        del "package-lock.json" 2>nul
    )
)

REM Install dependencies with verbose output for debugging
echo ^ Running: npm install
npm install --progress=true
if !errorlevel! neq 0 (
    echo X Dependencies installation failed
    echo.
    echo Possible solutions:
    echo 1. Check network connection
    echo 2. Clean npm cache: npm cache clean --force
    echo 3. Use China mirror: npm config set registry https://registry.npmmirror.com
    echo 4. Try running as administrator
    pause
    exit /b 1
)

REM Verify key dependencies
if not exist "node_modules\@playwright\test" (
    echo X @playwright/test dependency installation failed
    echo   Checking node_modules directory...
    dir node_modules 2>nul | findstr /i playwright
    pause
    exit /b 1
)

if not exist "node_modules\axios" (
    echo X axios dependency installation failed
    echo   Checking node_modules directory...
    dir node_modules 2>nul | findstr /i axios
    pause
    exit /b 1
)

echo + Dependencies installation completed

:check_playwright

REM Check Playwright browsers
echo.
echo [4/5] Checking Playwright browsers...
echo ^ Installing/updating Playwright browsers...
echo This step is necessary for web automation to work properly.

npx playwright install chromium --with-deps
if !errorlevel! neq 0 (
    echo ^ Warning: Playwright browser installation had issues
    echo   This might cause "Executable doesn't exist" errors during testing
    echo   You can manually install later with: npx playwright install chromium
    echo   Continuing with server startup...
) else (
    echo + Playwright browsers ready
)

:check_config

REM Check configuration file
echo.
echo [5/5] Checking configuration file...
if not exist ".env" (
    echo ^ First run, creating configuration file...
    copy ".env.example" ".env" >nul 2>&1
    if !errorlevel! neq 0 (
        echo X Failed to copy .env.example to .env
        echo   Please manually create .env file or check file permissions
        pause
        exit /b 1
    )
    echo.
    echo ! Important: Please configure AI API key
    echo.
    echo Configuration file created: .env
    echo Please edit this file and add your AI API key
    echo.
    echo After configuration, please run this script again
    echo.
    if exist "notepad.exe" (
        start notepad ".env"
    ) else (
        echo Please manually edit the .env file
    )
    pause
    exit /b 0
)

echo + Configuration file exists

REM Final check - verify all is ready
echo.
echo ========================================
echo   Starting Server
echo ========================================

echo ^ Starting Intent Test Framework Local Proxy Server...
echo.
echo After successful startup, you should see:
echo   - Server listening messages
echo   - WebSocket server ready
echo   - AI model configuration
echo.
echo Then return to the Web interface and select "Local Proxy Mode"
echo Press Ctrl+C to stop the server
echo.

REM Start the server with error handling
node midscene_server.js
set SERVER_EXIT_CODE=!errorlevel!

echo.
if !SERVER_EXIT_CODE! neq 0 (
    echo X Server exited with error code: !SERVER_EXIT_CODE!
    echo.
    echo Common issues:
    echo 1. Port 3001 is already in use
    echo 2. Missing AI API key in .env file
    echo 3. Node.js version compatibility
    echo 4. Missing dependencies
    echo.
    echo Please check the error messages above
) else (
    echo ^ Server stopped normally
)

pause