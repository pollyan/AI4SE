#!/bin/bash

# 腾讯云服务器自动部署脚本
# 用途：在服务器上初始化项目或手动触发部署

set -e  # 遇到错误立即退出

PROJECT_DIR="/opt/intent-test-framework"
COMPOSE_FILE="docker-compose.prod.yml"

echo "=========================================="
echo "🚀 Intent Test Framework - 服务器部署"
echo "=========================================="

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  建议使用 root 用户执行此脚本"
    echo "   或者使用: sudo ./deploy-server.sh"
fi

# 1. 检查 Docker 是否安装
echo ""
echo "1️⃣  检查 Docker 环境..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    echo "请先安装 Docker: curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

echo "✅ Docker 已安装: $(docker --version)"
echo "✅ Docker Compose 已安装: $(docker-compose --version)"

# 2. 创建项目目录并克隆代码（首次部署）
echo ""
echo "2️⃣  准备项目代码..."
if [ ! -d "$PROJECT_DIR" ]; then
    echo "📥 首次部署，克隆代码仓库..."
    read -p "请输入 Git 仓库地址: " REPO_URL
    git clone "$REPO_URL" "$PROJECT_DIR"
else
    echo "📂 项目目录已存在，拉取最新代码..."
    cd "$PROJECT_DIR"
    git pull || {
        echo "⚠️  Git pull 失败，可能有本地修改"
        read -p "是否强制覆盖？(y/N): " force
        if [ "$force" = "y" ] || [ "$force" = "Y" ]; then
            git fetch --all
            git reset --hard origin/main || git reset --hard origin/master
        fi
    }
fi

cd "$PROJECT_DIR"

# 3. 配置环境变量
echo ""
echo "3️⃣  配置环境变量..."
if [ ! -f ".env" ]; then
    echo "📝 创建 .env 文件..."
    cat > .env << 'EOF'
# ===========================================
# 数据库配置 - 使用 Supabase
# ===========================================
DATABASE_URL=postgresql://postgres.jzmqsuxphksbulrbhebp:Shunlian04@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require&connect_timeout=15&application_name=prod

# ===========================================
# Flask 应用配置
# ===========================================
SECRET_KEY=CHANGE_THIS_TO_RANDOM_STRING
FLASK_ENV=production

# ===========================================
# 服务端口
# ===========================================
WEB_PORT=5001
EOF

    echo "⚠️  请编辑 .env 文件并修改 SECRET_KEY"
    echo "   生成密钥: openssl rand -hex 32"
    read -p "按回车继续..."
else
    echo "✅ .env 文件已存在"
fi

# 4. 创建 Nginx 配置目录
echo ""
echo "4️⃣  配置 Nginx..."
mkdir -p nginx/ssl

if [ ! -f "nginx/nginx.conf" ]; then
    echo "📝 创建 Nginx 配置文件..."
    # Nginx 配置将在下一步创建
    echo "⚠️  请确保 nginx/nginx.conf 已创建"
fi

# 5. 修改 docker-compose.prod.yml (移除 postgres 服务)
echo ""
echo "5️⃣  配置 Docker Compose..."
if grep -q "^  postgres:" "$COMPOSE_FILE"; then
    echo "📝 注释掉 postgres 服务（使用 Supabase）..."
    # 创建备份
    cp "$COMPOSE_FILE" "${COMPOSE_FILE}.backup"
    # 这里需要手动编辑，脚本暂时跳过
    echo "⚠️  请手动编辑 $COMPOSE_FILE，注释掉 postgres 服务"
fi

# 6. 构建并启动服务
echo ""
echo "6️⃣  构建 Docker 镜像..."
docker-compose -f "$COMPOSE_FILE" build

echo ""
echo "7️⃣  启动服务..."
docker-compose -f "$COMPOSE_FILE" up -d

# 7. 等待服务启动
echo ""
echo "8️⃣  等待服务启动..."
sleep 10

# 8. 健康检查
echo ""
echo "9️⃣  健康检查..."
if curl -f http://localhost:5001/health > /dev/null 2>&1; then
    echo "✅ Web 应用健康检查通过"
else
    echo "❌ Web 应用健康检查失败"
    echo "查看日志: docker-compose -f $COMPOSE_FILE logs web-app"
fi

# 9. 显示服务状态
echo ""
echo "🔟 服务状态:"
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "📍 Web 界面: http://$(curl -s https://ifconfig.me):5001"
echo "📍 健康检查: http://localhost:5001/health"
echo ""
echo "常用命令:"
echo "  查看日志: docker-compose -f $COMPOSE_FILE logs -f"
echo "  重启服务: docker-compose -f $COMPOSE_FILE restart"
echo "  停止服务: docker-compose -f $COMPOSE_FILE down"
echo ""
