# API 接口契约 (API Contracts)

> **生成日期**: {{date}}
> **协议**: HTTP/1.1 REST
> **认证**: Bearer Token (部分接口) / Session

## 1. 意图测试工具 API

Base URL: `/intent-tester/api`

### 测试用例管理

#### 获取用例列表
`GET /testcases`

**Response:**
```json
[
  {
    "id": 1,
    "name": "登录测试",
    "steps_count": 3,
    "last_run": "2025-01-01T12:00:00Z"
  }
]
```

#### 创建测试用例
`POST /testcases`

**Request:**
```json
{
  "name": "Search Test",
  "steps": [
    {"action": "open", "url": "https://google.com"},
    {"action": "type", "selector": "input[name=q]", "value": "test"}
  ]
}
```

### 执行控制

#### 启动执行
`POST /executions/<case_id>/start`

此接口会通过 WebSocket 通知连接的本地 MidScene Server 开始执行任务。

---

## 2. AI 智能体 API

Base URL: `/ai-agents/api`

### 需求分析会话 (Requirements)

#### 创建新会话
`POST /requirements/sessions`

**Request:**
```json
{
  "assistant_type": "alex" // or "lisa"
}
```

#### 发送消息 (流式 V2 - Data Stream Protocol)
`POST /requirements/sessions/<session_id>/messages/v2/stream`

**Request:**
```json
{
  "content": "用户消息"
}
```

**Response:**
Standard Data Stream Protocol (SSE JSON).
Events: `start`, `text-delta`, `tool-call`, `data`, `finish`.

#### 发送消息 (流式 V1 - Deprecated)
`POST /requirements/sessions/<session_id>/messages/stream`
(Legacy custom SSE format)

### AI 配置管理

#### 更新用户配置
`PUT /requirements/configs`

**Request:**
```json
{
  "api_key": "sk-...",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4-turbo"
}
```

---

## 3. 标准响应格式

所有 API 遵循统一的错误响应格式：

```json
{
  "error": "ErrorType",
  "message": "Human readable error details",
  "code": 400
}
```
