#!/usr/bin/env node

/**
 * 本地代理服务器打包脚本
 * 生成可分发的代理包，包含所有必要文件和启动脚本
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const PACKAGE_NAME = 'intent-test-proxy';
const BUILD_DIR = path.join(__dirname, '..', 'dist', PACKAGE_NAME);

console.log('🚀 开始构建本地代理服务器包...');

// 创建构建目录
if (fs.existsSync(BUILD_DIR)) {
    fs.rmSync(BUILD_DIR, { recursive: true });
}
fs.mkdirSync(BUILD_DIR, { recursive: true });

// 复制核心文件
console.log('📁 复制核心文件...');

// 复制服务器文件
fs.copyFileSync(
    path.join(__dirname, '..', 'midscene_server.js'),
    path.join(BUILD_DIR, 'midscene_server.js')
);

// 创建精简的package.json
const packageJson = {
    "name": "intent-test-proxy",
    "version": "1.0.0",
    "description": "Intent Test Framework 本地代理服务器",
    "main": "midscene_server.js",
    "scripts": {
        "start": "node midscene_server.js",
        "install-deps": "npm install"
    },
    "dependencies": {
        "@midscene/web": "^0.22.1",
        "@playwright/test": "^1.45.0",
        "axios": "^1.10.0",
        "cors": "^2.8.5",
        "express": "^4.18.2",
        "playwright": "^1.45.0",
        "socket.io": "^4.7.0"
    },
    "devDependencies": {
        "@types/node": "^20.0.0"
    },
    "keywords": ["midscene", "automation", "testing", "ai"],
    "author": "Intent Test Framework",
    "license": "MIT"
};

fs.writeFileSync(
    path.join(BUILD_DIR, 'package.json'),
    JSON.stringify(packageJson, null, 2)
);

// 创建环境变量模板
console.log('⚙️ 创建配置模板...');
const envTemplate = `# Intent Test Framework 本地代理服务器配置

# AI API配置 (必填)
# 选择以下其中一种配置方式：

# 方式1: 阿里云DashScope (推荐)
OPENAI_API_KEY=sk-your-dashscope-api-key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest

# 方式2: OpenAI
# OPENAI_API_KEY=sk-your-openai-api-key
# OPENAI_BASE_URL=https://api.openai.com/v1
# MIDSCENE_MODEL_NAME=gpt-4o

# 服务器配置 (可选)
# PORT=3001

# 浏览器配置 (可选)
# BROWSER_HEADLESS=false
# BROWSER_TIMEOUT=30000
`;

fs.writeFileSync(path.join(BUILD_DIR, '.env.example'), envTemplate);

// 创建Windows启动脚本 (使用修复后的版本)
console.log('🖥️ 创建启动脚本...');
const windowsScript = `@echo off
chcp 65001 >nul
title Intent Test Framework - Local Proxy Server [FIXED VERSION]
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Intent Test Framework Local Proxy
echo   [FINAL FIXED VERSION - No Interruption]
echo ========================================
echo.

REM Step 1: Check Node.js
echo [1/5] Checking Node.js environment...
for /f "tokens=*" %%i in ('node --version 2^>nul') do set NODE_VERSION=%%i
if "!NODE_VERSION!"=="" (
    echo X Error: Node.js not detected
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
echo + Node.js version: !NODE_VERSION!

REM Step 2: Skip npm check (causes issues)
echo.
echo [2/5] npm check...
echo + npm: Will be tested during installation

REM Step 3: Dependencies
echo.
echo [3/5] Installing dependencies...

if exist "node_modules\\@playwright\\test" (
    if exist "node_modules\\axios" (
        echo + Dependencies already exist, skipping installation
        goto step4_playwright
    )
)

echo ^ node_modules missing or incomplete
echo ^ Running npm install...
echo   Please wait, this may take several minutes...
echo   Note: npm warnings are normal and will not interrupt installation
echo.

REM Redirect stderr to capture warnings but continue on success
npm install --no-audit --no-fund 2>npm_install.log
set NPM_EXIT_CODE=!errorlevel!

REM Show any warnings/errors from log, but only fail on actual errors
if exist npm_install.log (
    findstr /i "warn" npm_install.log >nul && (
        echo ^ npm warnings detected ^(normal, continuing...^)
    )
    findstr /i "error" npm_install.log >nul && (
        echo ^ npm errors detected:
        type npm_install.log
    )
    del npm_install.log
)

if !NPM_EXIT_CODE! neq 0 (
    echo.
    echo X npm install failed ^(exit code: !NPM_EXIT_CODE!^)
    echo Try: 1^) Run as administrator 2^) npm cache clean --force 3^) npm config set registry https://registry.npmmirror.com
    pause
    exit /b 1
)

echo + npm install completed successfully!

:step4_playwright
REM Step 4: Playwright browsers
echo.
echo [4/5] Installing Playwright browsers...
echo ^ Installing Chromium browser...
echo   This may take 2-5 minutes and show download progress...
echo.

REM Redirect stderr to handle warnings gracefully  
npx playwright install chromium 2>playwright_install.log
set PLAYWRIGHT_EXIT_CODE=!errorlevel!

REM Show log content but don't fail on warnings
if exist playwright_install.log (
    findstr /i "warn" playwright_install.log >nul && (
        echo ^ Playwright installation warnings ^(normal^)
    )
    findstr /i "error" playwright_install.log >nul && (
        echo ^ Playwright installation errors:
        type playwright_install.log
    )
    del playwright_install.log
)

if !PLAYWRIGHT_EXIT_CODE! neq 0 (
    echo ^ Warning: Playwright browser installation had issues ^(exit code: !PLAYWRIGHT_EXIT_CODE!^)
    echo   You can install manually later: npx playwright install chromium
    echo   Continuing with server startup...
) else (
    echo + Playwright browsers installed successfully
)

REM Step 5: Configuration and startup
echo.
echo [5/5] Configuration and server startup...

if not exist ".env" (
    echo ^ Creating configuration file...
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
    ) else (
        echo OPENAI_API_KEY=your-api-key-here > .env
        echo OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 >> .env
        echo MIDSCENE_MODEL_NAME=qwen-vl-max-latest >> .env
        echo PORT=3001 >> .env
    )
    echo + Configuration file created
    echo.
    echo ========================================
    echo   CONFIGURATION REQUIRED
    echo ========================================
    echo.
    echo Please edit .env file and set your API key
    echo Current placeholder: 'your-api-key-here'
    echo.
    start notepad .env 2>nul
    echo After editing, run this script again.
    pause
    exit /b 0
)

echo + Configuration file exists

REM Check API key
findstr /c:"your-api-key-here" .env >nul
if !errorlevel! equ 0 (
    echo X Please set your actual API key in .env file
    start notepad .env 2>nul
    pause
    exit /b 0
)

echo + API key configured

echo.
echo ========================================
echo   ALL STEPS COMPLETED - STARTING SERVER
echo ========================================
echo.
echo ^ Starting Intent Test Framework Local Proxy Server...
echo.
echo What to expect:
echo - Server will show startup messages
echo - Look for "Server listening on port 3001"
echo - Then go to Web interface and select "Local Proxy Mode"
echo.
echo Press Ctrl+C to stop the server
echo.

node midscene_server.js

set EXIT_CODE=!errorlevel!
echo.
echo ========================================
echo Server stopped ^(exit code: !EXIT_CODE!^)

if !EXIT_CODE! neq 0 (
    echo.
    echo Possible issues:
    echo 1. API key invalid or missing
    echo 2. Port 3001 already in use
    echo 3. Network connectivity issues
    echo 4. Missing dependencies
)

echo.
echo Script execution completed.
pause
`;

fs.writeFileSync(path.join(BUILD_DIR, 'start.bat'), windowsScript);

// 创建Mac/Linux启动脚本
const unixScript = `#!/bin/bash

# Intent Test Framework 本地代理服务器启动脚本

# 设置颜色输出
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

echo ""
echo "========================================"
echo "  Intent Test Framework 本地代理服务器"
echo "========================================"
echo ""

# 检查Node.js
echo -e "\${BLUE}[1/4]\${NC} 检查Node.js环境..."
if ! command -v node &> /dev/null; then
    echo -e "\${RED}❌ 错误: 未检测到Node.js\${NC}"
    echo ""
    echo "请先安装Node.js:"
    echo "https://nodejs.org/"
    echo ""
    echo "建议安装LTS版本 (16.x或更高)"
    exit 1
fi

NODE_VERSION=\$(node --version)
echo -e "\${GREEN}✅ Node.js版本: \$NODE_VERSION\${NC}"

# 检查npm
if ! command -v npm &> /dev/null; then
    echo -e "\${RED}❌ 错误: npm未找到\${NC}"
    exit 1
fi

# 检查和安装依赖
echo ""
echo -e "\${BLUE}[2/4]\${NC} 检查依赖包..."

# 检查关键依赖是否存在
PLAYWRIGHT_TEST_MISSING=false
AXIOS_MISSING=false

if [ ! -d "node_modules/@playwright/test" ]; then
    PLAYWRIGHT_TEST_MISSING=true
fi

if [ ! -d "node_modules/axios" ]; then
    AXIOS_MISSING=true
fi

# 如果关键依赖缺失或node_modules不存在，则重新安装
if [ ! -d "node_modules" ] || [ "\$PLAYWRIGHT_TEST_MISSING" = true ] || [ "\$AXIOS_MISSING" = true ]; then
    echo -e "\${YELLOW}📦 安装/更新依赖包...\${NC}"
    echo "这可能需要几分钟时间，请耐心等待..."
    
    # 清理旧的依赖
    if [ -d "node_modules" ]; then
        echo -e "\${YELLOW}🧹 清理旧依赖...\${NC}"
        rm -rf node_modules package-lock.json
    fi
    
    # 安装依赖
    npm install
    if [ \$? -ne 0 ]; then
        echo -e "\${RED}❌ 依赖安装失败\${NC}"
        echo ""
        echo "可能的解决方案:"
        echo "1. 检查网络连接"
        echo "2. 清理npm缓存: npm cache clean --force"
        echo "3. 使用国内镜像: npm config set registry https://registry.npmmirror.com"
        exit 1
    fi
    
    # 验证关键依赖
    if [ ! -d "node_modules/@playwright/test" ]; then
        echo -e "\${RED}❌ @playwright/test 依赖安装失败\${NC}"
        exit 1
    fi
    
    if [ ! -d "node_modules/axios" ]; then
        echo -e "\${RED}❌ axios 依赖安装失败\${NC}"
        exit 1
    fi
    
    echo -e "\${GREEN}✅ 依赖安装完成\${NC}"
else
    echo -e "\${GREEN}✅ 依赖包已存在\${NC}"
fi

# 检查配置文件
echo ""
echo -e "\${BLUE}[3/4]\${NC} 检查配置文件..."
if [ ! -f ".env" ]; then
    echo -e "\${YELLOW}⚙️ 首次运行，创建配置文件...\${NC}"
    cp .env.example .env
    echo ""
    echo -e "\${YELLOW}⚠️  重要: 请配置AI API密钥\${NC}"
    echo ""
    echo "配置文件已创建: .env"
    echo "请编辑此文件，添加您的AI API密钥"
    echo ""
    echo "配置完成后，请重新运行此脚本"
    echo ""
    echo "编辑配置文件: nano .env"
    exit 0
fi

echo -e "\${GREEN}✅ 配置文件存在\${NC}"

# 启动服务器
echo ""
echo -e "\${BLUE}[4/4]\${NC} 启动服务器..."
echo ""
echo -e "\${GREEN}🚀 正在启动Intent Test Framework本地代理服务器...\${NC}"
echo ""
echo "启动成功后，请返回Web界面选择"本地代理模式""
echo "按 Ctrl+C 可停止服务器"
echo ""

node midscene_server.js

echo ""
echo "服务器已停止"
`;

fs.writeFileSync(path.join(BUILD_DIR, 'start.sh'), unixScript);

// 设置Unix脚本执行权限
try {
    execSync(`chmod +x "${path.join(BUILD_DIR, 'start.sh')}"`);
} catch (error) {
    console.warn('⚠️ 无法设置start.sh执行权限 (Windows环境下正常)');
}

// 创建README文档
console.log('📝 创建说明文档...');
const readme = `# Intent Test Framework - 本地代理服务器

## 快速开始

### 1. 启动服务器

**Windows:**
双击 \`start.bat\` 文件

**Mac/Linux:**
双击 \`start.sh\` 文件，或在终端中运行：
\`\`\`bash
./start.sh
\`\`\`

### 2. 配置AI API密钥

首次运行会自动创建配置文件 \`.env\`，请编辑此文件添加您的AI API密钥：

\`\`\`env
# 阿里云DashScope (推荐)
OPENAI_API_KEY=sk-your-dashscope-api-key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest
\`\`\`

### 3. 开始使用

配置完成后重新运行启动脚本，看到以下信息表示启动成功：

\`\`\`
🚀 MidSceneJS本地代理服务器启动成功
🌐 HTTP服务器: http://localhost:3001
🔌 WebSocket服务器: ws://localhost:3001
✨ 服务器就绪，等待测试执行请求...
\`\`\`

然后返回Web界面，选择"本地代理模式"即可使用！

## 系统要求

- Node.js 16.x 或更高版本
- 至少 2GB 可用内存
- 稳定的网络连接 (用于AI API调用)

## 故障排除

### Node.js未安装
请访问 https://nodejs.org/ 下载并安装Node.js LTS版本

### 端口被占用
如果3001端口被占用，可以在 \`.env\` 文件中修改：
\`\`\`env
PORT=3002
\`\`\`

### 依赖安装失败
尝试清除缓存后重新安装：
\`\`\`bash
npm cache clean --force
rm -rf node_modules
npm install
\`\`\`

### AI API调用失败
1. 检查API密钥是否正确
2. 确认账户余额充足
3. 检查网络连接
4. 验证BASE_URL和MODEL_NAME配置

## 技术支持

如遇问题，请检查：
1. 控制台错误信息
2. 网络连接状态
3. API密钥配置
4. 防火墙设置

---

Intent Test Framework - AI驱动的Web自动化测试平台
`;

fs.writeFileSync(path.join(BUILD_DIR, 'README.md'), readme);

console.log('✅ 构建完成！');
console.log(`📦 代理包位置: ${BUILD_DIR}`);
console.log('');
console.log('📋 包含文件:');
console.log('  - midscene_server.js    (服务器主文件)');
console.log('  - package.json          (依赖配置)');
console.log('  - .env.example          (配置模板)');
console.log('  - start.bat             (Windows启动脚本)');
console.log('  - start.sh              (Mac/Linux启动脚本)');
console.log('  - README.md             (使用说明)');
console.log('');
console.log('🎯 下一步: 将整个文件夹打包为ZIP文件供用户下载');
