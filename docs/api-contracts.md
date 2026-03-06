# API 契约文档

> 生成日期: 2026-03-06 | 扫描级别: Deep Scan

## Intent-Tester API (端口 5001)

基础路径: `/intent-tester/api/`（经 Nginx 路由后 Flask 接收 `/api/`）

### 测试用例 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/testcases` | 获取测试用例列表（支持分页、筛选） |
| POST | `/api/testcases` | 创建测试用例 |
| GET | `/api/testcases/<id>` | 获取单个测试用例详情 |
| PUT | `/api/testcases/<id>` | 更新测试用例 |
| DELETE | `/api/testcases/<id>` | 删除测试用例（软删除） |

#### 测试用例数据结构

```json
{
  "id": 1,
  "name": "登录流程测试",
  "description": "验证用户登录功能",
  "steps": [
    {"action": "goto", "params": {"url": "https://example.com/login"}},
    {"action": "ai_input", "params": {"query": "在用户名输入框输入 test@example.com"}},
    {"action": "ai_tap", "params": {"query": "点击登录按钮"}},
    {"action": "ai_assert", "params": {"assertion": "页面显示欢迎信息"}}
  ],
  "tags": ["login", "smoke"],
  "category": "authentication",
  "priority": 1,
  "is_active": true,
  "execution_count": 5,
  "success_rate": 80.0
}
```

### 执行管理 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/executions` | 获取执行历史列表 |
| GET | `/api/executions/<id>` | 获取执行详情（含步骤） |
| POST | `/api/executions` | 触发新的测试执行 |
| POST | `/api/executions/<id>/stop` | 停止正在运行的执行 |

#### 执行历史数据结构

```json
{
  "execution_id": "uuid-string",
  "test_case_id": 1,
  "test_case_name": "登录流程测试",
  "status": "success",
  "mode": "headless",
  "browser": "chrome",
  "start_time": "2026-03-06T10:00:00.000Z",
  "end_time": "2026-03-06T10:01:30.000Z",
  "duration": 90,
  "steps_total": 4,
  "steps_passed": 4,
  "steps_failed": 0
}
```

### MidScene 集成 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/midscene/execution-start` | 通知 MidScene 开始执行 |
| POST | `/api/midscene/execution-result` | 接收 MidScene 执行结果 |

### WebSocket 事件（SocketIO）

| 事件 | 方向 | 说明 |
|------|------|------|
| `execution-start` | Server → Client | 执行开始 |
| `step-start` | Server → Client | 步骤开始 |
| `step-completed` | Server → Client | 步骤完成 |
| `step-failed` | Server → Client | 步骤失败 |
| `execution-completed` | Server → Client | 执行完成 |
| `execution-stopped` | Server → Client | 执行停止 |
| `screenshot-taken` | Server → Client | 截图完成 |
| `log-message` | Server → Client | 日志消息 |

### 其他 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/proxy/download` | 下载 MidScene 代理包 |

---

## MidScene Server API (端口 3001，本地运行)

独立的 Node.js Express 服务，由 Python 后端通过 HTTP 调用。

### AI 浏览器操作

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/goto` | 导航到 URL |
| POST | `/ai-tap` | AI 识别并点击元素 |
| POST | `/ai-input` | AI 识别并输入文本 |
| POST | `/ai-query` | AI 查询页面数据（返回 JSON） |
| POST | `/ai-assert` | AI 断言验证 |
| POST | `/ai-action` | AI 执行复合操作 |
| POST | `/ai-wait-for` | AI 等待条件满足 |
| POST | `/ai-scroll` | AI 滚动页面 |
| POST | `/screenshot` | 截取页面截图 |
| GET | `/page-info` | 获取页面信息 |

### 测试执行管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/execute-testcase` | 执行完整测试用例 |
| GET | `/api/execution-status/:id` | 获取执行状态 |
| GET | `/api/execution-report/:id` | 获取执行报告 |
| GET | `/api/executions` | 获取执行列表 |
| POST | `/api/stop-execution/:id` | 停止执行 |
| POST | `/set-browser-mode` | 设置浏览器模式 (headless/headed) |
| POST | `/cleanup` | 清理浏览器资源 |

---

## New Agents Backend API (端口 5002)

基础路径: `/new-agents/api/`（经 Nginx 路由重写为 `/api/`）

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/health` | 健康检查 | 无 |
| GET | `/api/config` | 获取默认 LLM 配置（不含 API Key） | 无 |
| POST | `/api/chat/stream` | SSE 流式聊天代理 | 无 |

### GET `/api/config` 响应

```json
// 有默认配置时:
{
  "hasDefault": true,
  "config": {
    "config_key": "default",
    "base_url": "https://api.example.com/v1",
    "model": "gpt-4o",
    "description": "默认配置"
  }
}

// 无默认配置时:
{
  "hasDefault": false
}
```

### POST `/api/chat/stream` 请求

```json
{
  "messages": [
    {"role": "system", "content": "你是测试专家 Lisa..."},
    {"role": "user", "content": "帮我设计一个登录功能的测试方案"}
  ],
  "model": "gpt-4o",
  "temperature": 0.7
}
```

### SSE 响应格式

```text
data: {"choices":[{"delta":{"content":"好的"},"index":0}]}

data: {"choices":[{"delta":{"content":"，让我"},"index":0}]}

data: [DONE]
```

错误时：
```text
data: {"error": "No default LLM configuration found", "code": "NO_CONFIG"}
```

---

## 健康检查端点汇总

| 服务 | 端点 | 预期响应 |
|------|------|----------|
| Nginx 网关 | `http://localhost/health` | 200 OK |
| Intent-Tester | `http://localhost:5001/health` | `{"status": "ok"}` |
| New Agents Backend | `http://localhost:5002/api/health` | `{"status": "ok", "service": "new-agents-backend"}` |
| MidScene Server | `http://localhost:3001/health` | 200 OK |
