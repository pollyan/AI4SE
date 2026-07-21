#!/bin/bash

# ========================================
# 部署后健康检查脚本
# ========================================
# 用法:
#   ./scripts/health/health_check.sh [local|production]
#
# 检查项目:
#   1. Docker 容器状态
#   2. 数据库连通性
#   3. 页面 HTTP 访问
#   4. 核心 API 端点
# ========================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# 配置
ENVIRONMENT=${1:-local}
MAX_RETRIES=5
RETRY_DELAY=3
FAILED_CHECKS=0

case "$ENVIRONMENT" in
    local|dev|development)
        BASE_URL="http://localhost"
        COMPOSE_FILE="docker-compose.dev.yml"
        DB_CONTAINER="ai4se-db"
        CONTAINERS=("ai4se-db" "ai4se-intent-tester" "ai4se-gateway" "ai4se-new-agents-backend")
        ;;
    prod|production|remote)
        echo "Production release verification requires scripts/ci/release_transaction.py." >&2
        exit 2
        ;;
    *)
        log_error "未知环境: $ENVIRONMENT"
        echo "用法: $0 [local|production]"
        exit 1
        ;;
esac

echo ""
echo "🏥 部署后健康检查"
echo "   环境: $ENVIRONMENT"
echo "   基础 URL: $BASE_URL"
echo ""

# ========================================
# 1. 检查 Docker 容器状态
# ========================================
check_containers() {
    log_section "1. Docker 容器状态检查"
    
    local all_running=true
    
    for container in "${CONTAINERS[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            local status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null)
            if [ "$status" = "running" ]; then
                log_info "$container: 运行中"
            else
                log_error "$container: 状态异常 ($status)"
                all_running=false
            fi
        else
            log_error "$container: 未运行"
            all_running=false
        fi
    done
    
    if [ "$all_running" = false ]; then
        log_error "部分容器未正常运行"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
    
    log_info "所有容器正常运行"
    return 0
}

# ========================================
# 2. 检查数据库连通性
# ========================================
check_database() {
    log_section "2. 数据库连通性检查"
    
    local retry=0
    while [ $retry -lt $MAX_RETRIES ]; do
        # 经唯一网关确认 Intent 服务，再在数据库容器内确认 PostgreSQL readiness。
        local response=$(curl -s --max-time 10 "${BASE_URL}/intent-tester/health" 2>/dev/null || echo "")
        
        if echo "$response" | grep -q '"status".*"ok"'; then
            log_info "Intent Tester 服务健康"
            
            local db_check=$(docker exec "$DB_CONTAINER" sh -c 'pg_isready -U "$POSTGRES_USER"' 2>/dev/null || echo "failed")
            
            if echo "$db_check" | grep -q "accepting connections"; then
                log_info "PostgreSQL 数据库: 接受连接"
                return 0
            else
                log_warn "数据库连接检查中..."
            fi
        fi
        
        retry=$((retry + 1))
        if [ $retry -lt $MAX_RETRIES ]; then
            log_warn "数据库检查重试 $retry/$MAX_RETRIES..."
            sleep $RETRY_DELAY
        fi
    done
    
    log_error "数据库连通性检查失败"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    return 1
}

# ========================================
# 3. 检查页面 HTTP 访问
# ========================================
check_pages() {
    log_section "3. 页面 HTTP 访问检查"
    
    # 页面列表: 路径 ^ 描述 ^ 声明允许的匿名状态
    local pages=(
        "/^首页 (Common Frontend)^200|304"
        "/profile^个人资料页^200|304"
        "/intent-tester/^意图测试首页^200|302"
        "/intent-tester/testcases^测试用例列表^200|302"
        "/intent-tester/execution^执行控制台^200|302|403"
        "/intent-tester/local-proxy^本地代理页^200|302"
    )
    
    local all_ok=true
    
    for page_info in "${pages[@]}"; do
        IFS='^' read -r path desc allowed <<< "$page_info"
        
        local retry=0
        local success=false
        
        while [ $retry -lt 3 ]; do
            local status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${BASE_URL}${path}" 2>/dev/null || echo "000")
            
            if [[ "|$allowed|" == *"|$status_code|"* ]]; then
                log_info "$desc: HTTP $status_code"
                success=true
                break
            elif [ "$status_code" = "000" ]; then
                retry=$((retry + 1))
                if [ $retry -lt 3 ]; then
                    sleep 2
                fi
            else
                log_error "$desc: HTTP $status_code"
                all_ok=false
                break
            fi
        done
        
        if [ "$success" = false ] && [ "$status_code" = "000" ]; then
            log_error "$desc: 连接失败"
            all_ok=false
        fi
    done
    
    if [ "$all_ok" = false ]; then
        log_error "部分页面访问失败"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
    
    log_info "所有页面访问正常"
    return 0
}

# ========================================
# 4. 检查核心 API 端点
# ========================================
check_apis() {
    log_section "4. 核心 API 端点检查"
    
    # API 列表: 路径 ^ 方法 ^ 描述 ^ 声明允许的匿名状态
    local apis=(
        "/health^GET^Nginx 网关健康检查^200"
        "/intent-tester/health^GET^Intent Tester 健康检查^200"
        "/intent-tester/api/testcases^GET^测试用例 API^200|401"
        "/new-agents/api/health^GET^New Agents Backend 健康检查^200"
    )
    
    local all_ok=true
    
    for api_info in "${apis[@]}"; do
        IFS='^' read -r path method desc allowed <<< "$api_info"
        
        local retry=0
        local success=false
        
        while [ $retry -lt 3 ]; do
            local status_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" --max-time 10 "${BASE_URL}${path}" 2>/dev/null || echo "000")
            
            if [[ "|$allowed|" == *"|$status_code|"* ]]; then
                log_info "$desc: HTTP $status_code"
                success=true
                break
            elif [ "$status_code" = "000" ]; then
                retry=$((retry + 1))
                if [ $retry -lt 3 ]; then
                    sleep 2
                fi
            else
                log_error "$desc: HTTP $status_code"
                all_ok=false
                break
            fi
        done
        
        if [ "$success" = false ] && [ "$status_code" = "000" ]; then
            log_error "$desc: 连接失败"
            all_ok=false
        fi
    done
    
    if [ "$all_ok" = false ]; then
        log_error "部分 API 端点检查失败"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
    
    log_info "所有 API 端点正常"
    return 0
}

# ========================================
# 主流程
# ========================================
main() {
    # 等待服务完全启动
    log_info "等待服务启动 (10秒)..."
    sleep 10
    
    # 执行所有检查
    check_containers || true
    check_database || true
    check_pages || true
    check_apis || true
    
    # 汇总结果
    log_section "健康检查结果汇总"
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ 所有健康检查通过！${NC}"
        echo ""
        exit 0
    else
        echo ""
        echo -e "${RED}❌ 有 $FAILED_CHECKS 项检查失败${NC}"
        echo ""
        exit 1
    fi
}

# 运行主流程
main
