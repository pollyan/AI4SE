#!/bin/bash

# ========================================
# 本地测试脚本 (Local Test Runner)
# 模拟 GitHub Actions 的测试流程
# ========================================
# 用法:
#   ./scripts/test/test-local.sh          # 运行所有测试 (不含 smoke)
#   ./scripts/test/test-local.sh api      # 仅运行 API 测试 (不含 smoke)
#   ./scripts/test/test-local.sh proxy    # 仅运行代理测试
#   ./scripts/test/test-local.sh lint     # 仅运行代码检查
#   ./scripts/test/test-local.sh smoke    # 仅运行耗时的大模型冒烟测试
# ========================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# 切换到项目根目录
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)

# 解析参数
TEST_TYPE=${1:-all}
FAILED=0

# ==========================================
# API 测试 (Python)
# ==========================================
run_api_tests() {
    log_section "🐍 API Integration Tests"
    
    # 检查 Python 环境
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        return 1
    fi
    
    log_info "Python 版本: $(python3 --version)"
    
    # 安装依赖
    log_info "安装 Python 依赖..."
    pip3 install -q -r requirements.txt pytest pytest-cov 2>/dev/null || pip install -q -r requirements.txt pytest pytest-cov
    
    # 设置 PYTHONPATH
    export PYTHONPATH=$PROJECT_ROOT:$PROJECT_ROOT/tools/intent-tester:$PYTHONPATH
    
    # 运行测试
    log_info "运行 API 测试..."
    # 运行 Intent Tester 测试
    log_info "运行 Intent Tester API 测试..."
    if python3 -m pytest tools/intent-tester/tests/ -v --cov=tools/intent-tester/backend --cov-report=term; then
        log_info "✅ Intent Tester 测试通过"
    else
        log_error "❌ Intent Tester 测试失败"
        return 1
    fi
}

# ==========================================
# 代码质量检查 (Flake8)
# ==========================================
run_lint() {
    log_section "📊 Code Quality Check"
    
    # 安装 flake8
    log_info "安装 flake8..."
    pip3 install -q flake8 2>/dev/null || pip install -q flake8
    
    log_info "运行代码质量检查..."
    
    # 检查严重错误 (和 GitHub Actions 一致)
    LINT_RESULT=0
    
    if python3 -m flake8 tools/intent-tester/backend --count --select=E9,F63,F7,F82 --show-source --statistics; then
        log_info "✅ 代码质量检查通过 (无严重错误)"
    else
        log_warn "⚠️ 代码质量检查发现问题"
        LINT_RESULT=1
    fi
    
    return $LINT_RESULT
}

# ==========================================
# MidScene 代理测试 (Node.js)
# ==========================================
run_proxy_tests() {
    log_section "🟢 MidScene Proxy Tests"
    
    # 检查 Node.js 环境
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装"
        return 1
    fi
    
    log_info "Node.js 版本: $(node --version)"
    
    # 切换到 intent-tester 目录
    cd "$PROJECT_ROOT/tools/intent-tester"
    
    # 检查 package.json 存在
    if [ ! -f "package.json" ]; then
        log_error "package.json 未找到"
        cd "$PROJECT_ROOT"
        return 1
    fi
    
    # 安装依赖
    log_info "安装 Node.js 依赖..."
    npm ci --silent 2>/dev/null || npm install --silent
    
    # 运行测试
    log_info "运行代理测试..."
    if npx jest --testPathPatterns="tests/proxy" --passWithNoTests --forceExit; then
        log_info "✅ 代理测试通过"
    else
        log_error "❌ 代理测试失败"
        cd "$PROJECT_ROOT"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
    cd "$PROJECT_ROOT"
}

# ==========================================
# New Agents Frontend Tests (Vitest)
# ==========================================
run_new_agents_frontend_tests() {
    log_section "🤖 New Agents Frontend Tests"
    cd "$PROJECT_ROOT/tools/new-agents"
    
    log_info "安装 New Agents 依赖..."
    npm ci --silent 2>/dev/null || npm install --silent

    log_info "运行 New Agents Frontend 测试..."
    if npm run test; then
        log_info "✅ New Agents Frontend 测试通过"
    else
        log_error "❌ New Agents Frontend 测试失败"
        cd "$PROJECT_ROOT"
        return 1
    fi
    cd "$PROJECT_ROOT"
}

# ==========================================
# New Agents Backend Tests (Python)
# ==========================================
run_new_agents_backend_tests() {
    log_section "🐍 New Agents Backend Tests"
    cd "$PROJECT_ROOT/tools/new-agents/backend"
    
    # 尝试激活虚拟环境 (如果有)
    [ -f "venv/bin/activate" ] && source venv/bin/activate
    
    log_info "安装 Backend 依赖..."
    pip3 install -q -r requirements.txt pytest 2>/dev/null || pip install -q -r requirements.txt pytest

    log_info "运行 New Agents Backend 测试..."
    if python3 -m pytest tests/test_api.py -v; then
        log_info "✅ New Agents Backend 测试通过"
    else
        log_error "❌ New Agents Backend 测试失败"
        cd "$PROJECT_ROOT"
        return 1
    fi
    cd "$PROJECT_ROOT"
}

# ==========================================
# Common Frontend 测试 (React - Homepage/Profile)
# ==========================================
run_common_frontend_tests() {
    log_section "⚛️ Common Frontend Tests (Homepage/Profile)"

    # 检查 Node.js 环境
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装"
        return 1
    fi

    # 切换到 common frontend 目录
    cd "$PROJECT_ROOT/tools/frontend"

    # 安装依赖 (如果需要)
    log_info "检查依赖..."
    if [ ! -d "node_modules" ]; then
        log_info "安装 Common Frontend 依赖..."
        npm ci --silent 2>/dev/null || npm install --silent
    fi

    # 运行 Lint
    log_info "运行 Common Frontend Lint..."
    if npm run lint; then
        log_info "✅ Common Frontend Lint 通过"
    else
        log_error "❌ Common Frontend Lint 失败"
        cd "$PROJECT_ROOT"
        return 1
    fi

    # 运行 Build (作为测试)
    log_info "运行 Common Frontend Build (作为验证)..."
    if npm run build; then
        log_info "✅ Common Frontend Build 通过"
    else
        log_error "❌ Common Frontend Build 失败"
        cd "$PROJECT_ROOT"
        return 1
    fi

    cd "$PROJECT_ROOT"
}

# ==========================================
# 主流程
# ==========================================
log_section "🚀 本地测试开始"
log_info "项目根目录: $PROJECT_ROOT"
log_info "测试类型: $TEST_TYPE"

case "$TEST_TYPE" in
    api)
        run_api_tests || FAILED=1
        ;;
    proxy)
        run_proxy_tests || FAILED=1
        ;;
    lint)
        run_lint || FAILED=1
        ;;
    smoke)
        run_smoke_tests || FAILED=1
        ;;
    all)
        run_api_tests || FAILED=1
        run_lint || true  # lint 失败不中断
        run_proxy_tests || FAILED=1
        run_common_frontend_tests || FAILED=1
        run_new_agents_frontend_tests || FAILED=1
        run_new_agents_backend_tests || FAILED=1
        ;;
    *)
        log_error "未知测试类型: $TEST_TYPE"
        echo "用法: $0 [all|api|proxy|lint|smoke]"
        exit 1
        ;;
esac

# ==========================================
# 结果汇总
# ==========================================
log_section "📊 测试结果汇总"

if [ $FAILED -eq 0 ]; then
    log_info "🎉 所有测试通过！可以安全推送到 GitHub。"
    exit 0
else
    log_error "❌ 部分测试失败，请修复后再推送。"
    exit 1
fi
