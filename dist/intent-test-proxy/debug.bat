@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   Debug: Testing npm detection
echo ========================================

echo Testing npm command directly...
npm --version
echo npm direct command exit code: !errorlevel!

echo.
echo Testing npm with error redirection...
npm --version >temp_output.txt 2>&1
set NPM_EXIT_CODE=!errorlevel!
echo npm redirect exit code: !NPM_EXIT_CODE!

echo.
echo Output content:
type temp_output.txt
del temp_output.txt 2>nul

echo.
echo Testing npm quiet version...
npm --version >nul 2>&1
echo npm quiet exit code: !errorlevel!

echo.
echo Testing where npm...
where npm
echo where npm exit code: !errorlevel!

echo.
echo PATH contains:
echo !PATH!

pause