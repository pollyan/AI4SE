#!/bin/bash

# ========================================
# 数据库迁移脚本：Supabase → 腾讯云 PostgreSQL
# ========================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\ 033[1;33m'
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

# Supabase 连接信息
SUPABASE_URL="postgresql://postgres.jzmqsuxphksbulrbhebp:Shunlian04@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

# 腾讯云 PostgreSQL （Docker 容器）
TENCENT_CONTAINER="intent-test-db"
TENCENT_USER="postgres"
TENCENT_DB="intent_test"

# 备份目录
BACKUP_DIR="./database_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/supabase_backup_$TIMESTAMP.sql"

log_info "========================================"
log_info "数据库迁移：Supabase → 腾讯云"
log_info "========================================"

# 1. 创建备份目录
log_info "创建备份目录..."
mkdir -p "$BACKUP_DIR"

# 2. 从 Supabase 导出数据
log_info "从 Supabase 导出数据..."
log_warn "这可能需要几分钟，请耐心等待..."

# 使用 pg_dump 导出（只导出 public schema，排除 Supabase 系统表）
pg_dump "$SUPABASE_URL" \
    --schema=public \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    --file="$BACKUP_FILE"

if [ $? -eq 0 ]; then
    log_info "✅ 数据导出成功: $BACKUP_FILE"
    log_info "文件大小: $(du -h "$BACKUP_FILE" | cut -f1)"
else
    log_error "❌ 数据导出失败"
    exit 1
fi

# 3. 清理 SQL 文件（移除 Supabase 特定内容）
log_info "清理 SQL 文件..."
sed -i.bak '/^COMMENT ON EXTENSION/d' "$BACKUP_FILE" 2>/dev/null || true
sed -i.bak '/supabase_/d' "$BACKUP_FILE" 2>/dev/null || true

# 4. 检查腾讯云 PostgreSQL 容器是否运行
log_info "检查腾讯云数据库容器..."
if ! docker ps | grep -q "$TENCENT_CONTAINER"; then
    log_error "❌ 容器 $TENCENT_CONTAINER 未运行"
    log_info "请先启动服务: docker-compose up -d"
    exit 1
fi

log_info "✅ 容器正在运行"

# 5. 备份现有腾讯云数据（如果有）
log_info "备份现有腾讯云数据..."
docker exec "$TENCENT_CONTAINER" pg_dump -U "$TENCENT_USER" "$TENCENT_DB" > "$BACKUP_DIR/tencent_backup_before_migration_$TIMESTAMP.sql" 2>/dev/null || true

# 6. 导入数据到腾讯云
log_info "导入数据到腾讯云 PostgreSQL..."
log_warn "这将清空现有数据并导入 Supabase 数据"

# 等待用户确认
read -p "是否继续？[y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "取消迁移"
    exit 0
fi

# 复制 SQL 文件到容器
docker cp "$BACKUP_FILE" "$TENCENT_CONTAINER:/tmp/import.sql"

# 执行导入
docker exec -i "$TENCENT_CONTAINER" psql -U "$TENCENT_USER" -d "$TENCENT_DB" < "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    log_info "✅ 数据导入成功"
else
    log_error "❌ 数据导入失败"
    log_info "可以使用备份恢复: $BACKUP_DIR/tencent_backup_before_migration_$TIMESTAMP.sql"
    exit 1
fi

# 7. 验证数据
log_info "验证数据..."
TABLE_COUNT=$(docker exec "$TENCENT_CONTAINER" psql -U "$TENCENT_USER" -d "$TENCENT_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
log_info "数据库表数量: $TABLE_COUNT"

# 8. 清理临时文件
docker exec "$TENCENT_CONTAINER" rm -f /tmp/import.sql

log_info "========================================"
log_info "🎉 迁移完成！"
log_info "========================================"
log_info "备份文件保存在: $BACKUP_DIR"
log_info "Supabase 导出: $BACKUP_FILE"
log_info "迁移前备份: $BACKUP_DIR/tencent_backup_before_migration_$TIMESTAMP.sql"
log_info "========================================"
log_warn "请测试应用功能，确认数据迁移成功"
log_info "========================================"
