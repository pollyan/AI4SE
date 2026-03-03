#!/bin/bash

# ========================================
# 架构边界检查脚本 (Architecture Check)
# ========================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILED=0

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cd "$(dirname "$0")/../.."

# 1. 检查跨模块导入 (new-agents ↛ intent-tester 和 intent-tester ↛ new-agents)
log_info "检查模块边界: new-agents 不应导入 intent-tester..."
if grep -rnw "tools/new-agents/frontend" -e "intent-tester" -e "intent_tester"; then
    log_error "发现 tools/new-agents 存在对 intent-tester 的违规引用！"
    FAILED=1
else
    log_info "✅ new-agents -> intent-tester 边界正常"
fi

log_info "检查模块边界: intent-tester 不应导入 new-agents..."
if grep -rnw "tools/intent-tester" -e "new-agents" -e "new_agents"; then
    log_error "发现 tools/intent-tester 存在对 new-agents 的违规引用！"
    FAILED=1
else
    log_info "✅ intent-tester -> new-agents 边界正常"
fi

# 2. 检查单文件大小限制 (500 行，前端生成类等除外)
log_info "检查文件大小限制 (单文件 <= 500 行)..."
# 找出所有超过 500 行的源文件（排除 node_modules, venv, test_output 等）
LARGE_FILES=$(find tools/ -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) \
    -not -path "*/node_modules/*" \
    -not -path "*/venv/*" \
    -not -path "*/\.venv/*" \
    -not -path "*/dist/*" \
    -exec wc -l {} + | awk '$1 > 500 && $2 != "total" {print $2 " (" $1 " lines)"}')

if [ -n "$LARGE_FILES" ]; then
    log_warn "⚠️ 发现超过 500 行的文件 (需逐步重构，暂不报错):"
    echo "$LARGE_FILES"
else
    log_info "✅ 所有源文件大小均符合规范 (<= 500 行)"
fi

if [ $FAILED -ne 0 ]; then
    log_error "❌ 架构检查失败！"
    exit 1
else
    log_info "🎉 架构检查全部通过！"
    exit 0
fi
