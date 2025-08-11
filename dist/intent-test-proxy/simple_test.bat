@echo off
setlocal enabledelayedexpansion

echo === Simple npm test ===

echo Step 1: Direct npm call
npm --version
echo Exit code: !errorlevel!

echo.
echo Step 2: npm with redirection
npm --version >nul 2>&1
echo Exit code: !errorlevel!

echo.
echo Step 3: Version capture
for /f "tokens=*" %%i in ('npm --version 2^>nul') do set NPM_VER=%%i
echo Captured version: !NPM_VER!

echo.
echo Test completed
pause