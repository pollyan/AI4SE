#!/bin/bash

# AI4SE工具集 - 本地开发环境完整启动脚本
# 这是一个更详细的启动脚本，包含完整的环境检查和服务管理功能
# 由主脚本 ../../dev.sh 调用

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "📍 项目根目录: $PROJECT_ROOT"
echo "📍 脚本目录: $SCRIPT_DIR"

cd "$PROJECT_ROOT"

# 检查Python环境
echo "🐍 检查Python环境..."
python3 --version
pip3 --version || echo "⚠️ pip3 不可用，可能需要安装"

# 检查虚拟环境
if [[ -d "venv" ]]; then
    echo "📦 发现虚拟环境，正在激活..."
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "⚠️ 未找到虚拟环境，使用系统Python"
fi

# 检查依赖
echo "📋 检查Python依赖..."
if [[ -f "requirements.txt" ]]; then
    echo "发现 requirements.txt，检查关键依赖..."
    python3 -c "import flask; print('✅ Flask 可用')" 2>/dev/null || echo "❌ Flask 不可用"
    python3 -c "import sqlite3; print('✅ SQLite 可用')" 2>/dev/null || echo "❌ SQLite 不可用"
else
    echo "⚠️ 未找到 requirements.txt"
fi

# 检查数据库
echo "🗄️ 检查数据库..."
if [[ -f "data/local/intent_test_framework.db" ]]; then
    echo "✅ 本地数据库文件存在"
else
    echo "⚠️ 本地数据库文件不存在，将在首次运行时创建"
fi

# 启动服务的实际逻辑由主脚本处理
echo "🚀 准备启动服务..."
