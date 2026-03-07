# new-agents 模块重构计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重构 `new-agents` 模块，解决架构不一致（引入 Flask 工厂模式）、消除反模式（裸 except）并提升安全性（移除 localStorage 的 apiKey）。

**Architecture:** 将 `new-agents-backend` 从全局 app 实例迁移为工厂模式（`create_app()`），并统一使用 `Flask-SQLAlchemy` 进行 Session 管理。前端将 `apiKey` 的持久化从 `localStorage` 回退到非持久化状态（或仅在当前会话保存）。合并或重构 `models.py` 以消除重复的序列化逻辑。

**Tech Stack:** Python, Flask, Flask-SQLAlchemy, pytest, TypeScript, React, Zustand

---

### Task 1: 初始化 db 对象并修改 models.py

为了与 `intent-tester` 保持一致，需要使用 `Flask-SQLAlchemy` 的 `db` 实例，并给所有模型添加一致的继承。

**Files:**
- Modify: `tools/new-agents/backend/models.py`
- Modify: `tools/new-agents/backend/requirements.txt`

**Step 1: 安装依赖 (在 requirements.txt 中补全)**
```text
Flask-SQLAlchemy==3.1.1
```

**Step 2: 修改 models.py 并编写测试**
此时我们可以暂时不修改测试，仅完成模型的迁移。
首先在 `models.py` 顶部实例化 db:

```python
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# 替换 base 为 db.Model
class LlmConfig(db.Model):
    __tablename__ = 'llm_config'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # ... 其他字段保持原样
    
    def to_dict(self):
        return {
            'id': self.id,
            'config_key': self.config_key,
            'base_url': self.base_url,
            'model': self.model,
            'description': self.description
            # 同样不返回 api_key
        }
```

删除原有的 `get_engine`, `get_session`, `Base` 声明等逻辑。

**Step 3: Commit**
```bash
git add tools/new-agents/backend/models.py tools/new-agents/backend/requirements.txt
git commit -m "refactor(new-agents): migrate models to Flask-SQLAlchemy"
```

---

### Task 2: 改造 app.py 支持应用工厂模式

**Files:**
- Modify: `tools/new-agents/backend/app.py`
- Modify: `tools/new-agents/backend/tests/test_api.py`

**Step 1: 重构 `app.py` 中的 `create_app`**

```python
import os
import json
from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS
from models import db, LlmConfig
from config import Config
from openai import OpenAI

def create_app(test_config=None):
    app = Flask(__name__)
    CORS(app)
    
    if test_config is None:
        app.config.from_object(Config)
    else:
        app.config.from_mapping(test_config)
        
    db.init_app(app)
    
    # 将原有路由包装进 init_routes() 并调用
    init_routes(app)
    
    return app

def init_routes(app):
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "ok", "service": "new-agents-backend"})
    
    @app.route('/api/config', methods=['GET'])
    def get_config():
        try:
            config = LlmConfig.query.filter_by(config_key='default').first()
            if not config:
                return jsonify({"hasDefault": False})
            return jsonify({
                "hasDefault": True,
                **config.to_dict()
            })
        except Exception as e:
            app.logger.error(f"Error getting config: {e}")
            return jsonify({"error": str(e)}), 500
            
    # ... 将原有 /api/chat/stream 的逻辑移入，替换 get_session() 为 LlmConfig.query
```

**Step 2: 修正 `test_api.py` 中的 client fixture**

```python
# test_api.py
@pytest.fixture
def app():
    from app import create_app
    from models import db
    import tempfile
    
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })

    with app.app_context():
        db.create_all()
        yield app

    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()
```

**Step 3: 运行测试**
Run: `cd tools/new-agents/backend && pytest tests/test_api.py`
Expected: PASS

**Step 4: Commit**
```bash
git add tools/new-agents/backend/app.py tools/new-agents/backend/tests/test_api.py
git commit -m "refactor(new-agents): convert to application factory pattern"
```

---

### Task 3: 修复 gunicorn 的启动方式和剩余测试文件

**Files:**
- Modify: `tools/new-agents/backend/docker/Dockerfile`
- Modify: `tools/new-agents/backend/tests/test_chat_history.py`
- Modify: `tools/new-agents/backend/tests/test_error_handling.py`

**Step 1: 修复 Dockerfile**

```dockerfile
# tools/new-agents/backend/docker/Dockerfile 的最后一行改为:
CMD ["gunicorn", "-c", "docker/gunicorn.conf.py", "app:create_app()"]
```

**Step 2: 更新剩余测试文件的 fixtures (`test_chat_history.py` / `test_error_handling.py`)**
将原有的 `get_session` 及其导入方式，全部改为依赖工厂生成的 `app` 和 `db.session`。参考 Task 2 Step 2 的 `app` fixture。

**Step 3: 运行所有测试**
Run: `cd tools/new-agents/backend && pytest`
Expected: PASS

**Step 4: Commit**
```bash
git add tools/new-agents/backend/docker/Dockerfile tools/new-agents/backend/tests/
git commit -m "build(new-agents): update Docker CMD and fix remaining tests"
```

---

### Task 4: 清除所有后端的裸 `except:`

**Files:**
*此任务目前属于 `intent-tester` 的范畴，但根据需要，我们也可以一并清理。鉴于指令要求 “intent tester 部分已经比较稳定了，我们不去重构他们”，我们可以跳过此步骤，或者仅清理新出现的 `new-agents-backend` 相关的坏代码（目前 new-agents 中只有一个 `except Exception as e:`）。*
=> **Skipped 按照用户要求跳过 intent-tester 重构。**

---

### Task 5: 修复前端 Store 中 API Key 的不安全持久化

**Files:**
- Modify: `tools/new-agents/frontend/src/store.ts`

**Step 1: 修改 partialize 函数，剔除 `apiKey`**

```typescript
// tools/new-agents/frontend/src/store.ts
// 在 createJSONStorage 所在的 persist 选项中更新:

partialize: (state) => ({
    chatHistory: state.chatHistory,
    // 移除 apiKey: state.apiKey,
    workflow: state.workflow,
    stageIndex: state.stageIndex,
    lastAnalyzedIndex: state.lastAnalyzedIndex,
    stageArtifacts: state.stageArtifacts
}),
```

**Step 2: 运行前端测试**
Run: `cd tools/new-agents/frontend && npm run test`
Expected: PASS (测试会检测 store 的清理逻辑，不受 apiKey 持久化影响)

**Step 3: Commit**
```bash
git add tools/new-agents/frontend/src/store.ts
git commit -m "fix(new-agents-frontend): remove apiKey from local storage persistence"
```

---

### Task 6: 清理 shared 模块中的闲置 `db`

**Files:**
- Modify: `tools/shared/database/__init__.py`
- Modify: `tools/shared/__init__.py`

**Step 1: 移除未使用的 `db = SQLAlchemy()`**

在 `tools/shared/database/__init__.py` 中，删除:
```python
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
```

在 `tools/shared/__init__.py` 中，删除对 `db` 的导入和暴露：
```python
# 修改前：from .database import db, get_database_config
# 修改后：
from .database import get_database_config
```

**Step 2: 确认无其它依赖**
Run: `grep -r "from shared import db" tools/`
Expected: 无结果（因为 intent-tester 重新定义了，new-agents 之前没用 shared）

**Step 3: Commit**
```bash
git add tools/shared/
git commit -m "refactor(shared): remove unused global db instance"
```
