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
        COMPOSE_FILE="docker-compose.dev.yml"
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
        if [ -f "scripts/ci/build-proxy-package.js" ]; then
            if command -v node &> /dev/null; then
                node scripts/ci/build-proxy-package.js
                log_info "✅ 本地代理包构建完成"
            else
                log_warn "⚠️ Node.js未安装，跳过代理包构建"
            fi
        fi
    fi
else
    # 本地环境始终尝试构建
    if [ -f "scripts/ci/build-proxy-package.js" ]; then
        if command -v node &> /dev/null; then
            node scripts/ci/build-proxy-package.js
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

read_env_value() {
    key="$1"
    awk -F= -v expected="$key" '$1 == expected {print substr($0, index($0, "=") + 1)}' .env | tail -n 1
}

require_deploy_env() {
    key="$1"
    value="$(read_env_value "$key")"
    if [ -z "$value" ]; then
        log_error "缺少部署环境变量: $key"
        exit 1
    fi
}

validate_deploy_environment() {
    if [ ! -f .env ]; then
        log_error "缺少部署配置文件: .env"
        exit 1
    fi
    for key in DB_USER DB_PASSWORD SECRET_KEY INTENT_ACCESS_MODE INTENT_TESTER_ADMIN_PASSWORD_HASH \
        INTENT_PUBLIC_ORIGIN INTENT_EXECUTION_ENABLED \
        NEW_AGENTS_DEFAULT_LLM_API_KEY NEW_AGENTS_DEFAULT_LLM_BASE_URL \
        NEW_AGENTS_DEFAULT_LLM_MODEL NEW_AGENTS_CONFIG_ADMIN_API_KEY \
        PROXY_API_KEY; do
        require_deploy_env "$key"
    done

    NEW_AGENTS_CONFIG_ADMIN_API_KEY_VALUE="$(read_env_value NEW_AGENTS_CONFIG_ADMIN_API_KEY)"
    PROXY_API_KEY_VALUE="$(read_env_value PROXY_API_KEY)"
    NEW_AGENTS_DEFAULT_LLM_API_KEY_VALUE="$(read_env_value NEW_AGENTS_DEFAULT_LLM_API_KEY)"
    if [ "$NEW_AGENTS_CONFIG_ADMIN_API_KEY_VALUE" = "$PROXY_API_KEY_VALUE" ]; then
        log_error "NEW_AGENTS_CONFIG_ADMIN_API_KEY 与 PROXY_API_KEY 必须使用不同值"
        exit 1
    fi
    if [ "$NEW_AGENTS_CONFIG_ADMIN_API_KEY_VALUE" = "$NEW_AGENTS_DEFAULT_LLM_API_KEY_VALUE" ]; then
        log_error "NEW_AGENTS_CONFIG_ADMIN_API_KEY 与 NEW_AGENTS_DEFAULT_LLM_API_KEY 必须使用不同值"
        exit 1
    fi
    if [ "$PROXY_API_KEY_VALUE" = "$NEW_AGENTS_DEFAULT_LLM_API_KEY_VALUE" ]; then
        log_error "PROXY_API_KEY 与 NEW_AGENTS_DEFAULT_LLM_API_KEY 必须使用不同值"
        exit 1
    fi

    INTENT_ACCESS_MODE_VALUE="$(read_env_value INTENT_ACCESS_MODE)"
    case "$INTENT_ACCESS_MODE_VALUE" in
        restricted|public-readonly) ;;
        *)
            log_error "INTENT_ACCESS_MODE 必须是 restricted 或 public-readonly"
            exit 1
            ;;
    esac

    INTENT_EXECUTION_ENABLED_VALUE="$(read_env_value INTENT_EXECUTION_ENABLED)"
    case "$INTENT_EXECUTION_ENABLED_VALUE" in
        true)
            for key in INTENT_PROXY_TOKEN OPENAI_API_KEY OPENAI_BASE_URL MIDSCENE_MODEL_NAME; do
                require_deploy_env "$key"
            done
            COMPOSE_PROFILE_ARGS="--profile execution"
            ;;
        false)
            COMPOSE_PROFILE_ARGS=""
            ;;
        *)
            log_error "INTENT_EXECUTION_ENABLED 必须是 true 或 false"
            exit 1
            ;;
    esac
}

COMPOSE_PROFILE_ARGS=""
if [ "$BACKUP_ENABLED" = true ]; then
    validate_deploy_environment
fi

# 备份（仅生产环境）
if [ "$BACKUP_ENABLED" = true ]; then
    log_info "创建备份..."
    BACKUP_DIR="/opt/intent-test-framework-backup/latest"
    # 使用 sudo 创建备份目录
    if ! sudo mkdir -p "$BACKUP_DIR"; then
        log_warn "无法创建备份目录 $BACKUP_DIR (权限不足)，尝试使用用户目录..."
        BACKUP_DIR="$HOME/backups/intent-test-framework/latest"
        mkdir -p "$BACKUP_DIR"
    else
        # 确保当前用户有权访问，或者后续操作都用sudo
        sudo chown $USER:$USER "$BACKUP_DIR"
    fi
    
    log_info "备份至: $BACKUP_DIR"
    
    # 使用 rsync 备份 (如果目录属于当前用户，不需要sudo；如果是系统目录，可能需要)
    # 为安全起见，如果有sudo权限，可以用sudo rsync确保读取所有文件
    sudo rsync -a --exclude='node_modules' --exclude='.git' --exclude='__pycache__' \
          --exclude='logs' --exclude='*.pyc' \
          "$DEPLOY_DIR/" "$BACKUP_DIR/" || log_warn "备份过程中出现非致命错误"
          
    log_info "✅ 备份完成"
fi

# 停止现有服务
log_info "停止现有服务..."
$DOCKER_CMD $COMPOSE_PROFILE_ARGS -f "$COMPOSE_FILE" down || true  # 移除 -v 以保留数据卷
sleep 3

# 强制清理残留容器和网络（本地和生产环境都需要）
log_info "清理残留资源..."
if [ "$BACKUP_ENABLED" = true ]; then
    sudo docker ps -a | grep -E "(intent-test|ai4se)" | awk '{print $1}' | xargs sudo docker rm -f 2>/dev/null || true
    sudo docker network ls | grep -E "(intent-test|ai4se)" | awk '{print $1}' | xargs sudo docker network rm 2>/dev/null || true
else
    docker ps -a | grep -E "(intent-test|ai4se)" | awk '{print $1}' | xargs docker rm -f 2>/dev/null || true
    docker network ls | grep -E "(intent-test|ai4se)" | awk '{print $1}' | xargs docker network rm 2>/dev/null || true
fi

log_info "✅ 服务已停止"

# 构建镜像
log_info "构建 Docker 镜像..."
if [ "$BACKUP_ENABLED" = true ]; then
    # 生产环境强制无缓存构建，确保包含最新代码
    $DOCKER_CMD $COMPOSE_PROFILE_ARGS -f "$COMPOSE_FILE" build --no-cache
else
    $DOCKER_CMD $COMPOSE_PROFILE_ARGS -f "$COMPOSE_FILE" build
fi

log_info "✅ 镜像构建完成"

# 启动服务
log_info "启动服务..."
$DOCKER_CMD $COMPOSE_PROFILE_ARGS -f "$COMPOSE_FILE" up -d

log_info "✅ 服务已启动"

# 复制assistant-bundles到容器 (已移除: Dockerfile COPY 指令已处理，且避免覆盖/权限问题)


# 等待服务启动
log_info "等待服务启动..."
sleep 10

if [ "$BACKUP_ENABLED" = true ]; then
    log_info "同步 New Agents 默认 LLM 配置..."
    $DOCKER_CMD $COMPOSE_PROFILE_ARGS -f "$COMPOSE_FILE" exec -T new-agents-backend \
        python -c "from app import app, init_db; init_db(app)"
    log_info "✅ New Agents 默认 LLM 配置已同步"
fi

# 健康检查
log_info "执行部署后健康检查..."

# 首先进行快速基础检查
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s --max-time 5 http://localhost/intent-tester/health > /dev/null 2>&1; then
        log_info "✅ 基础服务响应正常"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        log_warn "等待服务响应，重试 $RETRY_COUNT/$MAX_RETRIES..."
        sleep 3
    else
        log_error "基础服务无响应"
        
        # 生产环境失败时回滚
        if [ "$BACKUP_ENABLED" = true ] && [ -d "$BACKUP_DIR" ]; then
            log_error "开始回滚..."
            rsync -a --delete "$BACKUP_DIR/" "$DEPLOY_DIR/"
            $DOCKER_CMD $COMPOSE_PROFILE_ARGS -f "$COMPOSE_FILE" up -d
            log_info "已回滚到上一版本"
        fi
        
        exit 1
    fi
done

# 执行完整健康检查脚本
if [ -f "scripts/health/health_check.sh" ]; then
    chmod +x scripts/health/health_check.sh
    log_info "执行完整健康检查..."
    
    if bash scripts/health/health_check.sh "$ENVIRONMENT"; then
        log_info "✅ 完整健康检查通过"
    else
        log_error "完整健康检查失败"
        
        # 生产环境失败时回滚
        if [ "$BACKUP_ENABLED" = true ] && [ -d "$BACKUP_DIR" ]; then
            log_error "开始回滚..."
            rsync -a --delete "$BACKUP_DIR/" "$DEPLOY_DIR/"
            $DOCKER_CMD $COMPOSE_PROFILE_ARGS -f "$COMPOSE_FILE" up -d
            log_info "已回滚到上一版本"
        fi
        
        exit 1
    fi
else
    log_warn "健康检查脚本不存在，跳过完整检查"
fi

# 显示服务状态
log_info "=========================================="
log_info "服务状态:"
log_info "=========================================="
$DOCKER_CMD $COMPOSE_PROFILE_ARGS -f "$COMPOSE_FILE" ps

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
log_info "访问地址: http://localhost"
log_info "=========================================="
