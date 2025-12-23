#!/bin/bash
# 快速重启脚本 - 用于重新加载配置或重启服务
# 注意: 代码更改无需重启,volumes 挂载会自动同步,Flask 会自动重载
# 仅在需要重新加载环境变量或重启服务时使用

set -e

echo "========================================"
echo "  快速重启 Docker 容器"
echo "========================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}[1/2]${NC} 重启容器..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart web-app

echo -e "${YELLOW}[2/2]${NC} 等待服务启动..."
sleep 10

if docker ps | grep -q "intent-test-web"; then
    echo -e "${GREEN}✓${NC} 容器重启成功"
    echo ""
    echo "服务地址: http://localhost:5001"
else
    echo "容器未运行，请使用完整部署脚本: ./scripts/deploy-local.sh"
    exit 1
fi
