#!/bin/bash

# =================================================================
# 服务器端部署脚本
# 用于 GitHub Actions SCP/SSH 推送模式部署
# =================================================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
DEPLOY_DIR="/opt/intent-test-framework"
UPLOAD_DIR="/opt/intent-test-framework-upload"
BACKUP_DIR="/opt/intent-test-framework-backup"
HEALTH_URL="http://localhost:5001/health"
MAX_HEALTH_RETRIES=10
HEALTH_RETRY_DELAY=3

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 健康检查函数
health_check() {
    local retries=0
    log_info "开始健康检查..."
    
    while [ $retries -lt $MAX_HEALTH_RETRIES ]; do
        if curl -f -s --max-time 5 "$HEALTH_URL" > /dev/null 2>&1; then
            log_info "✅ 健康检查通过"
            return 0
        fi
        
        retries=$((retries + 1))
        if [ $retries -lt $MAX_HEALTH_RETRIES ]; then
            log_warn "健康检查失败，等待 ${HEALTH_RETRY_DELAY} 秒后重试 ($retries/$MAX_HEALTH_RETRIES)..."
            sleep $HEALTH_RETRY_DELAY
        fi
    done
    
    log_error "健康检查失败，已达最大重试次数"
    return 1
}

# 回滚函数
rollback() {
    log_error "部署失败，开始回滚到上一版本..."
    
    if [ -d "$BACKUP_DIR/latest" ]; then
        log_info "恢复备份文件..."
        rsync -a --delete "$BACKUP_DIR/latest/" "$DEPLOY_DIR/"
        
        log_info "重启服务..."
        cd "$DEPLOY_DIR"
        docker-compose -f docker-compose.prod.yml up -d
        
        sleep 10
        
        if health_check; then
            log_info "✅ 回滚成功"
            exit 1
        else
            log_error "❌ 回滚后健康检查仍然失败，请手动检查"
            exit 1
        fi
    else
        log_error "没有找到备份，无法回滚"
        exit 1
    fi
}

# 主要部署流程
main() {
    log_info "=========================================="
    log_info "开始部署流程"
    log_info "=========================================="
    
    # 1. 检查上传目录
    if [ ! -d "$UPLOAD_DIR" ]; then
        log_error "上传目录不存在: $UPLOAD_DIR"
        exit 1
    fi
    
    log_info "上传目录检查通过"
    
    # 2. 创建备份目录
    log_info "创建备份目录..."
    mkdir -p "$BACKUP_DIR"
    
    # 3. 备份当前版本
    if [ -d "$DEPLOY_DIR" ]; then
        log_info "备份当前版本..."
        rm -rf "$BACKUP_DIR/latest"
        mkdir -p "$BACKUP_DIR/latest"
        rsync -a --exclude='node_modules' --exclude='.git' --exclude='__pycache__' \
              --exclude='logs' --exclude='*.pyc' \
              "$DEPLOY_DIR/" "$BACKUP_DIR/latest/"
        log_info "✅ 备份完成"
    else
        log_warn "部署目录不存在，这是首次部署"
        mkdir -p "$DEPLOY_DIR"
    fi
    
    # 4. 停止当前服务
    if [ -f "$DEPLOY_DIR/docker-compose.prod.yml" ]; then
        log_info "停止当前服务..."
        cd "$DEPLOY_DIR"
        docker-compose -f docker-compose.prod.yml down || true
        log_info "✅ 服务已停止"
    fi
    
    # 5. 复制新代码
    log_info "应用新代码..."
    rsync -a --delete --exclude='node_modules' --exclude='.git' --exclude='__pycache__' \
          --exclude='*.pyc' \
          "$UPLOAD_DIR/" "$DEPLOY_DIR/"
    log_info "✅ 代码更新完成"
    
    # 6. 检查 .env 文件
    if [ ! -f "$DEPLOY_DIR/.env" ]; then
        log_warn ".env 文件不存在，尝试从备份恢复..."
        if [ -f "$BACKUP_DIR/latest/.env" ]; then
            cp "$BACKUP_DIR/latest/.env" "$DEPLOY_DIR/.env"
            log_info "✅ 从备份恢复 .env 文件"
        else
            log_error "未找到 .env 文件，请手动创建"
            echo "你可以参考 .env.docker.example 创建 .env 文件"
            exit 1
        fi
    fi
    
    # 7. 重新构建 Docker 镜像
    log_info "构建 Docker 镜像..."
    cd "$DEPLOY_DIR"
    docker-compose -f docker-compose.prod.yml build --no-cache web-app
    log_info "✅ 镜像构建完成"
    
    # 8. 启动服务
    log_info "启动服务..."
    docker-compose -f docker-compose.prod.yml up -d
    log_info "✅ 服务已启动"
    
    # 9. 等待服务启动
    log_info "等待服务启动 (10秒)..."
    sleep 10
    
    # 10. 健康检查
    if ! health_check; then
        log_error "健康检查失败"
        rollback
    fi
    
    # 11. 清理旧镜像
    log_info "清理未使用的 Docker 镜像..."
    docker image prune -f || true
    log_info "✅ 清理完成"
    
    # 12. 显示服务状态
    log_info "=========================================="
    log_info "服务状态:"
    log_info "=========================================="
    docker-compose -f docker-compose.prod.yml ps
    
    # 13. 清理上传目录
    log_info "清理上传目录..."
    rm -rf "$UPLOAD_DIR"
    
    log_info "=========================================="
    log_info "🎉 部署成功！"
    log_info "=========================================="
}

# 错误处理
trap 'log_error "部署过程中发生错误"; rollback' ERR

# 执行主流程
main
