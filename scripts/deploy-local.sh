#!/bin/bash
# 本地 Docker 开发环境部署脚本
# 启用代码热更新 - 代码改动实时同步,Flask 自动重载
# 注意: 如果修改了依赖(requirements.txt),需要重新运行此脚本重新构建镜像

set -e  # 遇到错误立即退出

echo "========================================"
echo "  本地 Docker 环境部署"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录(脚本在 scripts/ 目录下,需要向上一级)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 步骤 1: 停止并删除现有容器
echo -e "${YELLOW}[1/6]${NC} 停止现有容器..."
docker-compose down 2>/dev/null || true
echo -e "${GREEN}✓${NC} 容器已停止"
echo ""

# 步骤 2: 清理旧镜像（可选，取消注释以启用）
# echo -e "${YELLOW}[2/6]${NC} 清理旧镜像..."
# docker rmi intent-test-framework-web-app 2>/dev/null || true
# echo -e "${GREEN}✓${NC} 旧镜像已清理"
# echo ""

# 步骤 3: 强制重新构建镜像（不使用缓存）
echo -e "${YELLOW}[2/6]${NC} 构建 Docker 镜像（无缓存）..."
echo "   这可能需要 2-3 分钟..."
docker-compose build --no-cache web-app
echo -e "${GREEN}✓${NC} 镜像构建完成"
echo ""

# 步骤 4: 启动所有服务(开发模式 - 支持代码热更新)
echo -e "${YELLOW}[3/6]${NC} 启动容器(开发模式 - 代码实时同步)..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
echo -e "${GREEN}✓${NC} 容器已启动(代码热更新已启用)"
echo ""

# 步骤 5: 等待服务健康
echo -e "${YELLOW}[4/6]${NC} 等待服务启动..."
sleep 10

# 检查容器状态
echo -e "${YELLOW}[5/6]${NC} 验证容器状态..."
if docker ps | grep -q "intent-test-web.*healthy"; then
    echo -e "${GREEN}✓${NC} 容器运行正常"
else
    if docker ps | grep -q "intent-test-web"; then
        echo -e "${YELLOW}!${NC} 容器运行中，等待健康检查..."
        sleep 10
    else
        echo -e "${RED}✗${NC} 容器未运行！"
        echo "查看日志："
        docker logs intent-test-web --tail=50
        exit 1
    fi
fi
echo ""

# 步骤 6: 验证代码已更新
echo -e "${YELLOW}[6/6]${NC} 验证代码更新..."
if docker exec intent-test-web python3 -c "
import sys
sys.path.insert(0, '/app')
from web_gui.services.langgraph_agents.lisa_v2.graph import create_lisa_v2_graph
print('SUCCESS')
" 2>&1 | grep -q "SUCCESS"; then
    echo -e "${GREEN}✓${NC} Lisa 模块加载成功"
else
    echo -e "${RED}✗${NC} Lisa 模块加载失败！"
    echo "查看错误日志："
    docker exec intent-test-web python3 -c "
import sys
sys.path.insert(0, '/app')
from web_gui.services.langgraph_agents.lisa_v2.graph import create_lisa_v2_graph
" 2>&1 || true
    exit 1
fi
echo ""

# 完成
echo "========================================"
echo -e "${GREEN}✓ 部署完成！${NC}"
echo "========================================"
echo ""
echo "服务信息："
echo "  - Web UI: http://localhost:5001"
echo "  - 数据库: localhost:5432"
echo ""
echo "常用命令："
echo "  - 查看日志: docker logs intent-test-web -f"
echo "  - 重启服务: docker-compose restart web-app (通常不需要,代码会自动重载)"
echo "  - 停止服务: docker-compose down"
echo ""
echo "💡 代码热更新已启用："
echo "  - Python 代码改动后会自动重载"
echo "  - 前端静态文件改动立即生效"
echo "  - 只有修改依赖时才需要重新运行此脚本"
echo ""
