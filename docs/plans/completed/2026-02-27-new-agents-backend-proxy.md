# New-Agents 后端代理服务实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 new-agents 构建独立的 Flask 后端代理服务，系统内置的 LLM API Key 存在数据库中（手动写入一次），前端通过后端代理转发请求，Key 不暴露给浏览器。用户也可配置自己的 Key 走前端直连。

**Architecture:** 新增 Flask 后端服务 `new-agents-backend`，复用已有 PostgreSQL。后端提供两个核心 API：`GET /api/config`（返回模型配置，不含 Key）和 `POST /api/chat/stream`（SSE 流式代理转发）。前端双模式：无 Key 走后端代理，有 Key 走前端直连。API Key 直接手动写入本地和线上数据库，一次性操作。

**Tech Stack:** Python 3.11 / Flask / Gunicorn / PostgreSQL / SQLAlchemy / SSE / OpenAI Python SDK

---

## 架构总览

```
浏览器 (React 前端)
  ├── 用户有自己的 Key → 前端直连 LLM（现有逻辑不变）
  └── 用户无 Key → POST /new-agents/api/chat/stream → 后端代理
                                    │
                              Nginx (:80)
                                    │
                    new-agents-backend (:5002)
                      ├── 从 PostgreSQL 读取系统 Key
                      └── 转发请求到 LLM Provider
```

## 数据库表设计

复用已有 PostgreSQL（`ai4se` 库），新增 `llm_config` 表：

```sql
CREATE TABLE IF NOT EXISTS llm_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(64) UNIQUE NOT NULL,
    api_key TEXT NOT NULL,
    base_url TEXT NOT NULL,
    model VARCHAR(128) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

Key 直接明文存数据库，手动 INSERT 一次。数据库不在代码仓库里，不会泄露。

---

### Task 1: 后端项目骨架与数据库模型

**Files:**
- Create: `tools/new-agents/backend/requirements.txt`
- Create: `tools/new-agents/backend/config.py`
- Create: `tools/new-agents/backend/models.py`
- Create: `tools/new-agents/backend/app.py`

**Step 1: 创建 requirements.txt**

```txt
Flask==3.0.3
flask-cors==4.0.1
gunicorn==22.0.0
psycopg2-binary==2.9.9
SQLAlchemy==2.0.35
openai==1.58.1
python-dotenv==1.0.1
```

**Step 2: 创建 config.py**

```python
import os

class Config:
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        'postgresql://ai4se_user:change_me_in_production@postgres:5432/ai4se'
    )
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
```

**Step 3: 创建 models.py**

```python
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from config import Config

Base = declarative_base()

class LlmConfig(Base):
    __tablename__ = 'llm_config'

    id = Column(Integer, primary_key=True)
    config_key = Column(String(64), unique=True, nullable=False)
    api_key = Column(Text, nullable=False)
    base_url = Column(Text, nullable=False)
    model = Column(String(128), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

def get_engine():
    return create_engine(Config.DATABASE_URL)

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
```

**Step 4: 创建 app.py**

```python
import json
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from models import init_db, get_session, LlmConfig
from config import Config
from openai import OpenAI

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

with app.app_context():
    init_db()

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "new-agents-backend"})

@app.route('/api/config', methods=['GET'])
def get_default_config():
    """获取系统默认模型配置（不返回 API Key）"""
    session = get_session()
    try:
        config = session.query(LlmConfig).filter_by(
            config_key='default', is_active=True
        ).first()
        if not config:
            return jsonify({"hasDefault": False}), 200
        return jsonify({
            "hasDefault": True,
            "baseUrl": config.base_url,
            "model": config.model,
            "description": config.description
        })
    finally:
        session.close()

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """SSE 流式代理转发 LLM 请求"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体为空"}), 400

    messages = data.get('messages', [])
    model_override = data.get('model')
    temperature = data.get('temperature', 0.7)

    if not messages:
        return jsonify({"error": "messages 不能为空"}), 400

    session = get_session()
    try:
        config = session.query(LlmConfig).filter_by(
            config_key='default', is_active=True
        ).first()
        if not config:
            return jsonify({"error": "系统未配置默认 LLM，请在设置中配置您自己的 API Key"}), 503
        api_key = config.api_key
        base_url = config.base_url
        default_model = config.model
    finally:
        session.close()

    client = OpenAI(api_key=api_key, base_url=base_url)
    model = model_override or default_model

    def generate():
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=True
            )
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield f"data: {json.dumps({'content': delta.content})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
```

**Step 5: Commit**

```bash
git add tools/new-agents/backend/
git commit -m "feat(new-agents): add backend proxy service skeleton"
```

---

### Task 2: Docker 化后端服务

**Files:**
- Create: `tools/new-agents/backend/docker/Dockerfile`
- Create: `tools/new-agents/backend/docker/gunicorn.conf.py`
- Modify: `docker-compose.dev.yml`（新增 new-agents-backend 服务 + nginx depends_on）
- Modify: `docker-compose.prod.yml`（同上）

**Step 1: 创建 gunicorn.conf.py**

```python
bind = "0.0.0.0:5002"
workers = 2
timeout = 300
keepalive = 5
worker_class = "gthread"
threads = 4
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

**Step 2: 创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY tools/new-agents/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tools/new-agents/backend/ .

EXPOSE 5002

CMD ["gunicorn", "-c", "docker/gunicorn.conf.py", "app:app"]
```

**Step 3: 修改 docker-compose.dev.yml**

在 `new-agents` 服务后新增：

```yaml
  new-agents-backend:
    build:
      context: .
      dockerfile: tools/new-agents/backend/docker/Dockerfile
    container_name: ai4se-new-agents-backend
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-ai4se_user}:${DB_PASSWORD:-change_me_in_production}@postgres:5432/ai4se
    ports:
      - "5002:5002"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - ai4se-network
```

nginx 的 depends_on 加上 `- new-agents-backend`。

**Step 4: 修改 docker-compose.prod.yml — 同理**

```yaml
  new-agents-backend:
    build:
      context: .
      dockerfile: tools/new-agents/backend/docker/Dockerfile
    container_name: ai4se-new-agents-backend-prod
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-ai4se_user}:${DB_PASSWORD:-change_me_in_production}@postgres:5432/ai4se
    depends_on:
      postgres:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    networks:
      - ai4se-network
```

nginx depends_on 加上 `- new-agents-backend`。

**Step 5: 验证构建**

Run: `docker-compose -f docker-compose.dev.yml build new-agents-backend`
Expected: 构建成功

**Step 6: Commit**

```bash
git add tools/new-agents/backend/docker/ docker-compose.dev.yml docker-compose.prod.yml
git commit -m "feat(new-agents): dockerize backend proxy service"
```

---

### Task 3: Nginx 路由 + 手动写入数据库

**Files:**
- Modify: `nginx/nginx.conf`（新增 upstream + location）

**Step 1: 在 upstream 区域新增（第 37 行后）**

```nginx
    upstream new_agents_backend {
        server new-agents-backend:5002;
    }
```

**Step 2: 在 `/new-agents/` location 之前新增 API 路由**

```nginx
        # 新 Agent 后端 API（LLM 代理）- 必须在前端路由之前
        location /new-agents/api/ {
            rewrite ^/new-agents/api/(.*) /api/$1 break;
            proxy_pass http://new_agents_backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Connection '';
            proxy_buffering off;
            proxy_cache off;
            proxy_read_timeout 300s;
            proxy_connect_timeout 10s;
            chunked_transfer_encoding on;
        }
```

**Step 3: 启动服务后，手动写入数据库配置 — 一次性操作**

本地环境：

```bash
docker exec -it ai4se-db psql -U ai4se_user -d ai4se -c "
INSERT INTO llm_config (config_key, api_key, base_url, model, description)
VALUES (
  'default',
  '你的实际API-Key',
  'https://generativelanguage.googleapis.com/v1beta/openai/',
  'gemini-2.5-flash',
  '系统默认配置'
) ON CONFLICT (config_key) DO UPDATE SET
  api_key = EXCLUDED.api_key,
  base_url = EXCLUDED.base_url,
  model = EXCLUDED.model,
  updated_at = NOW();
"
```

线上环境（SSH 到服务器后）：

```bash
docker exec -it ai4se-db-prod psql -U ai4se_user -d ai4se -c "
INSERT INTO llm_config (config_key, api_key, base_url, model, description)
VALUES (
  'default',
  '你的实际API-Key',
  'https://generativelanguage.googleapis.com/v1beta/openai/',
  'gemini-2.5-flash',
  '系统默认配置'
) ON CONFLICT (config_key) DO UPDATE SET
  api_key = EXCLUDED.api_key,
  base_url = EXCLUDED.base_url,
  model = EXCLUDED.model,
  updated_at = NOW();
"
```

**Step 4: 验证**

Run: `curl http://localhost/new-agents/api/health`
Expected: `{"status":"ok","service":"new-agents-backend"}`

Run: `curl http://localhost/new-agents/api/config`
Expected: `{"hasDefault":true,"baseUrl":"...","model":"gemini-2.5-flash",...}`

**Step 5: Commit**

```bash
git add nginx/nginx.conf
git commit -m "feat(nginx): add routing for new-agents-backend API proxy"
```

---

### Task 4: 前端改造 — 双模式 LLM 调用

**Files:**
- Modify: `tools/new-agents/src/store.ts`（新增 `isUserConfigured` 状态 + `resetToSystemConfig` 方法）
- Modify: `tools/new-agents/src/llm.ts`（核心：新增后端代理流式调用）
- Modify: `tools/new-agents/src/components/SettingsModal.tsx`（UI 提示 + 恢复默认按钮）

**Step 1: 修改 store.ts**

在 AppState interface 新增：

```typescript
isUserConfigured: boolean;
setIsUserConfigured: (val: boolean) => void;
resetToSystemConfig: () => void;
```

初始值：`apiKey: ''`, `baseUrl: ''`, `model: ''`, `isUserConfigured: false`

`setApiKey` 改为：当 key 非空时同时设 `isUserConfigured: true`。

`resetToSystemConfig` 方法：清空 apiKey/baseUrl/model，设 `isUserConfigured: false`。

persist 的 partialize 加上 `isUserConfigured`。

**Step 2: 修改 llm.ts — 新增后端代理调用**

新增函数 `generateResponseStreamViaProxy`：

```typescript
async function* generateResponseStreamViaProxy(
  messages: OpenAI.Chat.Completions.ChatCompletionMessageParam[],
  signal?: AbortSignal
) {
  const response = await fetch('/new-agents/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, temperature: 0.7 }),
    signal
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.error || '后端代理请求失败');
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const payload = line.slice(6).trim();
      if (payload === '[DONE]') return;
      try {
        const { content, error } = JSON.parse(payload);
        if (error) throw new Error(error);
        if (content) yield content;
      } catch {}
    }
  }
}
```

修改 `generateResponseStream` 主函数入口：

```typescript
const { isUserConfigured, apiKey } = state;

if (isUserConfigured && apiKey) {
  // 走现有的前端直连逻辑（OpenAI SDK）
  // ... 现有代码不变 ...
} else {
  // 走后端代理
  const proxyMessages = [
    { role: 'system', content: systemInstruction },
    ...chatHistory.map(...),
    { role: 'user', content: buildContentWithAttachments(userMessage, attachments) }
  ];

  let fullText = '';
  for await (const chunk of generateResponseStreamViaProxy(proxyMessages, signal)) {
    fullText += chunk;
    // 复用现有的 CHAT/ARTIFACT/ACTION 解析逻辑
    // ... 和现在 for await 循环体内的解析逻辑一样 ...
    yield { chatResponse, newArtifact, action, hasArtifactUpdate };
  }
}
```

**Step 3: 修改 SettingsModal.tsx**

在"模型配置"区域顶部加提示：

```tsx
<div className="rounded-lg border border-blue-900/30 bg-blue-900/10 p-3 mb-4">
  <p className="text-xs text-blue-300">
    💡 系统已内置默认模型，无需配置即可直接使用。
    如需使用自己的 API Key，请在下方填写。
  </p>
</div>
```

新增"恢复系统默认"按钮，调用 `resetToSystemConfig()`。

**Step 4: 验证构建**

Run: `cd tools/new-agents && npm run lint && npm run build`
Expected: 无错误

**Step 5: Commit**

```bash
git add tools/new-agents/src/
git commit -m "feat(new-agents): dual-mode LLM - backend proxy default, frontend direct with user key"
```

---

### Task 5: 部署配置更新与集成测试

**Files:**
- Modify: `scripts/test/test-local.sh`（可选：新增 backend lint 检查）
- Modify: `scripts/health/health_check.sh`（新增 backend 健康检查端点）

**Step 1: health_check.sh 新增**

```bash
check_endpoint "http://localhost:5002/api/health" "new-agents-backend"
```

**Step 2: 启动完整本地环境**

Run: `bash scripts/dev/deploy-dev.sh`
Expected: 所有服务启动成功

**Step 3: 手动写入数据库（用你的实际 Key）**

执行 Task 3 Step 3 中的 SQL INSERT 命令。

**Step 4: 浏览器端到端验证**

1. 打开 `http://localhost/new-agents/` → 选 Lisa → 选测试设计
2. 不配置任何 Key，直接发消息
3. 验证：等待动画正常 → 流式文字正常输出
4. 打开设置，配置自己的 Key，再发消息验证前端直连正常

**Step 5: 运行测试**

Run: `bash scripts/test/test-local.sh`
Expected: 全部通过

**Step 6: Commit + Push**

```bash
git add .
git commit -m "feat(new-agents): complete backend proxy integration"
git push origin master
```

---

## 安全清单

| 检查项 | 状态 |
|--------|------|
| API Key 不在代码仓库中 | ✅ 手动 INSERT 到数据库 |
| 数据库数据不在 Git 中 | ✅ Docker Volume，不提交 |
| 前端无法获取系统 Key | ✅ `/api/config` 不返回 Key |
| `.env` 被 gitignore | ✅ 已在 `.gitignore` |
| 用户可覆盖系统配置 | ✅ 前端设置 → isUserConfigured |
