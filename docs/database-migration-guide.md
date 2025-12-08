# 数据库迁移指南

从共享的 `langfuse-postgres-1` 迁移到独立的 PostgreSQL 容器

## 迁移概述

**目标**: 将生产环境从复用的 Langfuse 数据库迁移到独立管理的 PostgreSQL 容器

**收益**:
- ✅ 本地和云端环境完全一致
- ✅ 完全控制数据库配置和schema
- ✅ 独立的数据迁移和备份策略
- ✅ 避免与其他服务的冲突

## 前置准备

### 1. 备份现有数据（重要！）

在执行迁移前，先手动备份现有数据库：

```bash
# 在服务器上执行
docker exec langfuse-postgres-1 pg_dump -U postgres intent_test > backup_$(date +%Y%m%d).sql
```

### 2. 配置环境变量

复制并编辑环境变量文件：

```bash
cp .env.docker.example .env
```

在 `.env` 中设置：
```bash
DB_USER=intent_user
DB_PASSWORD=你的强密码  # 必须修改！
SECRET_KEY=你的随机密钥  # 必须修改！
FLASK_ENV=production
```

## 迁移步骤

### 步骤1: 拉取最新代码

```bash
cd /root/intent-test-framework
git pull origin main
```

### 步骤2: 启动新的PostgreSQL容器

```bash
# 只启动数据库服务
docker-compose -f docker-compose.prod.yml up -d postgres

# 检查容器状态
docker-compose -f docker-compose.prod.yml ps postgres

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f postgres
```

**预期输出**: 容器状态为 `Up (healthy)`

### 步骤3: 执行数据迁移

使用提供的迁移脚本：

```bash
# 赋予执行权限（如果还没有）
chmod +x scripts/migrate_langfuse_to_local.sh

# 执行迁移
./scripts/migrate_langfuse_to_local.sh
```

**脚本执行流程**:
1. 检查源数据库容器
2. 导出数据到 `database_backups/` 目录
3. 检查目标容器是否就绪
4. 导入数据到新容器
5. 验证数据完整性

### 步骤4: 启动Web应用

```bash
# 启动所有服务
docker-compose -f docker-compose.prod.yml up -d

# 检查所有容器状态
docker-compose -f docker-compose.prod.yml ps
```

### 步骤5: 验证迁移

#### 5.1 检查数据库连接

```bash
# 从宿主机连接数据库（端口5433）
docker exec -it intent-test-db-prod psql -U intent_user -d intent_test

# 在psql中执行：
\dt                          # 查看所有表
SELECT COUNT(*) FROM test_cases;
SELECT COUNT(*) FROM execution_history;
\q                           # 退出
```

#### 5.2 测试Web应用

1. 访问 `http://服务器IP:80`
2. 创建一个新的测试用例
3. 执行测试并查看结果
4. 检查执行历史是否正常保存

#### 5.3 检查应用日志

```bash
docker-compose -f docker-compose.prod.yml logs -f web-app
```

查找是否有数据库连接错误。

## 数据验证清单

- [ ] 所有表都已迁移（执行 `\dt` 查看）
- [ ] 测试用例数据完整
- [ ] 执行历史记录完整
- [ ] 变量管理表存在（如果使用）
- [ ] Web界面可以正常访问
- [ ] 可以创建新的测试用例
- [ ] 可以执行测试并保存结果

## 故障排除

### 问题1: 源容器不存在

**错误**: `✗ 源容器 langfuse-postgres-1 未运行！`

**解决**:
- 如果已经迁移过，选择 `y` 继续，脚本会使用现有备份
- 如果是首次迁移，检查源容器名称是否正确

### 问题2: 端口冲突

**错误**: `Error starting userland proxy: listen tcp4 0.0.0.0:5433: bind: address already in use`

**解决**:
```bash
# 查看占用5433端口的进程
sudo lsof -i :5433

# 修改 docker-compose.prod.yml 中的端口映射
# 将 "5433:5432" 改为其他端口，如 "5434:5432"
```

### 问题3: Web应用无法连接数据库

**错误**: 日志中显示连接超时或拒绝

**解决**:
```bash
# 1. 检查网络配置
docker network inspect intent-test-framework_intent-test-network

# 2. 确认web-app和postgres在同一网络
docker inspect intent-test-web | grep NetworkMode
docker inspect intent-test-db-prod | grep NetworkMode

# 3. 重启服务
docker-compose -f docker-compose.prod.yml restart web-app
```

### 问题4: 数据导入失败

**错误**: `✗ 数据导入失败！`

**解决**:
```bash
# 查看详细错误信息
cat database_backups/langfuse_migration_*.sql | docker exec -i intent-test-db-prod psql -U intent_user -d intent_test 2>&1 | tee import_errors.log

# 手动清理并重试
docker exec intent-test-db-prod psql -U intent_user -d intent_test -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
./scripts/migrate_langfuse_to_local.sh
```

## 回滚流程

如果迁移出现问题，需要回滚：

### 1. 停止新容器

```bash
docker-compose -f docker-compose.prod.yml down
```

### 2. 恢复旧配置

```bash
# 编辑 docker-compose.prod.yml，恢复旧的数据库连接
# 或者从git恢复
git checkout docker-compose.prod.yml
```

### 3. 重新部署

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 后续维护

### 数据库备份

建议设置定期备份：

```bash
# 创建备份脚本
cat > /root/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/root/intent-test-framework/database_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker exec intent-test-db-prod pg_dump -U intent_user intent_test | gzip > ${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz
# 保留最近7天的备份
find ${BACKUP_DIR} -name "backup_*.sql.gz" -mtime +7 -delete
EOF

chmod +x /root/backup_db.sh

# 添加到crontab（每天凌晨3点备份）
(crontab -l 2>/dev/null; echo "0 3 * * * /root/backup_db.sh") | crontab -
```

### 数据库监控

```bash
# 检查数据库大小
docker exec intent-test-db-prod psql -U intent_user -d intent_test -c "
SELECT pg_size_pretty(pg_database_size('intent_test')) AS db_size;
"

# 检查表大小
docker exec intent-test-db-prod psql -U intent_user -d intent_test -c "
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname='public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

## 其他注意事项

### 端口说明

- **宿主机访问**: `localhost:5433` → 新数据库容器
- **容器内访问**: `postgres:5432` → 新数据库容器（通过Docker网络）
- **旧数据库**: `langfuse-postgres-1:5432` → 可在迁移后停用

### 网络配置

新配置使用自定义网络 `intent-test-network`，确保：
- web-app 容器
- postgres 容器  
- nginx 容器

都在同一网络中，可以通过服务名互相访问。

### 资源配置

当前配置的资源限制：
- **PostgreSQL**: 0.5 CPU, 512MB 内存
- **Web应用**: 1.5 CPU, 1.5GB 内存
- **Nginx**: 0.5 CPU, 256MB 内存

根据实际使用情况调整 `docker-compose.prod.yml` 中的 `resources.limits`。
