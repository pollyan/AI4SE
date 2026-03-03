#!/bin/bash

# ========================================
# 文档路径有效性检查 (Docs Check)
# ========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILED=0

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cd "$(dirname "$0")/../.."

check_markdown_links() {
    local file=$1
    if [ ! -f "$file" ]; then
        return
    fi
    log_info "检查文档: $file"
    
    # 提取 [text](path) 格式的相对路径 (排除了以 http 或 file:/// 开头的外链和绝对路径)
    links=$(grep -oP '\[.*?\]\((?!http|file:///)(.*?)\)' "$file" | grep -oP '\(\K[^\)]+' || true)
    
    for link in $links; do
        # 移除锚点 (#xxx)
        clean_link=$(echo "$link" | cut -d'#' -f1)
        if [ -z "$clean_link" ]; then
            continue
        fi
        
        # 解析出相对于项目根目录的绝对路径 (简化处理：假设要么是目录相对于根，要么是相对路径)
        # 这里做最简单的验证，如果文件或目录不存在则报警
        if [ ! -e "$clean_link" ]; then
            # 尝试把相对路径拼回去，或者当前是在项目根目录执行
            # 由于 AGENTS.md 和 README 都在根目录，直接 test -e 也是准确的
            dir=$(dirname "$file")
            if [ ! -e "$dir/$clean_link" ] && [ ! -e "$clean_link" ]; then
                log_error "[$file] 引用的路径不存在: $link (解析为 $clean_link)"
                FAILED=1
            fi
        fi
    done
}

export -f log_info
export -f log_error
export FAILED

log_info "开始检查文档路径..."
check_markdown_links "AGENTS.md"
check_markdown_links "README.md"
check_markdown_links "docs/ARCHITECTURE.md"
check_markdown_links "docs/TESTING.md"
check_markdown_links "docs/CODING_STANDARDS.md"
check_markdown_links "docs/DESIGN_PRINCIPLES.md"

if [ $FAILED -ne 0 ]; then
    log_error "❌ 文档检查失败: 发现失效的路径引用"
    exit 1
else
    log_info "🎉 所有文档引用检查通过！"
    exit 0
fi
