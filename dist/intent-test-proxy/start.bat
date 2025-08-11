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
node --version >node_check.tmp 2>&1
if !errorlevel! neq 0 (
    echo X Error: Node.js not detected
    echo.
    echo Please install Node.js first:
    echo https://nodejs.org/
    echo.
    echo Recommend LTS version ^(16.x or higher^)
    if exist node_check.tmp del node_check.tmp
    pause
    exit /b 1
)

set NODE_VERSION=Unknown
if exist node_check.tmp (
    for /f "tokens=*" %%i in (node_check.tmp) do set NODE_VERSION=%%i
    del node_check.tmp
)
echo + Node.js version: !NODE_VERSION!

REM Check npm - skip version check if problematic
echo.
echo [2/5] Checking npm...
echo ^ Skipping npm version check to avoid script termination
echo + npm: Will be verified during dependency installation

REM Check and install dependencies
echo.
echo [3/5] Checking dependencies...

REM Check key dependencies
set NEED_INSTALL=false

if not exist "node_modules" (
    set NEED_INSTALL=true
    echo ^ node_modules folder not found
)
if not exist "node_modules\@playwright\test" (
    set NEED_INSTALL=true
    echo ^ @playwright/test missing
)
if not exist "node_modules\axios" (
    set NEED_INSTALL=true
    echo ^ axios missing
)

if "!NEED_INSTALL!"=="false" (
    echo + Dependencies already exist
    goto check_playwright
)

:install_deps
echo.
echo ^ Installing dependencies...
echo This may take several minutes, please wait...
echo.

REM Clean old dependencies if they exist
if exist "node_modules" (
    echo ^ Cleaning old dependencies...
    rmdir /s /q "node_modules" 2>nul
)
if exist "package-lock.json" (
    del "package-lock.json" 2>nul
)

REM Install dependencies with progress monitoring
echo ^ Starting npm install...
echo   This may take 5-15 minutes on first run...
echo   Progress: npm install is running in background
echo.

REM Create monitoring script for long-running npm install
echo @echo off > install_monitor.bat
echo setlocal enabledelayedexpansion >> install_monitor.bat
echo set counter=0 >> install_monitor.bat
echo :monitor_loop >> install_monitor.bat
echo timeout /t 30 /nobreak ^>nul >> install_monitor.bat
echo set /a counter+=30 >> install_monitor.bat
echo echo [!counter!s] npm install is still running... >> install_monitor.bat
echo if !counter! geq 900 ( >> install_monitor.bat
echo   echo [15min] This is taking longer than usual >> install_monitor.bat
echo   echo [15min] Check network connection or consider Ctrl+C and retry >> install_monitor.bat
echo ^) >> install_monitor.bat
echo tasklist /fi "imagename eq npm.exe" ^>nul 2^>^&1 >> install_monitor.bat
echo if !errorlevel! equ 0 goto monitor_loop >> install_monitor.bat
echo echo + npm install process completed >> install_monitor.bat
echo del install_monitor.bat >> install_monitor.bat

REM Run npm install with monitoring
start /b install_monitor.bat

REM Try the actual npm install
npm install --no-audit --no-fund

set INSTALL_RESULT=!errorlevel!

REM Stop monitoring
taskkill /f /im timeout.exe >nul 2>&1

if !INSTALL_RESULT! neq 0 (
    echo.
    echo X npm install failed ^(exit code: !INSTALL_RESULT!^)
    echo.
    echo Most common solutions:
    echo.
    echo 1. Network/Registry Issues:
    echo    npm config set registry https://registry.npmmirror.com
    echo    npm cache clean --force
    echo.
    echo 2. Permission Issues:
    echo    Close this window and "Run as administrator"
    echo.
    echo 3. Proxy/Firewall:
    echo    Check your corporate proxy settings
    echo    Temporarily disable antivirus/firewall
    echo.
    echo 4. Manual Installation:
    echo    Run these commands manually:
    echo    npm install --verbose
    echo    npm install @playwright/test axios
    echo.
    pause
    exit /b 1
)

REM Verify key dependencies
if not exist "node_modules\@playwright\test" (
    echo X @playwright/test dependency missing after installation
    echo.
    if exist npm_install.log (
        echo Installation log:
        type npm_install.log
        del npm_install.log
    )
    pause
    exit /b 1
)

if not exist "node_modules\axios" (
    echo X axios dependency missing after installation
    pause
    exit /b 1
)

if exist npm_install.log del npm_install.log
echo + Dependencies installation completed

:check_playwright
echo.
echo [4/5] Checking Playwright browsers...
echo ^ Installing Playwright browsers (required for automation)...

REM Try to install Playwright browsers with error handling
npx playwright install chromium >playwright_install.log 2>&1
if !errorlevel! neq 0 (
    echo ^ Warning: Playwright browser installation had issues
    echo   This might cause "Executable doesn't exist" errors during testing
    if exist playwright_install.log (
        echo.
        echo Installation details:
        type playwright_install.log
    )
    echo.
    echo   You can manually install later with: npx playwright install chromium
    echo   Continuing with server startup...
) else (
    echo + Playwright browsers ready
)

if exist playwright_install.log del playwright_install.log

:check_config
echo.
echo [5/5] Checking configuration file...
if not exist ".env" (
    echo ^ First run, creating configuration file...
    
    if exist ".env.example" (
        copy ".env.example" ".env" >nul 2>&1
        if !errorlevel! neq 0 (
            echo ^ Warning: Could not copy .env.example, creating basic .env
            goto create_basic_env
        )
        echo + Configuration file created from template
    ) else (
        :create_basic_env
        echo # Intent Test Framework - Local Proxy Configuration > .env
        echo. >> .env
        echo # AI API Configuration ^(Required^) >> .env
        echo OPENAI_API_KEY=your-api-key-here >> .env
        echo OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 >> .env
        echo MIDSCENE_MODEL_NAME=qwen-vl-max-latest >> .env
        echo. >> .env
        echo # Server Configuration >> .env
        echo PORT=3001 >> .env
        echo + Basic configuration file created
    )
    
    echo.
    echo ! IMPORTANT: Please configure your AI API key
    echo.
    echo Configuration file: .env
    echo Please edit this file and add your AI API key
    echo.
    echo After configuration, run this script again
    echo.
    
    REM Try to open notepad, but don't fail if it doesn't work
    start notepad .env 2>nul
    pause
    exit /b 0
)

echo + Configuration file exists

REM Final startup
echo.
echo ========================================
echo   Starting Server
echo ========================================
echo.
echo ^ Starting Intent Test Framework Local Proxy Server...
echo.
echo Server startup messages:
echo - If you see "Server listening" - SUCCESS!
echo - If you see error messages - check configuration
echo.
echo After successful startup:
echo 1. Return to the Web interface
echo 2. Select "Local Proxy Mode"
echo 3. Start running your tests
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server with comprehensive error handling
node midscene_server.js 2>&1
set SERVER_EXIT_CODE=!errorlevel!

echo.
echo ========================================
if !SERVER_EXIT_CODE! equ 0 (
    echo ^ Server stopped normally
) else (
    echo X Server exited with error code: !SERVER_EXIT_CODE!
    echo.
    echo Common issues and solutions:
    echo 1. Port 3001 in use - Close other applications using this port
    echo 2. Missing API key - Edit .env file and add valid OPENAI_API_KEY
    echo 3. Network issues - Check internet connection
    echo 4. Permission issues - Try running as administrator
    echo 5. Node.js issues - Reinstall Node.js from https://nodejs.org/
    echo.
    echo Check the error messages above for specific details
)

pause