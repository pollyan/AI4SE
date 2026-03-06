# 部署指南

> 生成日期: 2026-03-06 | 扫描级别: Deep Scan

## 部署架构

```text
┌─────────────────────────────────────────────────────────┐
│                    腾讯云服务器                            │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Nginx (80)  │  │ intent-tester│  │ new-agents-   │  │
│  │ 网关        │──│ Flask (5001) │  │ backend (5002)│  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│         │                │                  │           │
│         │          ┌─────┴──────┐           │           │
│         │          │ PostgreSQL │           │           │
│         │          │   (5432)   │◄──────────┘           │
│         │          └────────────┘                       │
│  ┌──────┴──────────────────────────────────────────┐    │
│  │ Docker Compose (docker-compose.prod.yml)        │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 开发环境部署

### 一键部署

```bash
./scripts/dev/deploy-dev.sh
```

### 部署选项

| 命令 | 说明 |
|------|------|
| `./scripts/dev/deploy-dev.sh` | 增量部署（默认） |
| `./scripts/dev/deploy-dev.sh full` | 全量重建（清除镜像缓存） |
| `./scripts/dev/deploy-dev.sh --skip-frontend` | 跳过前端构建 |

### 部署流程

1. 环境检查（`.env` 文件）
2. 构建前端产物（frontend, new-agents-frontend, 代理包）
3. Docker Compose 构建镜像
4. 启动所有容器
5. 重启 Nginx 刷新上游
6. 健康检查验证

### 服务地址

| 服务 | 地址 |
|------|------|
| 统一门户 | http://localhost |
| 意图测试 | http://localhost/intent-tester |
| AI 智能体 | http://localhost/new-agents |
| PostgreSQL | localhost:5432 |

---

## 生产环境部署

### 自动部署（推荐）

**绝不直接部署到服务器。** 推送到 `master` 分支 → GitHub Actions CI 测试 → 自动部署。

### CI/CD 流程

```text
Push to master
      │
      ▼
┌─────────────────────────────────────────┐
│ GitHub Actions - 并行测试                 │
│                                         │
│  backend-api-test ✓                     │
│  common-frontend-test ✓                 │
│  code-quality ✓                         │
│  proxy-test ✓                           │
└──────────────┬──────────────────────────┘
               │ 全部通过
               ▼
┌─────────────────────────────────────────┐
│ deploy-to-production                    │
│                                         │
│  1. 构建代理包                            │
│  2. 构建前端                              │
│  3. rsync 到腾讯云                        │
│  4. SSH 执行 scripts/ci/deploy.sh        │
└─────────────────────────────────────────┘
```

### 生产部署脚本行为

```bash
# 在服务器上执行
scripts/ci/deploy.sh production
```

1. **备份**: `rsync` 当前版本到 `/opt/intent-test-framework-backup/latest`
2. **停止服务**: `sudo docker-compose down`
3. **清理**: 移除残留容器和网络
4. **构建**: `sudo docker-compose build --no-cache`
5. **启动**: `sudo docker-compose up -d`
6. **健康检查**: `curl http://localhost:5001/health` (最多 10 次重试)
7. **失败回滚**: 自动从备份恢复并重启

### 手动部署（紧急情况）

```bash
# SSH 到服务器
ssh user@server

# 进入项目目录
cd /opt/intent-test-framework

# 拉取最新代码
git pull origin master

# 执行部署
./scripts/ci/deploy.sh production
```

---

## Docker 镜像

### Intent-Tester

- **基础镜像**: `python:3.11-slim`
- **构建上下文**: 项目根目录
- **Dockerfile**: `tools/intent-tester/docker/Dockerfile`
- **端口**: 5001
- **启动命令**: `python -m backend.app`
- **依赖**: `tools/intent-tester/requirements.txt` + `tools/shared/`
- **健康检查**: `requests.get('http://localhost:5001/health')`

### New Agents Backend

- **基础镜像**: `python:3.11-slim`
- **Dockerfile**: `tools/new-agents/backend/docker/Dockerfile`
- **端口**: 5002
- **启动命令**: `gunicorn -c docker/gunicorn.conf.py app:app`
- **依赖**: `tools/new-agents/backend/requirements.txt`

### New Agents Frontend

- **开发环境**: `nginx:alpine` + 挂载 `frontend/dist/`（秒级启动）
- **生产环境**: 多阶段构建 `node:20-alpine` → `nginx:alpine`

---

## 环境变量

### 必需变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `DB_USER` | 数据库用户名 | `ai4se_user` |
| `DB_PASSWORD` | 数据库密码 | `change_me_in_production` |
| `SECRET_KEY` | Flask 密钥 | `random-secure-string` |

### 可选变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `FLASK_ENV` | Flask 环境 | `production` |
| `MIDSCENE_SERVER_URL` | MidScene 服务地址 | `http://host.docker.internal:3001` |

### CI/CD Secrets (GitHub)

| Secret | 说明 |
|--------|------|
| `SERVER_HOST` | 腾讯云服务器 IP |
| `SERVER_USER` | SSH 用户名 |
| `SSH_PRIVATE_KEY` | SSH 私钥 |
| `DB_PASSWORD` | 生产数据库密码 |
| `SECRET_KEY` | 生产 Flask 密钥 |

---

## 健康检查

### 脚本

```bash
./scripts/health/health_check.sh local    # 本地
./scripts/health/health_check.sh          # 默认
```

### 端点

| 服务 | 端点 | 预期 |
|------|------|------|
| Nginx 网关 | `http://localhost/health` | 200 |
| Intent-Tester | `http://localhost:5001/health` | `{"status": "ok"}` |
| New Agents Backend | `http://localhost:5002/api/health` | `{"status": "ok"}` |

---

## 故障排查

### 服务无法启动

```bash
# 检查容器状态
docker-compose -f docker-compose.dev.yml ps

# 查看失败容器日志
docker-compose -f docker-compose.dev.yml logs intent-tester

# 检查端口占用
lsof -i :5001
lsof -i :5002
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 容器
docker-compose -f docker-compose.dev.yml logs postgres

# 手动连接测试
docker exec -it ai4se-db psql -U ai4se_user -d ai4se
```

### Nginx 502 Bad Gateway

```bash
# 检查上游服务是否健康
curl http://localhost:5001/health
curl http://localhost:5002/api/health

# 重启 Nginx
docker-compose -f docker-compose.dev.yml restart nginx
```
