# 项目源码分析 (Source Tree Analysis)

> **生成日期**: {{date}}
> **分析范围**: 核心工具模块 (`tools/`)

## 1. 目录结构总览

AI4SE 采用模块化单体 (Modular Monorepo) 结构，所有核心业务逻辑集中在 `tools/` 目录下。

```bash
AI4SE/
├── tools/
│   ├── ai-agents/            # [Backend] AI 智能体服务
│   │   ├── backend/          # Flask 应用核心 logic
│   │   ├── frontend/         # React 前端源码
│   │   └── docker/           # 容器化配置
│   ├── intent-tester/        # [Web + Proxy] 意图测试工具
│   │   ├── backend/          # Flask 后端 & API
│   │   ├── browser-automation/ # MidScene Server (Node.js 本地代理)
│   │   └── midscene_framework/ # Python 测试框架封装
│   ├── frontend/             # [Web] 统一门户前端 (React)
│   │   ├── src/              # 组件与页面源码
│   │   └── dist/             # 构建产物 (生产环境部署)
│   └── shared/               # [Lib] 共享工具库
│       ├── config/           # 统一配置管理
│       └── database/         # 数据库连接池
```

---

## 2. 关键模块详解

### 2.1 AI 智能体 service (`tools/ai-agents`)

负责提供基于 Google ADK 的智能体对话能力。

- **App 入口**: `backend/app.py` - Flask 应用工厂，注册蓝图，集成 React 静态资源。
- **Core Logic**: `backend/agents/` - 包含 `alex` (需求分析) 和 `lisa` (测试策略) 两个智能体的核心逻辑。
- **API Layer**: `backend/api/` - 处理会话管理、消息流式传输 (SSE) 的 REST 接口。
- **Frontend**: `frontend/` - 独立的 React 应用，构建后由 Flask 或 Nginx 提供服务。

### 2.2 意图测试工具 (`tools/intent-tester`)

负责自然语言驱动的端到端测试，采用典型的 C/S 架构，但特殊点在于 Client 是运行在用户本地的代理。

- **Server Side** (`backend/`):
  - `views.py` & `api/`: 提供 Web 界面和用例管理 API。
  - `models/`: 定义测试用例 (`TestCase`) 和执行记录 (`Execution`) 的数据模型。
- **Client Side** (`browser-automation/`):
  - `midscene_server.js`: **关键组件**。运行在用户本地的 Node.js 代理，通过 WebSocket 接收服务端指令，调用 Playwright 控制本地浏览器。

### 2.3 统一门户前端 (`tools/frontend`)

基于 React + Vite + Tailwind CSS 的现代化前端应用，作为整个平台的统一入口。

- **Src Structure**:
  - `pages/Home/`: 落地页组件 (Hero, Features, UseCases)。
  - `pages/Profile/`: 用户个人中心。
  - `components/`: 通用 UI 组件 (Navbar, Footer, Button)。
- **Build Output**: `dist/` - 构建后的静态资源，生产环境中直接挂载到 Nginx 容器。

### 2.4 共享库 (`tools/shared`)

防止代码重复的通用基础设施。

- `config/__init__.py`: 集中管理环境变量 (DB_URL, OPENAI_KEY 等)，确保所有服务配置一致。
- `database/__init__.py`: 统一的 SQLAlchemy 配置和连接工厂。

---

## 3. 核心文件及其职责

| 路径 | 类型 | 职责 |
|---|---|---|
| `tools/ai-agents/backend/app.py` | Python Script | AI Agents 服务的启动入口和配置中心 |
| `tools/intent-tester/browser-automation/midscene_server.js` | Node Script | **核心**：本地代理服务器，连接云端服务与本地浏览器 |
| `nginx/nginx.conf` | Config | 全局反向代理，处理 `/ai-agents` 和 `/intent-tester` 的路由分发 |
| `docker-compose.prod.yml` | Config | 生产环境编排，定义服务依赖、网络和 Volume 挂载 (包含关键的 `dist` 挂载) |

## 4. 跨模块依赖

1. **Shared Config**: 所有 Python 服务都从 `tools/shared/config` 导入配置，确保单一事实来源。
2. **Nginx Routing**: Nginx作为网关，根据 URL 前缀将流量分发到 `ai-agents` 或 `intent-tester` 容器。
3. **Database Sharing**: 多个服务共享同一个 PostgreSQL 实例 (`ai4se` 数据库)，通过 `tools/shared/database` 统一连接。
