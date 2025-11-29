# Docker部署指南

## 🚀 快速开始

### 1. 本地开发环境

```bash
# 1. 复制环境变量文件
cp .env.docker.example .env

# 2. 编辑.env文件，填入你的AI API密钥
nano .env  # 或使用其他编辑器

# 3. 启动所有服务（开发模式，支持代码热重载）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# 4. 访问应用
# Web界面: http://localhost:5001
# MidScene服务: http://localhost:3001
# 数据库: localhost:5432
```

### 2. 生产环境部署

```bash
# 1. 确保.env已正确配置
cat .env

# 2. 构建并启动服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f web-app
docker-compose logs -f midscene-server

# 5. 初始化数据库（首次部署）
docker-compose exec web-app python -c "from web_gui.models import db; from web_gui.app_enhanced import create_app; app=create_app(); app.app_context().push(); db.create_all()"
```

### 3. 添加Nginx（可选，用于SSL）

```bash
# 使用production profile启动nginx
docker-compose --profile production up -d
```

---

## 📋 常用命令

### 服务管理

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启某个服务
docker-compose restart web-app

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f [service-name]
```

### 数据库操作

```bash
# 进入数据库容器
docker-compose exec postgres psql -U intent_user -d intent_test

# 备份数据库
docker-compose exec postgres pg_dump -U intent_user intent_test > backup.sql

# 恢复数据库
cat backup.sql | docker-compose exec -T postgres psql -U intent_user intent_test
```

### 应用管理

```bash
# 进入应用容器
docker-compose exec web-app bash

# 运行Python命令
docker-compose exec web-app python -c "print('Hello')"

# 运行测试
docker-compose exec web-app pytest tests/

# 清理日志
docker-compose exec web-app rm -rf logs/*
```

### 镜像和容器清理

```bash
# 重新构建镜像
docker-compose build --no-cache

# 清理未使用的镜像
docker image prune -a

# 完全清理（慎用，会删除数据）
docker-compose down -v  # -v会删除数据卷
```

---

## 🔧 故障排查

### 1. 服务无法启动

```bash
# 查看详细日志
docker-compose logs web-app
docker-compose logs midscene-server
docker-compose logs postgres

# 检查健康状态
docker-compose ps
```

### 2. 数据库连接失败

```bash
# 确认数据库是否健康
docker-compose exec postgres pg_isready

# 检查网络连接
docker-compose exec web-app ping postgres
```

### 3. 端口冲突

```bash
# 检查端口占用
lsof -i :5001
lsof -i :3001
lsof -i :5432

# 修改docker-compose.yml中的端口映射
```

### 4. 重置一切

```bash
# 停止并删除所有容器、网络、卷
docker-compose down -v

# 删除所有镜像
docker-compose down --rmi all

# 重新开始
docker-compose up -d
```

---

## 🔄 更新部署

### 方式1：重新构建

```bash
# 拉取最新代码
git pull

# 停止服务
docker-compose down

# 重新构建并启动
docker-compose up -d --build
```

### 方式2：不停机更新

```bash
# 拉取最新代码
git pull

# 构建新镜像
docker-compose build

# 滚动更新
docker-compose up -d --no-deps --build web-app
```

---

## 📊 资源监控

```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
docker system df

# 查看数据卷大小
docker volume ls
du -sh /var/lib/docker/volumes/intent-test-framework_postgres_data
```

---

## 🔐 安全建议

1. **生产环境必做**：
   - [ ] 修改 `.env` 中的数据库密码
   - [ ] 修改 `SECRET_KEY` 为随机字符串
   - [ ] 配置防火墙，只开放80/443端口
   - [ ] 设置定期数据库备份

2. **可选增强**：
   - [ ] 使用Docker secrets管理敏感信息
   - [ ] 配置Nginx SSL证书
   - [ ] 设置日志轮转
   - [ ] 配置监控告警

---

## 📦 备份和恢复

### 完整备份

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec -T postgres pg_dump -U intent_user intent_test > $BACKUP_DIR/database.sql

# 备份截图和日志
tar -czf $BACKUP_DIR/files.tar.gz web_gui/static/screenshots logs

echo "备份完成: $BACKUP_DIR"
```

### 恢复

```bash
#!/bin/bash
# restore.sh
BACKUP_DIR=$1

# 恢复数据库
cat $BACKUP_DIR/database.sql | docker-compose exec -T postgres psql -U intent_user intent_test

# 恢复文件
tar -xzf $BACKUP_DIR/files.tar.gz

echo "恢复完成"
```

---

## 🎯 性能优化

### 针对2核4G服务器

```yaml
# 在docker-compose.yml中添加资源限制
services:
  web-app:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
  
  midscene-server:
    deploy:
      resources:
        limits:
          cpus: '1'  
          memory: 1.5G
        reservations:
          cpus: '0.5'
          memory: 768M
```

---

## 💡 开发技巧

### 1. 只重启某个服务

```bash
# 代码更改后，只重启web-app
docker-compose restart web-app
```

### 2. 查看实时日志

```bash
# 同时查看所有服务日志
docker-compose logs -f

# 只看最近100行
docker-compose logs --tail=100 web-app
```

### 3. 进入容器调试

```bash
# 进入web-app容器
docker-compose exec web-app bash

# 进入midscene容器
docker-compose exec midscene-server sh
```

### 4. 本地代码修改立即生效

开发模式下，代码已挂载到容器中，修改后立即生效。
如果需要重启Flask应用：

```bash
docker-compose restart web-app
```

---

## 🌐 域名配置（可选）

如果你有域名，可以配置Nginx：

1. 创建 `nginx/nginx.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://web-app:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

2. 启动nginx:

```bash
docker-compose --profile production up -d
```

3. 配置SSL（Let's Encrypt）:

```bash
# 使用certbot容器
docker run -it --rm \
  -v ./nginx/ssl:/etc/letsencrypt \
  certbot/certbot certonly --standalone \
  -d your-domain.com
```

---

**问题反馈**: 如遇到问题，请检查日志 `docker-compose logs -f`
