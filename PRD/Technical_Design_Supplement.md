# AI测试GUI系统 - 技术设计补充文档

## 📋 文档信息

| 项目名称 | AI测试GUI系统技术设计 |
|---------|---------------------|
| 版本 | v1.0 |
| 创建日期 | 2025-01-13 |
| 关联文档 | AI_Test_GUI_Requirements.md |

## 🏗️ 详细技术架构

### 系统分层架构
```
┌─────────────────────────────────────────┐
│           前端展示层 (React/Vue)          │
├─────────────────────────────────────────┤
│           Web API层 (Flask)             │
├─────────────────────────────────────────┤
│         业务逻辑层 (Python Services)      │
├─────────────────────────────────────────┤
│      AI测试引擎层 (midscene_python.py)   │
├─────────────────────────────────────────┤
│       Node.js服务层 (midscene_server.js) │
├─────────────────────────────────────────┤
│         数据持久层 (SQLite + Files)      │
└─────────────────────────────────────────┘
```

### 核心模块设计

#### 1. 测试用例管理模块 (TestCaseManager)
```python
class TestCaseManager:
    def create_testcase(self, name, description, steps):
        """创建新的测试用例"""
        pass
    
    def update_testcase(self, id, updates):
        """更新测试用例"""
        pass
    
    def delete_testcase(self, id):
        """删除测试用例"""
        pass
    
    def get_testcase_list(self, filters=None):
        """获取测试用例列表"""
        pass
    
    def search_testcases(self, keyword):
        """搜索测试用例"""
        pass
```

#### 2. 执行引擎模块 (ExecutionEngine)
```python
class ExecutionEngine:
    def execute_single(self, testcase_id):
        """执行单个测试用例"""
        pass
    
    def execute_batch(self, testcase_ids):
        """批量执行测试用例"""
        pass
    
    def stop_execution(self, execution_id):
        """停止执行"""
        pass
    
    def get_execution_status(self, execution_id):
        """获取执行状态"""
        pass
```

#### 3. 自然语言解析模块 (NLPParser)
```python
class NLPParser:
    def parse_step(self, natural_language):
        """解析自然语言为测试步骤"""
        pass
    
    def validate_syntax(self, text):
        """验证语法正确性"""
        pass
    
    def suggest_completion(self, partial_text):
        """提供自动补全建议"""
        pass
    
    def extract_parameters(self, step):
        """提取步骤参数"""
        pass
```

#### 4. 实时通信模块 (WebSocketManager)
```python
class WebSocketManager:
    def broadcast_execution_status(self, status):
        """广播执行状态"""
        pass
    
    def send_debug_info(self, client_id, debug_data):
        """发送调试信息"""
        pass
    
    def handle_client_connection(self, client):
        """处理客户端连接"""
        pass
```

## 🎨 前端架构设计

### 组件层次结构
```
App
├── Layout
│   ├── Header
│   ├── Sidebar
│   └── Footer
├── Pages
│   ├── TestCaseListPage
│   │   ├── TestCaseTable
│   │   ├── SearchBar
│   │   └── FilterPanel
│   ├── TestEditorPage
│   │   ├── StepEditor
│   │   ├── PreviewPanel
│   │   └── TemplateSelector
│   ├── ExecutionPage
│   │   ├── ExecutionConsole
│   │   ├── ProgressIndicator
│   │   └── LogViewer
│   └── ReportPage
│       ├── ReportSummary
│       ├── DetailedResults
│       └── ScreenshotGallery
└── Common
    ├── Modal
    ├── Loading
    └── ErrorBoundary
```

### 状态管理设计 (Redux/Vuex)
```javascript
// 全局状态结构
const globalState = {
  testCases: {
    list: [],
    current: null,
    loading: false,
    error: null
  },
  execution: {
    current: null,
    history: [],
    realTimeData: null
  },
  ui: {
    sidebarCollapsed: false,
    theme: 'light',
    notifications: []
  },
  user: {
    preferences: {},
    settings: {}
  }
};
```

## 🔌 API接口详细设计

### RESTful API规范

#### 测试用例相关接口
```yaml
# 获取测试用例列表
GET /api/v1/testcases
Parameters:
  - page: int (页码)
  - size: int (每页数量)
  - search: string (搜索关键词)
  - tags: string[] (标签筛选)
Response:
  {
    "code": 200,
    "data": {
      "items": [...],
      "total": 100,
      "page": 1,
      "size": 20
    }
  }

# 创建测试用例
POST /api/v1/testcases
Body:
  {
    "name": "登录测试",
    "description": "测试用户登录功能",
    "steps": [...],
    "tags": ["login", "auth"]
  }
```

#### 执行相关接口
```yaml
# 执行测试用例
POST /api/v1/executions
Body:
  {
    "testcase_id": 123,
    "mode": "debug", // normal | debug
    "browser": "chrome"
  }
Response:
  {
    "code": 200,
    "data": {
      "execution_id": "exec_123456",
      "status": "running"
    }
  }
```

### WebSocket事件设计
```javascript
// 客户端监听的事件
const wsEvents = {
  // 执行状态更新
  'execution.status': (data) => {
    // data: { execution_id, status, current_step, progress }
  },
  
  // 实时截图
  'execution.screenshot': (data) => {
    // data: { execution_id, step_index, screenshot_url }
  },
  
  // 调试信息
  'debug.info': (data) => {
    // data: { ai_decision, elements_found, confidence }
  },
  
  // 错误信息
  'execution.error': (data) => {
    // data: { execution_id, error_message, stack_trace }
  }
};
```

## 💾 数据库设计详细

### 完整表结构设计

#### 用户表 (users)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    password_hash VARCHAR(255),
    role VARCHAR(20) DEFAULT 'tester',
    preferences JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 测试用例表 (test_cases) - 扩展版
```sql
CREATE TABLE test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    steps JSON NOT NULL,
    tags VARCHAR(500),
    category VARCHAR(100),
    priority INTEGER DEFAULT 3,
    estimated_duration INTEGER, -- 预估执行时间(秒)
    created_by INTEGER,
    updated_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
);
```

#### 执行历史表 (execution_history) - 扩展版
```sql
CREATE TABLE execution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id VARCHAR(50) UNIQUE NOT NULL,
    test_case_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL, -- running, success, failed, stopped
    mode VARCHAR(20) DEFAULT 'normal', -- normal, debug
    browser VARCHAR(50) DEFAULT 'chrome',
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration INTEGER, -- 实际执行时间(秒)
    steps_total INTEGER,
    steps_passed INTEGER,
    steps_failed INTEGER,
    result_summary JSON,
    screenshots_path TEXT,
    logs_path TEXT,
    error_message TEXT,
    error_stack TEXT,
    executed_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (test_case_id) REFERENCES test_cases(id),
    FOREIGN KEY (executed_by) REFERENCES users(id)
);
```

#### 步骤执行详情表 (step_executions)
```sql
CREATE TABLE step_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id VARCHAR(50) NOT NULL,
    step_index INTEGER NOT NULL,
    step_description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL, -- success, failed, skipped
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration INTEGER,
    screenshot_path TEXT,
    ai_confidence REAL,
    ai_decision JSON,
    error_message TEXT,
    FOREIGN KEY (execution_id) REFERENCES execution_history(execution_id)
);
```

#### 模板表 (templates)
```sql
CREATE TABLE templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    steps_template JSON NOT NULL,
    parameters JSON, -- 模板参数定义
    usage_count INTEGER DEFAULT 0,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_public BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (created_by) REFERENCES users(id)
);
```

### 索引设计
```sql
-- 提高查询性能的索引
CREATE INDEX idx_test_cases_name ON test_cases(name);
CREATE INDEX idx_test_cases_tags ON test_cases(tags);
CREATE INDEX idx_test_cases_created_by ON test_cases(created_by);
CREATE INDEX idx_execution_history_test_case_id ON execution_history(test_case_id);
CREATE INDEX idx_execution_history_status ON execution_history(status);
CREATE INDEX idx_execution_history_start_time ON execution_history(start_time);
CREATE INDEX idx_step_executions_execution_id ON step_executions(execution_id);
```

## 🔧 核心算法设计

### 自然语言解析算法
```python
class NLPStepParser:
    def __init__(self):
        self.action_patterns = {
            'navigate': [r'访问|打开|导航到', r'(https?://\S+)'],
            'input': [r'输入|填写|键入', r'"([^"]+)"', r'在(.+?)中'],
            'click': [r'点击|单击|按', r'(.+?)按钮|(.+?)链接'],
            'assert': [r'验证|检查|确认', r'(.+)'],
            'wait': [r'等待', r'(.+?)加载|(.+?)出现']
        }
    
    def parse(self, natural_text):
        """解析自然语言为结构化步骤"""
        for action, patterns in self.action_patterns.items():
            if self._match_patterns(natural_text, patterns):
                return self._extract_parameters(action, natural_text, patterns)
        
        raise ValueError(f"无法解析的步骤: {natural_text}")
```

### 执行状态管理算法
```python
class ExecutionStateManager:
    def __init__(self):
        self.executions = {}  # execution_id -> ExecutionState
    
    def start_execution(self, testcase, mode='normal'):
        """开始执行测试用例"""
        execution_id = self._generate_execution_id()
        state = ExecutionState(execution_id, testcase, mode)
        self.executions[execution_id] = state
        return execution_id
    
    def update_step_status(self, execution_id, step_index, status, result=None):
        """更新步骤执行状态"""
        if execution_id in self.executions:
            self.executions[execution_id].update_step(step_index, status, result)
            self._notify_clients(execution_id)
```

## 🚀 部署架构设计

### Docker容器化部署
```dockerfile
# Dockerfile
FROM node:16-alpine AS node-builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY --from=node-builder /app/dist ./static
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

### docker-compose配置
```yaml
version: '3.8'
services:
  ai-test-gui:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
      - ./screenshots:/app/screenshots
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=sqlite:///data/app.db
    depends_on:
      - midscene-server
  
  midscene-server:
    build: ./midscene
    ports:
      - "3001:3001"
    environment:
      - NODE_ENV=production
```

---

**文档状态**: 技术设计完成  
**关联文档**: AI_Test_GUI_Requirements.md  
**维护人**: 技术团队  
