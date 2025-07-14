#!/bin/bash

# Intent Test Framework 本地代理服务器依赖修复脚本

echo "========================================"
echo "  Intent Test Framework 依赖修复"
echo "========================================"
echo ""

# 检查当前目录
if [ ! -f "package.json" ]; then
    echo "❌ 错误：请在包含 package.json 的目录中运行此脚本"
    exit 1
fi

echo "[1/5] 清理旧的依赖..."
rm -rf node_modules package-lock.json
echo "✅ 清理完成"

echo "[2/5] 重新安装基础依赖..."
npm install
echo "✅ 基础依赖安装完成"

echo "[3/5] 安装 Playwright 相关依赖..."
npm install @playwright/test playwright
echo "✅ Playwright 依赖安装完成"

echo "[4/5] 安装 Playwright 浏览器..."
npx playwright install chromium
echo "✅ Playwright 浏览器安装完成"

echo "[5/5] 验证依赖..."
node -e "
try {
    require('@playwright/test');
    require('playwright');
    require('@midscene/web');
    console.log('✅ 所有依赖验证通过');
} catch (error) {
    console.log('❌ 依赖验证失败:', error.message);
    process.exit(1);
}
"

echo ""
echo "🎉 依赖修复完成！"
echo ""
echo "现在您可以运行："
echo "  bash start.sh"
echo ""
echo "或者直接运行："
echo "  node midscene_server.js"
echo ""