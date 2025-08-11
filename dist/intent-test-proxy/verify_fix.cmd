@echo off
setlocal enabledelayedexpansion

echo Testing the Windows script fix...
echo.

REM Test the fixed variable expansion
for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo Node.js version captured: !NODE_VERSION!

if "!NODE_VERSION!"=="" (
    echo FAILED: Variable expansion not working
) else (
    echo SUCCESS: Variable expansion is working correctly
)

echo.
echo Testing errorlevel handling...
node --version >nul 2>&1
if !errorlevel! equ 0 (
    echo SUCCESS: Node.js detected and errorlevel handling works
) else (
    echo FAILED: Node.js detection failed
)

echo.
echo Fix verification completed!