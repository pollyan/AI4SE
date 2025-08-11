@echo off
chcp 65001 >nul
title Intent Test Framework - 本地代理服务器

echo.
echo ========================================
echo   Intent Test Framework 本地代理服务器
echo ========================================
echo.

REM 检查Node.js
echo [1/4] 检查Node.js环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未检测到Node.js
    echo.
    echo 请先安装Node.js:
    echo https://nodejs.org/
    echo.
    echo 建议安装LTS版本 ^(16.x或更高^)
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
echo ✅ Node.js版本: %NODE_VERSION%

REM 检查npm
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: npm未找到
    pause
    exit /b 1
)

REM 检查和安装依赖
echo.
echo [2/4] 检查依赖包...

REM 检查关键依赖是否存在
set PLAYWRIGHT_TEST_MISSING=false
set AXIOS_MISSING=false

if not exist "node_modules\@playwright\test" (
    set PLAYWRIGHT_TEST_MISSING=true
)

if not exist "node_modules\axios" (
    set AXIOS_MISSING=true
)

REM 如果关键依赖缺失或node_modules不存在，则重新安装
if not exist node_modules (
    goto install_deps
)
if "%PLAYWRIGHT_TEST_MISSING%"=="true" (
    goto install_deps
)
if "%AXIOS_MISSING%"=="true" (
    goto install_deps
)

echo ✅ 依赖包已存在
goto check_config

:install_deps
echo 📦 安装/更新依赖包...
echo 这可能需要几分钟时间，请耐心等待...

REM 清理旧的依赖
if exist node_modules (
    echo 🧹 清理旧依赖...
    rmdir /s /q node_modules
    if exist package-lock.json (
        del package-lock.json
    )
)

REM 安装依赖
npm install
if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败
    echo.
    echo 可能的解决方案:
    echo 1. 检查网络连接
    echo 2. 清理npm缓存: npm cache clean --force
    echo 3. 使用国内镜像: npm config set registry https://registry.npmmirror.com
    pause
    exit /b 1
)

REM 验证关键依赖
if not exist "node_modules\@playwright\test" (
    echo ❌ @playwright/test 依赖安装失败
    pause
    exit /b 1
)

if not exist "node_modules\axios" (
    echo ❌ axios 依赖安装失败
    pause
    exit /b 1
)

echo ✅ 依赖安装完成

:check_config

REM 检查配置文件
echo.
echo [3/4] 检查配置文件...
if not exist .env (
    echo ⚙️ 首次运行，创建配置文件...
    copy .env.example .env >nul
    echo.
    echo ⚠️  重要: 请配置AI API密钥
    echo.
    echo 配置文件已创建: .env
    echo 请编辑此文件，添加您的AI API密钥
    echo.
    echo 配置完成后，请重新运行此脚本
    echo.
    notepad .env
    pause
    exit /b 0
)

echo ✅ 配置文件存在

REM 启动服务器
echo.
echo [4/4] 启动服务器...
echo.
echo 🚀 正在启动Intent Test Framework本地代理服务器...
echo.
echo 启动成功后，请返回Web界面选择"本地代理模式"
echo 按 Ctrl+C 可停止服务器
echo.

node midscene_server.js

echo.
echo 服务器已停止
pause
