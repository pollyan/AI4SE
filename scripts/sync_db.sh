#!/bin/bash

# 数据库同步脚本：从远程数据库(Vercel/Supabase)同步到本地Docker
# 用法: ./scripts/sync_db.sh [远程数据库URL]

REMOTE_DB_URL=$1

# 检查参数
if [ -z "$REMOTE_DB_URL" ]; then
    echo "❌ 错误: 请提供远程数据库连接字符串"
    echo "用法: ./scripts/sync_db.sh \"postgres://user:pass@host:port/dbname\""
    echo ""
    echo "提示: 您可以在 Vercel 后台 -> Storage -> .env.local 中找到 POSTGRES_URL 或 DATABASE_URL"
    exit 1
fi

echo "=========================================="
echo "🔄 开始同步数据库..."
echo "📍 源数据库: (远程)"
echo "📍 目标数据库: 本地 Docker (intent-test-db)"
echo "=========================================="

# 确认提示
read -p "⚠️  警告: 这将覆盖本地数据库中的所有数据！是否继续？(y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "1. 正在导出远程数据 (pg_dump)..."
# 使用临时容器运行 pg_dump，避免本地安装依赖
# 注意：使用 --no-owner --no-acl 避免权限问题
# 注意：使用 postgres:17-alpine 以兼容较新的远程数据库版本
# 添加 -n public 只导出 public schema，避免导出 Supabase 系统表(storage, auth等)
docker run --rm postgres:17-alpine pg_dump "$REMOTE_DB_URL" \
    -n public --no-owner --no-acl --clean --if-exists \
    > dump_temp.sql

if [ $? -ne 0 ]; then
    echo "❌ 导出失败！请检查连接字符串是否正确。"
    rm -f dump_temp.sql
    exit 1
fi

echo "✅ 导出成功 (文件大小: $(du -h dump_temp.sql | cut -f1))"

echo ""
echo "2. 正在导入到本地数据库..."
# 导入到本地 postgres 容器
cat dump_temp.sql | docker-compose exec -T postgres psql -U intent_user -d intent_test

if [ $? -ne 0 ]; then
    echo "❌ 导入失败！"
    rm -f dump_temp.sql
    exit 1
fi

# 清理临时文件
rm -f dump_temp.sql

echo ""
echo "=========================================="
echo "🎉 数据库同步完成！"
echo "=========================================="
