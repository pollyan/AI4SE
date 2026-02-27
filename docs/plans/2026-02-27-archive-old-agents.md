# 归档旧 AI Agent 代码库 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 将 `tools/ai-agents` 旧代码干净地归档，并从本地开发环境、CI 流水线、生产环境中彻底移除其运行时依赖，使 `new-agents` 成为唯一的 AI 助手入口。

**架构思路：**
- 使用 Git 的标准移动命令将旧代码归档到 `archive` 目录，保留完整的 Git 历史。
- 从 Docker Compose（dev + prod）、Nginx、部署脚本、CI 流水线中剥离所有 `ai-agents` 的痕迹。
- 将全局门户前端中指向 `/ai-agents/` 的链接全部重定向到 `/new-agents/`。

**技术栈：** Docker, Nginx, Bash, TypeScript, GitHub Actions, Git

---

## 影响范围速查

在执行前，以下是所有涉及 `ai-agents` 的文件清单：

| 文件 | 影响 |
|------|------|
| `tools/ai-agents/` | 需要归档到 `archive/` |
| `docker-compose.dev.yml` | 移除 `ai-agents` service 和 nginx depends_on |
| `docker-compose.prod.yml` | 移除 `ai-agents` service 和 nginx depends_on |
| `nginx/nginx.conf` | 移除 `upstream ai_agents` 和两个 `location /ai-agents/` 块 |
| `.github/workflows/deploy.yml` | 移除 `ai-agents-test`、`ai-agents-frontend-test` job、构建步骤和 needs 依赖 |
| `scripts/dev/deploy-dev.sh` | 从 `JS_PROJECTS` 和 echo 输出中移除 |
| `scripts/test/test-local.sh` | 移除本地测试中的 ai-agents 相关路径和执行 |
| `scripts/health/health_check.sh` | 移除 `/ai-agents/` 的健康检查端点 |
| `scripts/health/README.md` | 移除 ai-agents 相关文档条目 |
| `tools/frontend/src/**/*.tsx` | 将所有 `/ai-agents/` 链接替换为 `/new-agents/` |

---

### Task 1: 归档旧 Agent 代码

**文件：**
- 移动: `tools/ai-agents` → `archive/ai-agents`

**步骤 1：移动代码**

```bash
mkdir -p archive
git mv tools/ai-agents archive/ai-agents
```

**步骤 2：提交**

```bash
git commit -m "chore(agents): archive legacy ai-agents codebase"
```

---

### Task 2: 清理 Nginx 配置

**文件：**
- 修改: `nginx/nginx.conf`

**步骤 1：删除 ai-agents 相关配置**

需要删除以下三个区块：
1. `upstream ai_agents { server ai-agents:5002; }` 块（第 35-37 行附近）
2. `location /ai-agents/ { ... }` 代理块（第 92-106 行附近）
3. `location /ai-agents/static/ { ... }` 静态资源块（第 108-113 行附近）

**步骤 2：验证**

```bash
grep -n "ai_agents\|ai-agents" nginx/nginx.conf
# 预期输出: 空（无匹配）
```

**步骤 3：提交**

```bash
git add nginx/nginx.conf
git commit -m "chore(infra): remove ai-agents proxy from nginx config"
```

---

### Task 3: 清理 Docker Compose（dev 环境）

**文件：**
- 修改: `docker-compose.dev.yml`

**步骤 1：修改文件**

1. 删除整个 `ai-agents` service 定义块
2. 从 `nginx` 服务的 `depends_on` 列表中移除 `- ai-agents`

**步骤 2：验证**

```bash
grep -n "ai-agents" docker-compose.dev.yml
# 预期输出: 空
```

**步骤 3：提交**

```bash
git add docker-compose.dev.yml
git commit -m "chore(infra): remove ai-agents service from dev compose"
```

---

### Task 4: 清理 Docker Compose（prod 环境）

**文件：**
- 修改: `docker-compose.prod.yml`

**步骤 1：修改文件**

1. 删除第 72-106 行的整个 `ai-agents` service 定义块
2. 从 `nginx` 服务的 `depends_on`（第 122 行）中移除 `- ai-agents`

> **注意：** prod 环境目前还没有 `new-agents` 服务的定义，本次计划暂不添加，后续迭代时再加。

**步骤 2：验证**

```bash
grep -n "ai-agents" docker-compose.prod.yml
# 预期输出: 空
```

**步骤 3：提交**

```bash
git add docker-compose.prod.yml
git commit -m "chore(infra): remove ai-agents service from prod compose"
```

---

### Task 5: 清理 CI 流水线（GitHub Actions）

**文件：**
- 修改: `.github/workflows/deploy.yml`

**步骤 1：删除测试 job**

删除以下两个完整的 job 定义：
1. `ai-agents-test`（第 56-83 行）— AI Agents 后端 Python 测试
2. `ai-agents-frontend-test`（第 85-106 行）— AI Agents 前端测试

**步骤 2：修改部署 job 的 needs 依赖**

将第 197 行的：
```yaml
needs: [intent-tester-test, ai-agents-test, ai-agents-frontend-test, common-frontend-test, proxy-test]
```
改为：
```yaml
needs: [intent-tester-test, common-frontend-test, proxy-test]
```

**步骤 3：删除部署阶段中的 AI Agents 前端构建步骤**

删除第 220-227 行的 `Build React frontend (AI Agents)` 步骤。

**步骤 4：清理代码质量检查**

将第 153 行的 flake8 命令中的 `tools/ai-agents/backend` 路径移除：
```yaml
flake8 tools/intent-tester/backend --count --select=E9,F63,F7,F82 --show-source --statistics || true
```

**步骤 5：验证**

```bash
grep -n "ai-agents" .github/workflows/deploy.yml
# 预期输出: 空
```

**步骤 6：提交**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: remove ai-agents test jobs and build steps from pipeline"
```

---

### Task 6: 清理本地测试脚本

**文件：**
- 修改: `scripts/test/test-local.sh`

**步骤 1：修改文件**

需要清理以下几处：
1. **PYTHONPATH**（第 70 行）：从路径中移除 `$PROJECT_ROOT/tools/ai-agents`
2. **快速测试块**（第 84-86 行附近）：删除 `if [ -d "tools/ai-agents/backend/tests" ]` 整个条件分支
3. **慢速测试块**（第 116-121 行附近）：同上，删除 ai-agents 相关的 PYTHONPATH 设置和测试执行
4. **flake8 检查**（第 148 行附近）：从 flake8 命令中移除 `tools/ai-agents/backend`
5. **前端测试**（第 215 行附近）：删除跳转到 `tools/ai-agents/frontend` 并执行测试的代码块

**步骤 2：验证**

```bash
grep -n "ai-agents" scripts/test/test-local.sh
# 预期输出: 空
```

**步骤 3：提交**

```bash
git add scripts/test/test-local.sh
git commit -m "chore(test): remove ai-agents from local test script"
```

---

### Task 7: 清理部署脚本和健康检查

**文件：**
- 修改: `scripts/dev/deploy-dev.sh`
- 修改: `scripts/health/health_check.sh`
- 修改: `scripts/health/README.md`

**步骤 1：清理 deploy-dev.sh**

1. 将 `JS_PROJECTS` 数组（第 65 行）中的 `"tools/ai-agents/frontend"` 移除
2. 删除两处 `echo "   🤖 AI 智能体: http://localhost/ai-agents"` 输出（第 146 行和第 171 行）

**步骤 2：清理 health_check.sh**

删除以下健康检查端点条目：
- `/ai-agents/|AI 智能体首页`（第 174 行）
- `/ai-agents/config|AI 配置页面`（第 175 行）
- `/ai-agents/health|GET|AI Agents 健康检查`（第 231 行）
- `/ai-agents/api/ai-configs|GET|AI 配置列表 API`（第 233 行）

**步骤 3：清理 README.md**

删除 `scripts/health/README.md` 中引用 `/ai-agents/` 的表格行。

**步骤 4：验证**

```bash
grep -rn "ai-agents" scripts/
# 预期输出: 空
```

**步骤 5：提交**

```bash
git add scripts/
git commit -m "chore(scripts): remove all ai-agents references from scripts"
```

---

### Task 8: 重定向门户前端链接

**文件：**
- 修改: `tools/frontend/src/components/Navbar.tsx`
- 修改: `tools/frontend/src/components/Footer.tsx`
- 修改: `tools/frontend/src/components/CompactLayout.tsx`
- 修改: `tools/frontend/src/pages/Home/HeroSection.tsx`
- 修改: `tools/frontend/src/pages/Home/ModulesSection.tsx`

**步骤 1：全局替换链接**

将上述文件中所有 `href="/ai-agents/"` 替换为 `href="/new-agents/"`。
将所有 `href="/ai-agents/config"` 替换为 `href="/new-agents/"`（配置页面在新 Agent 中暂无独立路由，统一指向主页）。

**步骤 2：构建验证**

```bash
cd tools/frontend && npm run build
```

**步骤 3：链接残留检查**

```bash
grep -rn "/ai-agents/" tools/frontend/src/
# 预期输出: 空
```

**步骤 4：提交**

```bash
git add tools/frontend/src/
git commit -m "feat(frontend): redirect portal links from /ai-agents/ to /new-agents/"
```

---

### Task 9: 线上环境清理（全自动，无需手动 SSH）

> **重要说明：** 本项目遵循 DevOps 最佳实践，通过 GitHub Actions 部署到腾讯云。线上清理**完全自动化**，无需手动 SSH 到服务器。

**原理说明：**

`scripts/ci/deploy.sh` 在每次部署时会执行以下清理流程：
1. `docker-compose -f docker-compose.prod.yml down` — 停止 Compose 定义中的服务
2. **关键保障：** `docker ps -a | grep -E "(intent-test|ai4se)" | xargs docker rm -f` — 用模式匹配强制清理所有名称包含 `ai4se` 的残留容器（包括已从 Compose 配置中移除的 `ai4se-agents-prod`）
3. `docker image prune -f` — 清理悬空镜像，释放磁盘空间

因此，当更新后的 `docker-compose.prod.yml`（不再有 ai-agents service）和 `nginx.conf` 通过 CI 同步到服务器并执行 `deploy.sh production` 后，旧容器会被自动清理干净。

**步骤 1：合并到 master 并等待 CI 部署**

当本分支合并到 master 后，CI 流水线会自动：
- 跳过已删除的 ai-agents 测试 job
- 不再构建 ai-agents 前端
- 将更新后的 `docker-compose.prod.yml` 和 `nginx.conf` 同步到服务器
- 执行 `scripts/ci/deploy.sh production`，该脚本会自动清理旧容器、构建新镜像、启动服务并执行健康检查

**步骤 2：验证 CI 部署结果**

在 GitHub Actions 页面确认部署成功后，验证线上环境：
```bash
# 检查 /new-agents/ 是否正常（需要后续迭代添加 prod 服务后才可用）
# curl -o /dev/null -s -w "%{http_code}" http://www.datou212.tech/new-agents/

# 检查 /ai-agents/ 已被移除
curl -o /dev/null -s -w "%{http_code}" http://www.datou212.tech/ai-agents/
# 预期: 404
```

---

### Task 10: 端到端验证（本地）

**步骤 1：重新部署本地环境**

```bash
bash scripts/dev/deploy-dev.sh
```

**步骤 2：验证新 Agent 可访问**

在浏览器访问 `http://localhost/new-agents/`，确认页面正常加载。

**步骤 3：验证旧入口不可访问**

在浏览器访问 `http://localhost/ai-agents/`，确认返回 404。

**步骤 4：验证门户链接跳转正确**

在浏览器访问 `http://localhost/`，点击链接确认跳转至 `/new-agents/`。
