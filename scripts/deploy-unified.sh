#!/bin/bash
# 本地开发部署脚本 - 统一启动所有服务

set -e

echo "🚀 启动 AI4SE 工具集..."
echo ""

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，正在复制 .env.example..."
    cp .env.example .env
    echo "✅ 请编辑 .env 文件配置必要的环境变量"
    echo ""
fi

# 启动所有服务
echo "📦 启动 Docker 容器..."
docker-compose -f docker-compose.new.yml up -d

echo ""
echo "⏳ 等待服务启动..."
sleep 5

echo ""
echo "✅ 所有服务已启动！"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 访问地址："
echo "   统一入口（Homepage）: http://localhost"
echo "   意图测试工具: http://localhost/intent-tester"
echo "   AI 智能体: http://localhost/ai-agents"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 提示："
echo "   - 查看日志: docker-compose -f docker-compose.new.yml logs -f"
echo "   - 停止服务: docker-compose -f docker-compose.new.yml down"
echo "   - 重启服务: docker-compose -f docker-compose.new.yml restart"
echo ""
