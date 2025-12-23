#!/bin/bash

# ========================================
# 通用部署脚本 - 支持本地和远程环境
# ========================================
# 用法:
#   本地: ./scripts/deploy.sh local
#   远程: ./scripts/deploy.sh production
# ========================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 解析参数
ENVIRONMENT=${1:-local}
COMPOSE_FILE=""
BACKUP_ENABLED=false
DOCKER_CMD="docker-compose"  # 默认不使用 sudo

case "$ENVIRONMENT" in
    local|dev|development)
        COMPOSE_FILE="docker-compose.yml"
        DEPLOY_DIR="."
        BACKUP_ENABLED=false
        DOCKER_CMD="docker-compose"
        log_info "部署环境: 本地开发"
        ;;
    prod|production|remote)
        COMPOSE_FILE="docker-compose.prod.yml"
        DEPLOY_DIR="/opt/intent-test-framework"
        BACKUP_ENABLED=true
        DOCKER_CMD="sudo docker-compose"  # 生产环境使用 sudo
        log_info "部署环境: 生产环境"
        ;;
    *)
        log_error "未知环境: $ENVIRONMENT"
        echo "用法: $0 [local|production]"
        exit 1
        ;;
esac

log_info "使用配置文件: $COMPOSE_FILE"
log_info "部署目录: $DEPLOY_DIR"

# 构建本地代理包（必须在Docker构建前完成）
log_info "构建本地代理包..."
# 生产环境如果已经有dist artifact，则跳过构建
if [ "$ENVIRONMENT" = "production" ] || [ "$ENVIRONMENT" = "prod" ] || [ "$ENVIRONMENT" = "remote" ]; then
    if [ -f "dist/intent-test-proxy.zip" ]; then
        log_info "✅ 检测到现有的代理包 artifact，跳过重新构建"
    else
        # 只有在缺失时才构建
        if [ -f "scripts/deployment/build-proxy-package.js" ]; then
            if command -v node &> /dev/null; then
                node scripts/deployment/build-proxy-package.js
                log_info "✅ 本地代理包构建完成"
            else
                log_warn "⚠️ Node.js未安装，跳过代理包构建"
            fi
        fi
    fi
else
    # 本地环境始终尝试构建
    if [ -f "scripts/deployment/build-proxy-package.js" ]; then
        if command -v node &> /dev/null; then
            node scripts/deployment/build-proxy-package.js
            log_info "✅ 本地代理包构建完成"
        fi
    elif [ -f "scripts/build-proxy-package.js" ]; then
         if command -v node &> /dev/null; then
            node scripts/build-proxy-package.js
            log_info "✅ 本地代理包构建完成 (旧脚本)"
        fi
    fi
fi

# 切换到部署目录
cd "$DEPLOY_DIR"

# 备份（仅生产环境）
if [ "$BACKUP_ENABLED" = true ]; then
    log_info "创建备份..."
    BACKUP_DIR="/opt/intent-test-framework-backup/latest"
    mkdir -p "$BACKUP_DIR"
    rsync -a --exclude='node_modules' --exclude='.git' --exclude='__pycache__' \
          --exclude='logs' --exclude='*.pyc' \
          "$DEPLOY_DIR/" "$BACKUP_DIR/" || true
    log_info "✅ 备份完成"
fi

# 停止现有服务
log_info "停止现有服务..."
$DOCKER_CMD -f "$COMPOSE_FILE" down || true  # 移除 -v 以保留数据卷
sleep 3

# 强制清理残留容器和网络（本地和生产环境都需要）
log_info "清理残留资源..."
if [ "$BACKUP_ENABLED" = true ]; then
    sudo docker ps -a | grep intent-test | awk '{print $1}' | xargs sudo docker rm -f 2>/dev/null || true
    sudo docker network ls | grep intent-test | awk '{print $1}' | xargs sudo docker network rm 2>/dev/null || true
else
    docker ps -a | grep intent-test | awk '{print $1}' | xargs docker rm -f 2>/dev/null || true
    docker network ls | grep intent-test | awk '{print $1}' | xargs docker network rm 2>/dev/null || true
fi

log_info "✅ 服务已停止"

# 构建镜像
log_info "构建 Docker 镜像..."
if [ "$BACKUP_ENABLED" = true ]; then
    # 生产环境强制无缓存构建，确保包含最新代码
    $DOCKER_CMD -f "$COMPOSE_FILE" build --no-cache
else
    $DOCKER_CMD -f "$COMPOSE_FILE" build
fi

log_info "✅ 镜像构建完成"

# 启动服务
log_info "启动服务..."
$DOCKER_CMD -f "$COMPOSE_FILE" up -d

log_info "✅ 服务已启动"

# 复制assistant-bundles到容器 (已移除: Dockerfile COPY 指令已处理，且避免覆盖/权限问题)


# 等待服务启动
log_info "等待服务启动..."
sleep 10

# 健康检查
log_info "健康检查..."
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s --max-time 5 http://localhost:5001/health > /dev/null 2>&1; then
        log_info "✅ 健康检查通过"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        log_warn "健康检查失败，重试 $RETRY_COUNT/$MAX_RETRIES..."
        sleep 3
    else
        log_error "健康检查失败"
        
        # 生产环境失败时回滚
        if [ "$BACKUP_ENABLED" = true ] && [ -d "$BACKUP_DIR" ]; then
            log_error "开始回滚..."
            rsync -a --delete "$BACKUP_DIR/" "$DEPLOY_DIR/"
            $DOCKER_CMD -f "$COMPOSE_FILE" up -d
            log_info "已回滚到上一版本"
        fi
        
        exit 1
    fi
done

# 显示服务状态
log_info "=========================================="
log_info "服务状态:"
log_info "=========================================="
$DOCKER_CMD -f "$COMPOSE_FILE" ps

# 清理旧镜像
log_info "清理未使用的镜像..."
if [ "$BACKUP_ENABLED" = true ]; then
    sudo docker image prune -f || true
else
    docker image prune -f || true
fi

log_info "=========================================="
log_info "🎉 部署成功！"
log_info "=========================================="
log_info "环境: $ENVIRONMENT"
log_info "访问地址: http://localhost:5001"
log_info "=========================================="
