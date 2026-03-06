# Lisa Agent 入口对接 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将现有 AI 智能体入口页面中的 Lisa 卡片点击行为改为跳转到 `/new-agents/` 路径下独立部署的新 Lisa Agent 纯前端应用。

**Architecture:** 新 Agent 是一个独立的 Vite + React 纯前端项目，通过 Docker 容器内的 Nginx serve 构建产物。Nginx 网关添加 `/new-agents/` 路由将请求代理到该容器。现有入口 `CompactApp` 仅修改 Lisa 卡片的点击行为为 URL 跳转。

**Tech Stack:** Vite, React, TypeScript, Tailwind v4, Docker (nginx:alpine), Nginx 反向代理

---

### Task 1: 修改 Vite `base` 配置

**Files:**
- Modify: `tools/new-agents/vite.config.ts:8-26`

**Step 1: 修改 `vite.config.ts`，添加 `base: '/new-agents/'`**

在 `return { ... }` 的最开头添加 `base` 配置：

```typescript
return {
    base: '/new-agents/',
    plugins: [react(), tailwindcss()],
    // ... 其余不变
};
```

**Step 2: 本地验证配置无误**

Run: `cd tools/new-agents && npm run build`
Expected: 构建成功，`dist/` 目录中所有资源路径以 `/new-agents/` 开头

**Step 3: Commit**

```bash
git add tools/new-agents/vite.config.ts
git commit -m "feat(new-agents): set vite base path to /new-agents/"
```

---

### Task 2: 创建 Dockerfile 用于新 Agent

**Files:**
- Create: `tools/new-agents/docker/Dockerfile`
- Create: `tools/new-agents/docker/nginx.conf`

**Step 1: 创建 Nginx 配置文件**

为了避免 `alias` 与 `try_files` 的经典兼容性问题，我们直接使用带目录层级的静态文件结构。创建 `tools/new-agents/docker/nginx.conf`：

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;

    location /new-agents/ {
        try_files $uri $uri/ /new-agents/index.html;
    }

    location /new-agents/assets/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

**Step 2: 创建多阶段 Dockerfile**

创建 `tools/new-agents/docker/Dockerfile`，注意我们将构建产物放入 `/usr/share/nginx/html/new-agents` 目录：

```dockerfile
# syntax=docker/dockerfile:1

# === 阶段一：构建 ===
FROM node:20-alpine AS builder
WORKDIR /app

# 复制依赖清单并安装
COPY tools/new-agents/package.json tools/new-agents/package-lock.json ./
RUN npm ci

# 复制源码并构建
COPY tools/new-agents/ ./
RUN npm run build

# === 阶段二：运行 ===
FROM nginx:alpine
# 复制 Nginx 配置
COPY tools/new-agents/docker/nginx.conf /etc/nginx/conf.d/default.conf
# 复制构建产物到 new-agents 子目录
COPY --from=builder /app/dist /usr/share/nginx/html/new-agents
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Step 3: Commit**

```bash
git add tools/new-agents/docker/
git commit -m "feat(new-agents): add Dockerfile and nginx config safely"
```

---

### Task 3: 添加 Docker Compose 服务

**Files:**
- Modify: `docker-compose.dev.yml:103-121`

**Step 1: 在 `ai-agents` 和 `nginx` 服务之间添加 `new-agents` 服务**

在 `ai-agents` 服务块结束后（约第 103 行之后），`nginx` 服务块之前，插入：

```yaml
  # 新 Agent（Lisa 纯前端版）
  new-agents:
    build:
      context: .
      dockerfile: tools/new-agents/docker/Dockerfile
    container_name: ai4se-new-agents
    restart: unless-stopped
    networks:
      - ai4se-network
```

**Step 2: 在 `nginx` 的 `depends_on` 中添加 `new-agents`**

```yaml
  nginx:
    # ... 原有配置不变
    depends_on:
      - intent-tester
      - ai-agents
      - new-agents  # 新增
```

**Step 3: Commit**

```bash
git add docker-compose.dev.yml
git commit -m "feat(infra): add new-agents service to docker-compose"
```

---

### Task 4: 配置 Nginx 反向代理路由

**Files:**
- Modify: `nginx/nginx.conf:35-37`（添加 upstream）
- Modify: `nginx/nginx.conf:106-113`（添加 location 块）

**Step 1: 添加 upstream 定义**

在 `upstream ai_agents { ... }` 块之后（约第 37 行后）添加：

```nginx
    upstream new_agents {
        server new-agents:80;
    }
```

**Step 2: 添加 location 路由块**

在 `# AI 智能体静态资源` location 块之后（约第 113 行后），`# 健康检查` 之前，添加：

```nginx
        # 新 Agent (Lisa 纯前端版)
        location /new-agents/ {
            proxy_pass http://new_agents;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
```

**Step 3: Commit**

```bash
git add nginx/nginx.conf
git commit -m "feat(infra): add /new-agents/ route to nginx config"
```

---

### Task 5: 修改入口页面 Lisa 卡片跳转行为

**Files:**
- Modify: `tools/ai-agents/frontend/CompactApp.tsx:113-122`

**Step 1: 修改 `handleSelectAssistant` 函数**

将原来的 `handleSelectAssistant` 替换为：

```typescript
    const handleSelectAssistant = (id: AssistantId) => {
        // Lisa 跳转到新的独立 Agent 页面
        if (id === AssistantId.Lisa) {
            window.location.href = '/new-agents/';
            return;
        }
        
        setSelectedAssistantId(id);
        // 重置状态
        setWorkflowProgress(null);
        setArtifacts({});
        setStructuredArtifacts({});
        setStreamingArtifactKey(null);
        setStreamingArtifactContent('');
        setSelectedStageId(null);
    };
```

**Step 2: Commit**

```bash
git add tools/ai-agents/frontend/CompactApp.tsx
git commit -m "feat(ai-agents): redirect Lisa card to /new-agents/"
```

---

### Task 6: 更新健康检查输出

**Files:**
- Modify: `scripts/dev/deploy-dev.sh:144-148`

**Step 1: 在健康检查输出中添加入口提示**

在 `echo "   🧪 意图测试: http://localhost/intent-tester"` 之后添加：

```bash
        echo "   🆕 新 Agent: http://localhost/new-agents"
```

(包含约第 147 行和第 171 行两个位置)

*注意：我们不修改 `JS_PROJECTS`，新 Agent 的打包完全交由 Docker 在 build 阶段处理，加速本地流程。*

**Step 2: Commit**

```bash
git add scripts/dev/deploy-dev.sh
git commit -m "feat(infra): add new-agents to health output in deploy script"
```

---

### Task 7: 端到端验证

**Step 1: 运行部署脚本**

```bash
bash scripts/dev/deploy-dev.sh
```

Expected: 所有服务启动成功，健康检查通过，输出中包含 `🆕 新 Agent: http://localhost/new-agents`

**Step 2: 浏览器验证 — 直接访问新 Agent**

打开 `http://localhost/new-agents/`
Expected: 新 Agent 主页面正常加载，显示 Lisa 测试专家界面

**Step 3: 浏览器验证 — 从入口页面跳转**

1. 打开 `http://localhost/ai-agents/`
2. 点击 Lisa 卡片
Expected: 页面跳转到 `http://localhost/new-agents/`，显示新 Agent 主页面

**Step 4: 浏览器验证 — Alex 不受影响**

1. 返回 `http://localhost/ai-agents/`
2. 点击 Alex 卡片
Expected: 进入原有的 Alex 聊天界面，行为不变
