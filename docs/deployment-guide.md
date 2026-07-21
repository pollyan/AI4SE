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

**绝不直接部署到 live 目录。** 受保护的 `master` SHA 经 GitHub Actions 全部测试后，由发布事务自动部署。

推送前必须先在本机对最终 `HEAD` 执行固定全量验证：首次运行 `./scripts/dev/install-git-hooks.sh` 安装 versioned hook；也可显式运行 `./scripts/test/pre-push.sh`。该命令会在隔离的 loopback Compose 项目中验证 Nginx、New Agents frontend/backend、PostgreSQL、重启恢复和真实模型 E2E。它不部署到生产，也不替代随后 GitHub Actions 的远端复验。

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
│  1. 构建发布包与 SHA/内容摘要 manifest       │
│  2. 传输到独立 uploads/run-attempt-sha      │
│  3. 锁内预检并构建 immutable release       │
│  4. 原子切换、完整 readiness 或可信回滚      │
└─────────────────────────────────────────┘
```

### 生产发布事务

发布唯一入口是上传包内的 `scripts/ci/release_transaction.py`；`scripts/ci/deploy.sh production` 和 `scripts/health/health_check.sh production` 会明确失败，不能绕过该事务。

1. GitHub 将受保护 SHA、release manifest 与代码传入唯一的 `uploads/<run>-<attempt>-<sha>/` 目录。
2. 远端以 `flock` 串行化发布，重算内容摘要，并只在 `releases/<sha>/` 中生成候选与 mode `0600` 的私有环境文件。
3. 候选先完成 Compose config、镜像 build 与 image identity 记录；这些步骤不会停止当前服务。
4. 只有预检成功后才原子更新 `current` symlink，并使用同一个 Compose project 受控重建。
5. 成功必须同时证明 New Agents 页面、gateway backend health、DB-backed readiness、typed SSE 与 PostgreSQL 临时读写；任一失败都以 recorded previous release 的 source/env/image identity 重建并复验。

首次迁移是刻意 fail-closed：若服务器没有 `current -> releases/<known-sha>` 的可信基线及 active state，事务拒绝切换。需由受权运维人员在维护窗口以已验证 SHA 建立基线；不能用 `git pull`、复制未知 live 目录或伪造 state 绕过。

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
| `DB_PASSWORD` | 数据库密码 | 仅 GitHub Secret / 远端私有 env |
| `SECRET_KEY` | Flask 密钥 | 仅 GitHub Secret / 远端私有 env |
| `NEW_AGENTS_DEFAULT_LLM_API_KEY` | New Agents 后端默认 LLM API Key | 仅 GitHub Secret / 远端私有 env |
| `NEW_AGENTS_DEFAULT_LLM_BASE_URL` | New Agents 后端默认 LLM Base URL | `https://api.deepseek.com` |
| `NEW_AGENTS_DEFAULT_LLM_MODEL` | New Agents 后端默认模型名 | `deepseek-v4-flash` |
| `NEW_AGENTS_CONFIG_ADMIN_API_KEY` | New Agents 配置写入和模型检测的独立管理密钥 | `随机高熵字符串` |
| `PROXY_API_KEY` | New Agents 运行时直连后端的代理密钥 | `随机高熵字符串` |

### 可选变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `FLASK_ENV` | Flask 环境 | `production` |
| `MIDSCENE_SERVER_URL` | MidScene 服务地址 | `http://host.docker.internal:3001` |
| `NEW_AGENTS_DEFAULT_LLM_DESCRIPTION` | New Agents 后端默认模型说明 | `GitHub Actions managed default LLM config` |
| `NEW_AGENTS_CONFIG_ADMIN_ALLOW_UNAUTHENTICATED` | 仅本地开发可显式放开配置管理；生产环境强制忽略 | `false` |

`NEW_AGENTS_DEFAULT_LLM_API_KEY`、`NEW_AGENTS_CONFIG_ADMIN_API_KEY` 与 `PROXY_API_KEY` 必须使用三个不同的高熵值。GitHub 部署、部署脚本和应用请求边界都会拒绝重复值。开发 Compose 默认关闭匿名配置管理，并将 80/443 仅绑定 `127.0.0.1`；确需本机表单配置时，操作者必须显式设置 `AI4SE_ENV=development` 和 `NEW_AGENTS_CONFIG_ADMIN_ALLOW_UNAUTHENTICATED=true`。

### CI/CD Secrets (GitHub)

| Secret | 说明 |
|--------|------|
| `SERVER_HOST` | 腾讯云服务器 IP |
| `SERVER_USER` | SSH 用户名 |
| `SSH_PRIVATE_KEY` | SSH 私钥 |
| `DB_PASSWORD` | 生产数据库密码 |
| `SECRET_KEY` | 生产 Flask 密钥 |
| `NEW_AGENTS_DEFAULT_LLM_API_KEY` | New Agents 后端默认 LLM API Key |
| `NEW_AGENTS_DEFAULT_LLM_BASE_URL` | New Agents 后端默认 LLM Base URL |
| `NEW_AGENTS_DEFAULT_LLM_MODEL` | New Agents 后端默认模型名 |
| `NEW_AGENTS_DEFAULT_LLM_DESCRIPTION` | New Agents 后端默认模型说明，可选 |
| `NEW_AGENTS_CONFIG_ADMIN_API_KEY` | New Agents 配置管理独立密钥；不得与模型或代理 Key 复用 |
| `PROXY_API_KEY` | New Agents 后端代理密钥；不得与模型或配置管理 Key 复用 |

---

## 健康检查

### 脚本

```bash
./scripts/health/health_check.sh local    # 本地
./scripts/health/health_check.sh          # 默认
```

它只用于 local/dev 诊断，不能作为生产发布成功条件。生产 release 的唯一 verdict 是 transaction 内的完整 readiness。

### 端点

| 服务 | 端点 | 预期 |
|------|------|------|
| Nginx 网关 | `http://localhost/health` | 200 |
| Intent-Tester | `http://localhost:5001/health` | `{"status": "ok"}` |
| New Agents Backend | `http://localhost:5002/api/health` | `{"status": "ok"}` |
| New Agents Readiness | `http://localhost/new-agents/api/readiness` | DB-backed `{"status":"ok","database":"ok"}` |
| New Agents SSE Readiness | `http://localhost/new-agents/api/readiness/stream` | typed `run_started` SSE + `[DONE]` |

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
