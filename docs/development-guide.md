# 开发指南

> 生成日期: 2026-03-06 | 扫描级别: Deep Scan

## 前置条件

| 工具 | 版本要求 | 用途 |
|------|----------|------|
| **Python** | 3.11+ | 后端服务 |
| **Node.js** | 20+ | 前端构建、MidScene 代理 |
| **Docker** | 最新版 | 容器化部署 |
| **Docker Compose** | v2+ | 服务编排 |
| **Git** | 最新版 | 版本控制 |

## 环境配置

### 1. 克隆仓库

```bash
git clone <repo-url> AI4SE
cd AI4SE
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置以下必需变量:
# DB_USER=ai4se_user
# DB_PASSWORD=your_password
# SECRET_KEY=your-secret-key
```

### 3. 安装 Python 依赖

```bash
# 根级依赖
pip install -r requirements.txt

# Intent-Tester 依赖
pip install -r tools/intent-tester/requirements.txt

# New Agents Backend 依赖
pip install -r tools/new-agents/backend/requirements.txt
```

### 4. 安装 Node.js 依赖

```bash
# 统一门户前端
cd tools/frontend && npm install

# Intent-Tester (MidScene + Jest)
cd tools/intent-tester && npm install

# New Agents 前端
cd tools/new-agents/frontend && npm install
```

---

## Docker 开发部署

### 一键部署（推荐）

```bash
# 增量部署（首次或常规更新）
./scripts/dev/deploy-dev.sh

# 全量重建（依赖变更或问题排查）
./scripts/dev/deploy-dev.sh full

# 跳过前端构建（仅后端改动时）
./scripts/dev/deploy-dev.sh --skip-frontend
```

### 部署脚本行为

1. 检查/创建 `.env` 文件
2. 构建前端产物（frontend, new-agents-frontend）
3. 构建 MidScene 代理包
4. Docker Compose 构建并启动所有服务
5. 重启 Nginx 刷新上游
6. 执行健康检查

### 访问地址

| 服务 | URL |
|------|-----|
| 统一门户 | http://localhost |
| 意图测试 | http://localhost/intent-tester |
| AI 智能体 | http://localhost/new-agents |

### 查看日志

```bash
docker-compose -f docker-compose.dev.yml logs -f
docker-compose -f docker-compose.dev.yml logs -f intent-tester
docker-compose -f docker-compose.dev.yml logs -f new-agents-backend
```

---

## 本地开发（非 Docker）

### 前端开发服务器

```bash
# 统一门户
cd tools/frontend && npm run dev

# New Agents 前端
cd tools/new-agents/frontend && npm run dev
```

### MidScene 代理（本地运行浏览器自动化时需要）

```bash
cd tools/intent-tester
OPENAI_API_KEY=your-key npm start
# 运行在 http://localhost:3001
```

---

## 测试

### 运行所有测试

```bash
./scripts/test/test-local.sh
```

### 按类型运行

```bash
# Intent-Tester API 测试
./scripts/test/test-local.sh api
# 或: pytest tools/intent-tester/tests/ -v

# MidScene 代理测试
./scripts/test/test-local.sh proxy
# 或: cd tools/intent-tester && npm run test:proxy

# 代码质量检查
./scripts/test/test-local.sh lint
# 或: flake8 --select=E9,F63,F7,F82 .

# New Agents Backend 测试
cd tools/new-agents/backend && pytest tests/test_api.py -c pytest.ini

# New Agents Frontend 测试
cd tools/new-agents/frontend && npm test

# 冒烟测试
./scripts/test/test-local.sh smoke
```

### 测试标记 (pytest)

```bash
pytest -m unit        # 仅单元测试
pytest -m api         # 仅 API 测试
pytest -m integration # 集成测试
pytest -m "not slow"  # 跳过慢速测试
```

### 测试覆盖率

```bash
# Python 覆盖率
pytest --cov=backend --cov-report=html tools/intent-tester/tests/

# Jest 覆盖率
cd tools/intent-tester && npm run test:proxy:coverage
```

---

## 构建

### 前端构建

```bash
# 统一门户
cd tools/frontend && npm run build    # 输出: dist/

# New Agents 前端
cd tools/new-agents/frontend && npm run build    # 输出: dist/

# MidScene 代理包
node scripts/ci/build-proxy-package.js    # 输出: dist/intent-test-proxy.zip
```

### Docker 镜像构建

```bash
# 全部构建
docker-compose -f docker-compose.dev.yml build

# 单独构建某个服务
docker-compose -f docker-compose.dev.yml build intent-tester
docker-compose -f docker-compose.dev.yml build new-agents-backend
```

---

## 代码质量

### Lint

```bash
# Python (关键错误)
flake8 --select=E9,F63,F7,F82 .

# Python (完整检查)
flake8 .

# Python 格式化
black .

# TypeScript/React
cd tools/frontend && npm run lint
cd tools/new-agents/frontend && npm run lint
```

### 提交前检查清单

- [ ] 测试通过: `./scripts/test/test-local.sh`
- [ ] Lint 无新错误
- [ ] 已部署到 Docker 验证: `./scripts/dev/deploy-dev.sh`
- [ ] 删除了过期代码和无用测试

---

## CI/CD 流水线

### GitHub Actions 触发条件

- Push 到 `master`/`main` 分支
- Pull Request
- 手动触发 (`workflow_dispatch`)

### CI 测试阶段（并行执行）

| Job | 说明 |
|-----|------|
| **backend-api-test** | Intent-Tester + New Agents Backend pytest |
| **common-frontend-test** | 统一门户 Lint + Build |
| **code-quality** | flake8 关键错误检查 |
| **proxy-test** | MidScene 代理 Jest 测试 |

### CD 部署阶段

- **触发**: 所有 CI 测试通过 + push 到 master
- **流程**: 构建代理包 → 构建前端 → rsync 到腾讯云 → 执行部署脚本
- **安全**: 备份旧版本 → 部署 → 健康检查 → 失败自动回滚

---

## 常见开发任务

### 新增 API 端点 (Intent-Tester)

1. 在 `tools/intent-tester/backend/api/` 中创建或修改 Blueprint
2. 编写测试: `tools/intent-tester/tests/test_<module>.py`
3. 运行测试: `pytest tools/intent-tester/tests/ -v`
4. 部署验证: `./scripts/dev/deploy-dev.sh`

### 新增 React 组件 (New-Agents)

1. 在 `tools/new-agents/frontend/src/components/` 创建 `.tsx` 文件
2. 编写测试: `src/components/__tests__/<Component>.test.tsx`
3. 运行测试: `cd tools/new-agents/frontend && npm test`

### 新增工作流 (New-Agents)

1. 在 `core/prompts/` 创建新的 prompt 目录
2. 在 `core/workflows.ts` 添加工作流定义
3. 在 `core/config/agentWorkflows.ts` 关联到智能体
4. 添加对应的测试用例

### 修改数据库模型

1. 修改 `models.py` 中的 SQLAlchemy 模型
2. 更新对应的 `to_dict()` 和 `from_dict()` 方法
3. 编写迁移脚本（如需）
4. 测试环境使用 SQLite，生产需手动迁移
