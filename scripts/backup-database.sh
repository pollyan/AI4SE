#!/bin/bash

# ========================================
# 数据库备份脚本
# ========================================

set -e

GREEN='\033[0;32m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# 配置
CONTAINER="intent-test-db"
USER="postgres"
DB="intent_test"
BACKUP_DIR="./database_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"

log_info "创建数据库备份..."
mkdir -p "$BACKUP_DIR"

# 执行备份
docker exec "$CONTAINER" pg_dump -U "$USER" "$DB" > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    log_info "✅ 备份成功: $BACKUP_FILE"
    log_info "文件大小: $(du -h "$BACKUP_FILE" | cut -f1)"
    
    # 保留最近10个备份
    log_info "清理旧备份..."
    ls -t "$BACKUP_DIR"/backup_*.sql | tail -n +11 | xargs rm -f 2>/dev/null || true
else
    log_info "❌ 备份失败"
    exit 1
fi
