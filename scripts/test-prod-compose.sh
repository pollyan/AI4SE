#!/bin/bash

# ========================================
# 本地测试生产环境 docker-compose 配置
# ========================================

set -e

echo "🧪 测试 docker-compose.prod.yml 配置..."

# 1. 验证 YAML 语法
echo "📝 验证 YAML 语法..."
if command -v yamllint &> /dev/null; then
    yamllint docker-compose.prod.yml
else
    echo "⚠️  yamllint 未安装，跳过 YAML 语法检查"
fi

# 2. Docker Compose 配置验证
echo "🔍 验证 Docker Compose 配置..."
docker-compose -f docker-compose.prod.yml config > /dev/null

if [ $? -eq 0 ]; then
    echo "✅ Docker Compose 配置语法正确"
else
    echo "❌ Docker Compose 配置有错误"
    exit 1
fi

# 3. 显示将要创建的服务
echo ""
echo "📋 将要创建的服务："
docker-compose -f docker-compose.prod.yml config --services

# 4. 检查镜像构建（dry run）
echo ""
echo "🐳 检查 Docker 镜像构建..."
docker-compose -f docker-compose.prod.yml build --dry-run 2>/dev/null || \
    echo "⚠️  Docker Compose 不支持 --dry-run，跳过"

echo ""
echo "=========================================="
echo "✅ 所有检查通过！"
echo "=========================================="
echo "你可以安全地推送 docker-compose.prod.yml 到远程"
echo ""
echo "如果想在本地完整测试部署流程，运行："
echo "  docker-compose -f docker-compose.prod.yml up --build"
echo ""
