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

REM Check npm availability without version check
echo.
echo [2/5] Checking npm availability...
npm help >nul 2>&1
if !errorlevel! neq 0 (
    echo X Error: npm command not working
    echo.
    echo This usually indicates:
    echo   1. npm is not installed properly
    echo   2. npm is corrupted
    echo   3. PATH issues
    echo.
    echo Solutions:
    echo   1. Reinstall Node.js from https://nodejs.org/
    echo   2. Run "npm doctor" to diagnose npm issues
    echo   3. Try running as administrator
    pause
    exit /b 1
)
echo + npm command is available

REM Check and install dependencies
echo.
echo [3/5] Checking dependencies...

REM Check if we need to install
set NEED_INSTALL=false
if not exist "node_modules" (
    set NEED_INSTALL=true
    echo ^ node_modules folder not found
)
if not exist "package.json" (
    echo ^ package.json not found, creating basic package.json
    goto create_package_json
)

if "!NEED_INSTALL!"=="false" (
    if exist "node_modules\@playwright\test" (
        if exist "node_modules\axios" (
            echo + Dependencies already exist
            goto check_playwright
        )
    )
    set NEED_INSTALL=true
    echo ^ Some dependencies missing
)

if "!NEED_INSTALL!"=="true" goto install_deps
goto check_playwright

:create_package_json
echo + Creating package.json...
(
echo {
echo   "name": "intent-test-proxy",
echo   "version": "1.0.0",
echo   "description": "Intent Test Framework Local Proxy",
echo   "main": "midscene_server.js",
echo   "scripts": {
echo     "start": "node midscene_server.js"
echo   },
echo   "dependencies": {
echo     "@midscene/web": "^0.22.1",
echo     "@playwright/test": "^1.45.0",
echo     "axios": "^1.10.0",
echo     "cors": "^2.8.5",
echo     "dotenv": "^17.2.0",
echo     "express": "^4.18.2",
echo     "playwright": "^1.45.0",
echo     "socket.io": "^4.7.0"
echo   }
echo }
) > package.json
echo + package.json created

:install_deps
echo.
echo ========================================
echo   DEPENDENCY INSTALLATION
echo ========================================
echo.
echo This step may take 5-15 minutes depending on your internet speed.
echo The script will continue automatically when installation completes.
echo.
echo Progress indicators:
echo - If you see package names scrolling = Installation in progress  
echo - If screen stops for long time = Check network or try Ctrl+C then restart
echo - Installation complete when you see dependency verification
echo.

REM Clean old installation
if exist "node_modules" (
    echo ^ Removing old node_modules...
    rmdir /s /q "node_modules" 2>nul
    echo + Old dependencies cleaned
)
if exist "package-lock.json" (
    del "package-lock.json" 2>nul
)

echo ^ Starting npm install...
echo   This may appear to hang but is likely still working...
echo.

REM Try npm install with timeout mechanism
set "install_start_time=%time%"

REM Create a background monitoring script
echo @echo off > npm_monitor.bat
echo timeout /t 300 /nobreak ^>nul >> npm_monitor.bat
echo echo. >> npm_monitor.bat
echo echo [Monitor] Installation has been running for 5 minutes... >> npm_monitor.bat
echo echo [Monitor] This is normal for first-time installation >> npm_monitor.bat
echo echo [Monitor] Please wait, npm install is likely still working... >> npm_monitor.bat
echo del npm_monitor.bat >> npm_monitor.bat

REM Start monitoring in background and run install
start /b npm_monitor.bat
npm install --verbose --no-audit --no-fund

set INSTALL_RESULT=!errorlevel!

REM Kill monitor if still running
taskkill /f /im timeout.exe >nul 2>&1

if !INSTALL_RESULT! neq 0 (
    echo.
    echo X npm install failed with exit code !INSTALL_RESULT!
    echo.
    echo Common causes and solutions:
    echo 1. Network connectivity issues
    echo    - Check internet connection
    echo    - Try: npm config set registry https://registry.npmmirror.com
    echo.
    echo 2. Permission issues  
    echo    - Close this window
    echo    - Right-click start.bat and select "Run as administrator"
    echo.
    echo 3. npm cache corruption
    echo    - Run: npm cache clean --force
    echo    - Then run this script again
    echo.
    echo 4. Firewall/antivirus blocking npm
    echo    - Temporarily disable antivirus
    echo    - Check Windows Firewall settings
    echo.
    pause
    exit /b 1
)

echo.
echo + npm install completed successfully!

REM Verify critical dependencies
echo ^ Verifying installed packages...

if not exist "node_modules" (
    echo X node_modules folder still missing after installation
    pause
    exit /b 1
)

if not exist "node_modules\@playwright\test" (
    echo X @playwright/test missing - attempting individual install...
    npm install @playwright/test
)

if not exist "node_modules\axios" (
    echo X axios missing - attempting individual install...
    npm install axios
)

echo + Dependencies verified

:check_playwright
echo.
echo [4/5] Installing Playwright browsers...
echo.
echo ^ Installing Chromium browser for automation...
echo   This step installs the actual browser that will run your tests.
echo   It may take 2-5 minutes depending on your internet speed.
echo.

npx playwright install chromium 2>&1
if !errorlevel! neq 0 (
    echo.
    echo ^ Warning: Playwright browser installation had issues
    echo.
    echo This might cause "Executable doesn't exist" errors during testing.
    echo You can manually install later with:
    echo   npx playwright install chromium
    echo.
    echo Continuing with server startup...
) else (
    echo + Playwright browser installation completed
)

:check_config
echo.
echo [5/5] Configuration setup...

if not exist ".env" (
    echo ^ Creating configuration file...
    
    if exist ".env.example" (
        copy ".env.example" ".env" >nul 2>&1
        if !errorlevel! equ 0 (
            echo + Configuration created from template
        ) else (
            goto create_default_env
        )
    ) else (
        :create_default_env
        echo # Intent Test Framework - Local Proxy Server > .env
        echo. >> .env
        echo # AI API Configuration ^(REQUIRED^) >> .env
        echo # Please replace 'your-api-key-here' with your actual API key >> .env
        echo OPENAI_API_KEY=your-api-key-here >> .env
        echo OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 >> .env
        echo MIDSCENE_MODEL_NAME=qwen-vl-max-latest >> .env
        echo. >> .env
        echo # Server Configuration >> .env
        echo PORT=3001 >> .env
        echo + Default configuration created
    )
    
    echo.
    echo ========================================
    echo   IMPORTANT: API KEY REQUIRED
    echo ========================================
    echo.
    echo Before starting the server, you need to:
    echo 1. Edit the .env file
    echo 2. Replace 'your-api-key-here' with your actual API key
    echo 3. Save the file
    echo 4. Run this script again
    echo.
    
    start notepad .env >nul 2>&1
    if !errorlevel! neq 0 (
        echo Configuration file location: %cd%\.env
        echo Please edit this file manually with any text editor
    )
    
    echo.
    pause
    exit /b 0
) else (
    echo + Configuration file exists
)

REM Final server startup
echo.
echo ========================================
echo   STARTING SERVER
echo ========================================
echo.

REM Check if API key is configured
findstr /c:"your-api-key-here" .env >nul
if !errorlevel! equ 0 (
    echo.
    echo X Warning: Default API key detected in .env file
    echo.
    echo Please edit .env and set your actual API key before starting.
    echo Current placeholder: 'your-api-key-here'
    echo.
    echo Opening .env for editing...
    start notepad .env >nul 2>&1
    echo.
    echo After editing, run this script again.
    pause
    exit /b 0
)

echo + Starting Intent Test Framework Local Proxy Server...
echo.
echo What you should see after successful startup:
echo   ^> Server listening on port 3001
echo   ^> WebSocket server ready  
echo   ^> MidScene AI agent initialized
echo.
echo If you see these messages = SUCCESS! 
echo Then go to your web interface and select "Local Proxy Mode"
echo.
echo Press Ctrl+C to stop the server when done
echo.
echo ========================================

node midscene_server.js

set SERVER_CODE=!errorlevel!
echo.
echo ========================================

if !SERVER_CODE! equ 0 (
    echo + Server stopped normally
) else (
    echo X Server exited with error code !SERVER_CODE!
    echo.
    echo Troubleshooting guide:
    echo.
    echo Error Code !SERVER_CODE! usually means:
    if !SERVER_CODE! equ 1 (
        echo - Missing or invalid AI API key
        echo - Check your .env file configuration
    )
    if !SERVER_CODE! equ 3221225786 (
        echo - Ctrl+C was pressed ^(normal shutdown^)
    )
    echo.
    echo General solutions:
    echo 1. Verify API key in .env file
    echo 2. Check internet connection  
    echo 3. Ensure port 3001 is not in use
    echo 4. Try running as administrator
    echo 5. Check Windows Firewall settings
)

echo.
pause