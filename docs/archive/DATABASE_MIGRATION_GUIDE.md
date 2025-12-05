# 数据库迁移指南

## 概述

本指南说明如何将数据从 Supabase 迁移到腾讯云 PostgreSQL，并确保数据在后续部署中持久保存。

## 🎯 目标

1. ✅ 从 Supabase 导出所有数据
2. ✅ 导入到腾讯云 PostgreSQL
3. ✅ 确保后续部署不会清空数据

## 📋 前置条件

### 本地环境需要

```bash
# 1. 安装 PostgreSQL 客户端工具
brew install postgresql  # macOS
# 或
sudo apt-get install postgresql-client  # Linux

# 2. 确保本地服务正在运行
docker ps | grep intent-test-db

# 3. 如果未运行，先启动服务
docker-compose up -d
```

## 🚀 迁移步骤

### 步骤 1: 执行迁移脚本

```bash
# 在项目根目录执行
./scripts/migrate-from-supabase.sh
```

脚本会自动：
- ✅ 从 Supabase 导出数据
- ✅ 清理 Supabase 特定内容
- ✅ 备份当前腾讯云数据
- ✅ 导入到腾讯云 PostgreSQL
- ✅ 验证数据完整性

### 步骤 2: 验证迁移结果

```bash
# 连接到数据库
docker exec -it intent-test-db psql -U postgres intent_test

# 查看所有表
\dt

# 检查数据量
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public';

# 退出
\q
```

### 步骤 3: 测试应用

```bash
# 启动应用
docker-compose up -d

# 访问应用
open http://localhost:5001

# 测试核心功能
# - 登录
# - 查看测试用例
# - 创建/编辑数据
```

## 🔒 数据持久化保证

### 修改说明

我们已经修改了部署脚本 `scripts/deploy.sh`：

```bash
# 修改前（会删除数据卷）
$DOCKER_CMD -f "$COMPOSE_FILE" down -v || true

# 修改后（保留数据卷）
$DOCKER_CMD -f "$COMPOSE_FILE" down || true
```

### Docker 卷配置

数据存储在命名卷中，即使容器删除也不会丢失：

```yaml
# docker-compose.yml
volumes:
  postgres_data:
    driver: local
```

数据实际存储位置：
- **macOS**: `/var/lib/docker/volumes/intent-test-framework-1_postgres_data/_data`
- **Linux**: `/var/lib/docker/volumes/intent-test-framework-1_postgres_data/_data`

## 📦 定期备份

### 手动备份

```bash
# 执行备份
./scripts/backup-database.sh

# 备份文件保存在
ls -lh database_backups/
```

### 自动备份（推荐）

可以设置 cron 任务定期备份：

```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨 3 点备份
0 3 * * * cd /path/to/project && ./scripts/backup-database.sh
```

## 🔄 数据库架构更新

如果需要更新数据库结构（添加表、字段等）：

### 使用 Flask-Migrate

```bash
# 生成迁移脚本
flask db migrate -m "添加新字段"

# 查看迁移脚本
cat migrations/versions/xxx_添加新字段.py

# 应用迁移
flask db upgrade
```

## 🌐 远程部署数据迁移

### SSH 到腾讯云服务器

```bash
ssh user@your-server-ip

# 切换到项目目录
cd /opt/intent-test-framework

# 执行迁移脚本
./scripts/migrate-from-supabase.sh
```

### 或使用scp上传备份

```bash
# 1. 在本地执行迁移获取备份
./scripts/migrate-from-supabase.sh

# 2. 上传备份到服务器
scp database_backups/supabase_backup_*.sql user@server:/tmp/

# 3. SSH 到服务器导入
ssh user@server
cd /opt/intent-test-framework
docker exec -i intent-test-db psql -U postgres intent_test < /tmp/supabase_backup_*.sql
```

## ⚠️ 注意事项

### 已知问题

1. **Supabase 特定扩展**
   - 迁移脚本会自动过滤 Supabase 系统表（auth, storage等）
   - 只迁移 `public` schema

2. **数据卷删除风险**
   - ⚠️ 永远不要使用 `docker-compose down -v`
   - ⚠️ 永远不要使用 `docker volume rm`

3. **迁移时间**
   - 数据量小：< 1 分钟
   - 数据量中：1-5 分钟
   - 数据量大：> 5 分钟

### 回滚方案

如果迁移失败，可以恢复：

```bash
# 恢复到迁移前的状态
docker exec -i intent-test-db psql -U postgres intent_test < database_backups/tencent_backup_before_migration_*.sql
```

## 📚 相关文件

- `scripts/migrate-from-supabase.sh` - 迁移脚本
- `scripts/backup-database.sh` - 备份脚本
- `scripts/deploy.sh` - 部署脚本（已修改保留数据）
- `docker-compose.yml` - Docker 配置
- `docker-compose.prod.yml` - 生产环境配置

## ✅ 验证清单

迁移完成后，请验证：

- [ ] 所有表都已迁移
- [ ] 数据量正确
- [ ] 应用功能正常
- [ ] 可以创建/编辑/删除数据
- [ ] 重启容器后数据仍存在
- [ ] 备份文件已保存

---

**需要帮助？** 查看迁移脚本输出日志或联系技术支持。
