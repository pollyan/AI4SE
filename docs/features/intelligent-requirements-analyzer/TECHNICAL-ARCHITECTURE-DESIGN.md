# AI智能需求分析模块完整架构设计文档

## 📋 文档概述

**系统名称**: 智能需求分析模块 (Intelligent Requirements Analyzer)  
**文档版本**: v2.0 (合并完整版)  
**创建日期**: 2024年  
**架构类型**: 全栈应用架构  
**集成目标**: Intent Test Framework  

本文档详细描述了AI智能需求分析模块的完整架构设计，包括技术选型、系统分层、数据模型、API设计、前端架构、用户AI配置管理以及与现有Intent Test Framework的集成方案。

## 🎯 项目背景

### 业务目标
通过引入AI驱动的需求分析功能，提升Intent Test Framework的需求理解和测试用例生成能力，实现从自然语言需求到结构化测试用例的自动化转换。

### 核心价值主张
1. **智能需求理解**: AI自动理解和澄清模糊的需求描述
2. **结构化文档生成**: 自动生成PRD、Epic、Story等标准化文档  
3. **测试用例自动生成**: 基于需求自动创建测试用例框架
4. **迭代式需求优化**: 通过对话持续完善需求质量
5. **用户自主AI配置**: 支持用户配置自己的AI服务和模型

## 🏗️ 架构设计原则

### 🎯 极致BMAD架构理念

#### 核心突破：AI完全自主决策
> **革命性理念**: Web页面仅作为交互媒介，所有业务逻辑、决策判断、任务执行完全由AI通过提示词自主完成

#### 传统架构 vs 极致BMAD架构
```yaml
传统Web架构:
  ❌ 程序代码: if user_choice == "1": load_method_1()
  ❌ 业务逻辑: 硬编码在Python/JavaScript中
  ❌ 决策判断: 由程序员预设的逻辑分支
  ❌ AI角色: 被动的内容生成工具

极致BMAD架构:
  ✅ 提示词驱动: AI自主理解用户意图
  ✅ 业务逻辑: 完全由自然语言描述
  ✅ 决策判断: AI根据上下文自主决策  
  ✅ AI角色: 主动的智能决策者
```

#### AI自主决策能力范围
```markdown
AI需要自主完成的任务:
1. 理解用户输入意图 (而不是程序解析1-9选项)
2. 决定加载哪个配置文件 (而不是程序映射)
3. 选择执行哪个澄清方法 (而不是程序调用)
4. 判断澄清完成度 (而不是程序计算)
5. 决定何时进入下一阶段 (而不是程序状态机)
6. 选择生成哪种文档 (而不是程序分支)
7. 自主管理用户AI配置选择和验证
8. 自主决定界面状态更新和显示内容
```

### 1. 继承性原则
- **数据模型继承**: 扩展现有models.py，保持数据一致性
- **API模式继承**: 遵循现有API响应格式和错误处理模式  
- **服务层继承**: 复用现有服务架构和数据库服务层
- **测试架构继承**: 遵循现有API集成测试模式

### 2. 分离性原则
- **功能独立**: 需求分析模块可独立运行，不影响现有功能
- **数据隔离**: 新增数据表与现有数据逻辑分离
- **服务解耦**: AI服务通过HTTP API调用，支持独立部署
- **UI模块化**: 独立的前端模块，可选择性加载

### 3. 极简化原则
- **Web页面纯粹化**: 前端只负责传递，不做任何业务判断
- **后端最小化**: 只负责调用AI，不包含业务逻辑
- **AI最大化**: 所有智能决策完全由AI自主完成
- **提示词核心化**: 核心业务逻辑完全由提示词描述

### 4. 用户自主配置原则
- **AI配置独立**: 需求分析模块使用独立的AI配置，与现有midscene配置分离
- **用户自定义**: 用户可在Web界面配置自己的API Key、Base URL、模型名称等
- **配置安全**: AI配置信息加密存储，支持会话级别的配置管理
- **多模型支持**: 支持OpenAI、DashScope、Claude等多种AI服务商
- **AI智能选择**: AI可以根据任务需求智能选择最适合的配置

## 技术栈选择

### 后端技术栈
- **Web框架**: Flask (与现有架构一致)
- **数据库**: SQLAlchemy ORM + PostgreSQL/SQLite (复用现有数据库层)
- **AI服务**: 扩展现有midscene_server.js，添加需求分析专用端点
- **实时通信**: WebSocket (Flask-SocketIO，现有架构已支持)
- **API架构**: RESTful API + WebSocket混合模式

### 前端技术栈
- **渲染**: Flask Jinja2模板 (与现有UI系统一致)
- **样式**: CSS + 现有极简设计系统
- **交互**: Vanilla JavaScript + WebSocket实时通信
- **UI组件**: 复用现有minimal-preview设计组件

### AI技术栈
- **大模型**: 支持多种AI服务商 (OpenAI, DashScope, Claude等)
- **配置管理**: 用户自主配置AI服务参数 (API Key, Base URL, 模型名称)
- **提示工程**: 结构化Prompt模板系统
- **文档生成**: Markdown模板引擎
- **知识库**: 向量数据库 (Chroma/FAISS，轻量级部署)

### 用户AI配置架构
- **配置独立**: 需求分析模块使用独立的AI配置，与现有midscene配置分离
- **多服务商支持**: OpenAI、DashScope、Claude、自定义服务
- **安全存储**: API密钥加密存储，支持配置验证和测试
- **使用统计**: 记录配置使用情况，提供成功率和响应时间统计

## 系统分层架构

### 1. 表示层 (Presentation Layer)
```
intelligent-requirements-analyzer/
├── templates/
│   ├── requirements_chat.html      # 对话界面
│   ├── progress_dashboard.html     # 进度可视化
│   ├── document_preview.html       # 文档预览
│   └── session_management.html     # 会话管理
├── static/
│   ├── js/
│   │   ├── requirements_chat.js    # WebSocket对话逻辑
│   │   ├── progress_tracker.js     # 实时进度更新
│   │   └── document_viewer.js      # 文档操作界面
│   └── css/
│       └── requirements_ui.css     # 需求分析专用样式
```

### 2. API网关层 (API Gateway Layer)
```python
# web_gui/api/requirements.py
from flask import Blueprint, request, jsonify
from ..services.requirements_service import RequirementsAnalysisService

requirements_bp = Blueprint('requirements', __name__)

@requirements_bp.route('/sessions', methods=['POST'])
@api_error_handler
def create_analysis_session():
    """创建需求分析会话"""
    pass

@requirements_bp.route('/sessions/<session_id>/message', methods=['POST'])
@api_error_handler
def send_message(session_id):
    """发送用户消息到AI分析引擎"""
    pass

@requirements_bp.route('/sessions/<session_id>/documents', methods=['GET'])
@api_error_handler
def get_generated_documents(session_id):
    """获取生成的需求文档"""
    pass
```

### 3. 业务逻辑层 (Business Logic Layer)
```python
# web_gui/services/requirements_service.py
class RequirementsAnalysisService:
    """需求分析核心业务服务"""
    
    def __init__(self):
        self.ai_client = AIDecisionEngine()
        self.document_generator = DocumentGenerationService()
        self.knowledge_base = KnowledgeBaseService()
    
    async def create_session(self, user_context: dict) -> str:
        """创建需求分析会话"""
        pass
    
    async def process_user_message(self, session_id: str, message: str) -> dict:
        """处理用户消息并生成AI响应"""
        pass
    
    async def generate_requirements_document(self, session_id: str) -> str:
        """生成结构化需求文档"""
        pass
```

### 4. AI决策引擎层 (AI Decision Engine)
```python
# web_gui/services/ai_decision_engine.py
class AIDecisionEngine:
    """AI决策引擎 - 需求分析专用"""
    
    def __init__(self):
        self.model_name = os.getenv('MIDSCENE_MODEL_NAME', 'qwen-vl-max-latest')
        self.base_url = os.getenv('OPENAI_BASE_URL')
        self.master_prompt = self._load_master_prompt()
    
    async def analyze_requirements(self, context: dict, user_input: str) -> dict:
        """核心需求分析逻辑"""
        prompt = self.master_prompt.format(
            context=json.dumps(context),
            user_input=user_input,
            clarification_methods=self._get_clarification_methods()
        )
        
        response = await self._call_ai_service(prompt)
        return self._parse_ai_decision(response)
    
    def _get_clarification_methods(self) -> list:
        """获取可用的澄清方法"""
        return [
            "需求范围确认",
            "用户角色定义", 
            "功能优先级评估",
            "技术约束识别"
        ]
```

### 5. 知识库服务层 (Knowledge Base Layer)
```python
# web_gui/services/knowledge_base_service.py
class KnowledgeBaseService:
    """项目知识库服务"""
    
    def __init__(self):
        self.vector_store = self._initialize_vector_store()
        self.project_context = self._load_project_context()
    
    def query_project_knowledge(self, query: str) -> list:
        """查询项目相关知识"""
        pass
    
    def update_session_context(self, session_id: str, new_info: dict):
        """更新会话上下文"""
        pass
    
    def _load_project_context(self) -> dict:
        """加载项目上下文信息"""
        return {
            "existing_models": self._analyze_existing_models(),
            "api_patterns": self._analyze_api_patterns(),
            "ui_components": self._analyze_ui_components(),
            "test_patterns": self._analyze_test_patterns()
        }
```

### 6. 文档生成层 (Document Generation Layer)
```python
# web_gui/services/document_generation_service.py
class DocumentGenerationService:
    """结构化文档生成服务"""
    
    def __init__(self):
        self.template_engine = self._initialize_templates()
    
    def generate_prd(self, requirements_data: dict) -> str:
        """生成产品需求文档"""
        template = self.template_engine.get_template('prd_template.md')
        return template.render(**requirements_data)
    
    def generate_epic_stories(self, epic_data: dict) -> str:
        """生成Epic和用户故事"""
        template = self.template_engine.get_template('epic_stories_template.md')
        return template.render(**epic_data)
    
    def generate_test_cases(self, requirements: dict) -> list:
        """基于需求生成测试用例框架"""
        # 集成现有TestCase模型
        pass
```

### 7. 数据持久化层 (Data Persistence Layer)
```python
# 扩展现有models.py
class RequirementsSession(db.Model):
    """需求分析会话模型"""
    
    __tablename__ = "requirements_sessions"
    
    id = db.Column(db.String(50), primary_key=True)  # UUID
    project_name = db.Column(db.String(255))
    session_status = db.Column(db.String(50))  # active, completed, archived
    user_context = db.Column(db.Text)  # JSON
    ai_context = db.Column(db.Text)  # JSON 
    ai_config_id = db.Column(db.Integer, db.ForeignKey("requirements_ai_configs.id"))  # 关联的AI配置
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    messages = db.relationship("RequirementsMessage", backref="session", lazy=True)
    documents = db.relationship("GeneratedDocument", backref="session", lazy=True)

class RequirementsMessage(db.Model):
    """需求分析对话消息"""
    
    __tablename__ = "requirements_messages"
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), db.ForeignKey("requirements_sessions.id"))
    message_type = db.Column(db.String(20))  # user, assistant, system
    content = db.Column(db.Text)
    ai_decision = db.Column(db.Text)  # JSON - AI分析结果
    clarification_methods = db.Column(db.Text)  # JSON - 使用的澄清方法
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GeneratedDocument(db.Model):
    """生成的需求文档"""
    
    __tablename__ = "generated_documents"
    
    id = db.Column(db.Integer, primary_key=True) 
    session_id = db.Column(db.String(50), db.ForeignKey("requirements_sessions.id"))
    document_type = db.Column(db.String(50))  # prd, epic_stories, test_cases
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    version = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20))  # draft, final, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RequirementsAIConfig(db.Model):
    """用户AI配置模型 - 独立于现有midscene配置"""
    
    __tablename__ = "requirements_ai_configs"
    
    id = db.Column(db.Integer, primary_key=True)
    config_name = db.Column(db.String(255), nullable=False)  # 用户自定义配置名称
    provider = db.Column(db.String(50), nullable=False)  # openai, dashscope, claude, custom
    api_key = db.Column(db.Text, nullable=False)  # 加密存储的API密钥
    base_url = db.Column(db.String(500))  # API服务地址
    model_name = db.Column(db.String(100), nullable=False)  # 模型名称
    
    # 高级配置
    model_parameters = db.Column(db.Text)  # JSON: temperature, max_tokens等
    is_active = db.Column(db.Boolean, default=True)
    is_validated = db.Column(db.Boolean, default=False)  # 是否已验证可用
    
    # 使用统计
    usage_count = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)
    total_tokens_used = db.Column(db.Integer, default=0)
    
    # 审计字段
    created_by = db.Column(db.String(100), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime)
    
    # 关系
    sessions = db.relationship("RequirementsSession", backref="ai_config", lazy=True)

class RequirementsAIUsageLog(db.Model):
    """AI配置使用记录"""
    
    __tablename__ = "requirements_ai_usage_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey("requirements_ai_configs.id"))
    session_id = db.Column(db.String(50), db.ForeignKey("requirements_sessions.id"))
    
    # 使用信息
    request_type = db.Column(db.String(50))  # analysis, clarification, generation
    total_tokens = db.Column(db.Integer)
    response_time = db.Column(db.Float)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

## AI服务扩展设计

### 扩展midscene_server.js
```javascript
// midscene_server.js 新增需求分析端点

/**
 * 需求分析专用AI服务端点
 */
app.post('/api/requirements/analyze', async (req, res) => {
    try {
        const { context, userMessage, clarificationMethods } = req.body;
        
        // 构建需求分析专用Prompt
        const analysisPrompt = buildRequirementsPrompt(context, userMessage, clarificationMethods);
        
        // 获取用户的AI配置
        const userAIConfig = req.body.aiConfig;  // 从前端传递用户的AI配置
        
        // 根据配置创建AI客户端
        const aiClient = createAIClient(userAIConfig);
        
        // 调用用户配置的AI模型
        const response = await aiClient.chat.completions.create({
            model: userAIConfig.model_name,
            messages: [
                { role: "system", content: getRequirementsSystemPrompt() },
                { role: "user", content: analysisPrompt }
            ],
            temperature: userAIConfig.model_parameters?.temperature || 0.3,
            max_tokens: userAIConfig.model_parameters?.max_tokens || 2000
        });
        
        const aiDecision = parseRequirementsResponse(response.choices[0].message.content);
        
        res.json({
            success: true,
            decision: aiDecision,
            nextSteps: generateNextSteps(aiDecision),
            clarificationNeeded: identifyNextClarification(aiDecision)
        });
        
    } catch (error) {
        logger.error('需求分析失败:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

function getRequirementsSystemPrompt() {
    return `你是Mary，一位经验丰富的需求分析师。你的任务是：
    
1. **深入理解用户需求**: 通过结构化对话挖掘真实需求
2. **识别关键信息缺口**: 主动发现需要澄清的关键信息
3. **提供专业建议**: 基于最佳实践给出建议和优化方案
4. **生成结构化输出**: 确保输出符合PRD和Epic/Story格式要求

澄清方法优先级:
- 需求范围确认 (最高优先级)
- 用户角色定义
- 功能优先级评估  
- 技术约束识别

始终保持专业、友好的沟通风格，确保用户感到舒适和被理解。`;
}
```

## WebSocket实时通信架构

### 客户端WebSocket实现
```javascript
// static/js/requirements_chat.js
class RequirementsChat {
    constructor() {
        this.socket = io('/requirements');
        this.sessionId = null;
        this.setupEventHandlers();
    }
    
    setupEventHandlers() {
        this.socket.on('analysis_progress', (data) => {
            this.updateProgressIndicator(data.stage, data.progress);
        });
        
        this.socket.on('ai_response', (data) => {
            this.displayAIMessage(data.message, data.clarificationMethods);
        });
        
        this.socket.on('document_ready', (data) => {
            this.notifyDocumentGenerated(data.documentType, data.downloadUrl);
        });
    }
    
    async sendMessage(message) {
        const response = await fetch(`/api/requirements/sessions/${this.sessionId}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        const result = await response.json();
        this.displayAIMessage(result.data.aiResponse);
    }
}
```

### 服务端WebSocket处理
```python
# web_gui/api/requirements.py
from flask_socketio import emit, join_room, leave_room

@socketio.on('join_requirements_session')
def on_join_requirements_session(data):
    session_id = data['session_id']
    join_room(f"requirements_{session_id}")
    emit('session_joined', {'status': 'connected', 'session_id': session_id})

@socketio.on('send_requirements_message')
def on_send_requirements_message(data):
    session_id = data['session_id']
    message = data['message']
    
    # 异步处理AI分析
    task = process_requirements_message_async.delay(session_id, message)
    
    # 立即响应用户
    emit('message_received', {'status': 'processing'}, room=f"requirements_{session_id}")
```

## 集成现有测试架构

### API测试扩展
```python
# tests/api/test_requirements_api.py
class TestRequirementsAPI:
    """需求分析API测试套件"""
    
    def test_create_session(self, client):
        """测试创建分析会话"""
        response = client.post('/api/requirements/sessions', json={
            'project_name': 'Test Project',
            'user_context': {'role': 'product_owner'}
        })
        assert response.status_code == 200
        assert 'session_id' in response.json['data']
    
    def test_send_message(self, client, create_test_session):
        """测试发送消息"""
        session_id = create_test_session['session_id']
        
        response = client.post(f'/api/requirements/sessions/{session_id}/message', json={
            'message': '我需要创建一个用户管理系统'
        })
        
        assert response.status_code == 200
        assert 'ai_response' in response.json['data']
        assert 'clarification_methods' in response.json['data']
    
    def test_generate_document(self, client, create_test_session):
        """测试文档生成"""
        session_id = create_test_session['session_id']
        
        response = client.post(f'/api/requirements/sessions/{session_id}/generate', json={
            'document_type': 'prd'
        })
        
        assert response.status_code == 200
        assert 'document_url' in response.json['data']
```

## 部署和扩展考虑

### 开发环境配置
```bash
# 新增环境变量
REQUIREMENTS_AI_ENABLED=true
REQUIREMENTS_KNOWLEDGE_BASE_PATH=./knowledge_base
REQUIREMENTS_DOCUMENT_OUTPUT_PATH=./generated_docs
VECTOR_STORE_TYPE=chroma  # chroma, faiss
```

### 数据库迁移
```python
# 新增迁移脚本
# migrations/add_requirements_models.py
def upgrade():
    # 创建需求分析相关表
    op.create_table('requirements_sessions', ...)
    op.create_table('requirements_messages', ...)
    op.create_table('generated_documents', ...)
```

### 性能优化策略
1. **AI调用异步化**: 使用Celery处理长时间AI分析任务
2. **会话状态缓存**: Redis缓存活跃会话状态
3. **文档增量生成**: 避免重复生成相同内容
4. **知识库预加载**: 启动时加载项目上下文到内存

### 监控和日志
```python
# 复用现有日志系统
logger = logging.getLogger(__name__)

# 需求分析专用指标
@requirements_bp.after_request
def log_requirements_api_metrics(response):
    """记录需求分析API调用指标"""
    logger.info(f"Requirements API: {request.endpoint} - {response.status_code}")
    return response
```

## 与现有架构的集成点

### 1. 测试用例自动生成
- 需求分析完成后，自动生成TestCase记录
- 集成现有执行引擎，支持生成的测试用例直接执行

### 2. 复用现有UI组件
- 使用现有minimal-preview设计系统
- 扩展现有模板和静态资源结构

### 3. 数据库统一管理
- 复用现有DatabaseService
- 扩展现有models.py，保持一致的数据访问模式

### 4. API架构一致性
- 遵循现有API响应格式标准
- 复用现有错误处理和验证机制

## 🎨 前端架构设计

### UI组件架构

#### 页面组件结构
```
requirements/
├── templates/
│   ├── index.html              # 需求分析主页
│   ├── new_session.html        # 创建新会话
│   ├── ai_config.html          # AI配置管理 (新增)
│   ├── chat.html               # 对话界面
│   ├── progress.html           # 进度监控
│   └── documents.html          # 文档管理
├── static/
│   ├── js/
│   │   ├── requirements-chat.js     # 对话交互
│   │   ├── ai-config-manager.js     # AI配置管理 (新增)
│   │   ├── config-validator.js      # 配置验证 (新增)
│   │   ├── progress-tracker.js      # 进度可视化
│   │   ├── document-viewer.js       # 文档查看
│   │   └── session-manager.js       # 会话管理
│   └── css/
│       ├── requirements-chat.css    # 对话界面样式
│       ├── ai-config.css            # AI配置界面样式 (新增)
│       ├── progress-display.css     # 进度显示样式
│       └── document-preview.css     # 文档预览样式
```

#### AI配置管理界面设计
```html
<!-- templates/requirements/ai_config.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>AI配置管理</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/minimal-style.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/ai-config.css') }}">
</head>
<body>
    <div class="container">
        <!-- 页面头部 -->
        <div class="page-header">
            <h1>AI配置管理</h1>
            <button id="add-config-btn" class="btn-primary">添加新配置</button>
        </div>
        
        <!-- 配置列表 -->
        <div class="config-list">
            <div id="config-items" class="config-items">
                <!-- 配置项将通过JavaScript动态加载 -->
            </div>
        </div>
        
        <!-- 配置表单模态框 -->
        <div id="config-modal" class="modal hidden">
            <div class="modal-content">
                <form id="config-form" class="config-form">
                    <div class="form-group">
                        <label for="config-name">配置名称</label>
                        <input type="text" id="config-name" name="config_name" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="provider">AI服务提供商</label>
                        <select id="provider" name="provider" required>
                            <option value="openai">OpenAI</option>
                            <option value="dashscope">阿里云DashScope</option>
                            <option value="claude">Anthropic Claude</option>
                            <option value="custom">自定义服务</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="api-key">API密钥</label>
                        <input type="password" id="api-key" name="api_key" required>
                        <small>密钥将被安全加密存储</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="base-url">服务地址 (可选)</label>
                        <input type="url" id="base-url" name="base_url">
                    </div>
                    
                    <div class="form-group">
                        <label for="model-name">模型名称</label>
                        <input type="text" id="model-name" name="model_name" required>
                    </div>
                    
                    <div class="form-actions">
                        <button type="button" id="test-config-btn" class="btn-secondary">测试配置</button>
                        <button type="submit" class="btn-primary">保存配置</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <script src="{{ url_for('static', filename='js/ai-config-manager.js') }}"></script>
</body>
</html>
```

### JavaScript组件设计

#### AI配置管理器
```javascript
// static/js/ai-config-manager.js
class AIConfigManager {
    constructor() {
        this.configs = [];
        this.currentEditingId = null;
        this.setupEventHandlers();
        this.loadConfigs();
    }
    
    setupEventHandlers() {
        document.getElementById('add-config-btn').addEventListener('click', () => {
            this.showConfigModal();
        });
        
        document.getElementById('config-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveConfig();
        });
        
        document.getElementById('test-config-btn').addEventListener('click', () => {
            this.testConfig();
        });
    }
    
    async loadConfigs() {
        try {
            const response = await fetch('/api/requirements/ai-configs');
            const result = await response.json();
            
            if (result.code === 200) {
                this.configs = result.data;
                this.renderConfigs();
            }
        } catch (error) {
            console.error('加载AI配置失败:', error);
        }
    }
    
    renderConfigs() {
        const container = document.getElementById('config-items');
        container.innerHTML = '';
        
        this.configs.forEach(config => {
            const configElement = this.createConfigElement(config);
            container.appendChild(configElement);
        });
    }
    
    createConfigElement(config) {
        const div = document.createElement('div');
        div.className = 'config-item';
        div.innerHTML = `
            <div class="config-info">
                <h3>${config.config_name}</h3>
                <p>提供商: ${config.provider} | 模型: ${config.model_name}</p>
                <p>状态: ${config.is_validated ? '✅ 已验证' : '⚠️ 未验证'}</p>
                <small>成功率: ${(config.success_rate * 100).toFixed(1)}% | 使用次数: ${config.usage_count}</small>
            </div>
            <div class="config-actions">
                <button onclick="configManager.editConfig(${config.id})" class="btn-secondary">编辑</button>
                <button onclick="configManager.testConfig(${config.id})" class="btn-secondary">测试</button>
                <button onclick="configManager.deleteConfig(${config.id})" class="btn-danger">删除</button>
            </div>
        `;
        return div;
    }
    
    async saveConfig() {
        const formData = new FormData(document.getElementById('config-form'));
        const configData = Object.fromEntries(formData.entries());
        
        try {
            const url = this.currentEditingId 
                ? `/api/requirements/ai-configs/${this.currentEditingId}`
                : '/api/requirements/ai-configs';
            const method = this.currentEditingId ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configData)
            });
            
            const result = await response.json();
            
            if (result.code === 200) {
                this.hideConfigModal();
                this.loadConfigs();
                this.showMessage('配置保存成功', 'success');
            } else {
                this.showMessage(result.message, 'error');
            }
        } catch (error) {
            this.showMessage('保存失败: ' + error.message, 'error');
        }
    }
    
    async testConfig(configId) {
        try {
            const response = await fetch(`/api/requirements/ai-configs/${configId}/test`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.code === 200) {
                const testData = result.data;
                this.showTestResult(testData);
            } else {
                this.showMessage('测试失败: ' + result.message, 'error');
            }
        } catch (error) {
            this.showMessage('测试失败: ' + error.message, 'error');
        }
    }
    
    showTestResult(testData) {
        const message = testData.success 
            ? `✅ 测试成功\n响应时间: ${testData.response_time.toFixed(2)}s\n模型信息: ${testData.model_info}\n示例响应: ${testData.test_response}`
            : `❌ 测试失败\n错误: ${testData.error}`;
            
        alert(message);
    }
}

// 初始化
let configManager;
document.addEventListener('DOMContentLoaded', () => {
    configManager = new AIConfigManager();
});
```

## 🔒 安全设计

### 数据加密
```python
# web_gui/utils/encryption.py
from cryptography.fernet import Fernet
import os

class DataEncryption:
    def __init__(self):
        self.key = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
        self.cipher = Fernet(self.key)
    
    def encrypt_text(self, text: str) -> str:
        """加密文本"""
        return self.cipher.encrypt(text.encode()).decode()
    
    def decrypt_text(self, encrypted_text: str) -> str:
        """解密文本"""
        return self.cipher.decrypt(encrypted_text.encode()).decode()
```

### API访问控制
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@requirements_bp.route('/ai-configs', methods=['POST'])
@limiter.limit("5 per minute")  # 限制配置创建频率
def create_ai_config():
    pass

@requirements_bp.route('/sessions/<session_id>/messages', methods=['POST'])  
@limiter.limit("20 per minute")  # 限制AI调用频率
def send_message(session_id):
    pass
```

## 📊 监控和运维

### 日志系统
```python
import structlog

logger = structlog.get_logger(__name__)

class RequirementsLogger:
    @staticmethod
    def log_ai_config_created(config_id: int, provider: str):
        logger.info("ai_config_created",
                   config_id=config_id,
                   provider=provider,
                   timestamp=datetime.utcnow().isoformat())
    
    @staticmethod
    def log_ai_analysis(session_id: str, config_id: int, processing_time: float):
        logger.info("ai_analysis_completed",
                   session_id=session_id,
                   config_id=config_id,
                   processing_time=processing_time)
```

### 性能监控
```python
from prometheus_client import Counter, Histogram, Gauge

# 定义监控指标
ai_config_usage = Counter('ai_config_usage_total', 'Total AI config usage', ['config_id', 'provider'])
analysis_duration = Histogram('analysis_duration_seconds', 'Time spent on analysis')
active_configs = Gauge('active_ai_configs', 'Number of active AI configs')
```

## 🚀 部署架构

### Docker容器化
```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 初始化数据库和AI配置
RUN python scripts/setup_requirements_module.py

EXPOSE 5001
CMD ["python", "web_gui/run_enhanced.py"]
```

### Docker Compose配置  
```yaml
version: '3.8'
services:
  intent-test-framework:
    build: .
    ports:
      - "5001:5001"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/intent_framework
      - REQUIREMENTS_MODULE_ENABLED=true
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - db
      - redis
      - midscene-server
  
  midscene-server:
    build:
      context: .
      dockerfile: Dockerfile.midscene
    ports:
      - "3001:3001"
    environment:
      - NODE_ENV=production
  
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: intent_framework
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:6-alpine

volumes:
  postgres_data:
```

## 🎯 架构优势总结

1. **用户自主性**: 用户可自由配置AI服务，不依赖系统预设配置
2. **安全可靠**: API密钥加密存储，配置验证机制完善
3. **无缝集成**: 完全基于现有架构模式设计，集成风险最小
4. **服务解耦**: AI需求分析作为独立服务，不影响现有功能
5. **数据一致**: 复用现有数据模型和访问层，保持数据完整性
6. **扩展性强**: 模块化设计支持功能独立迭代和扩展
7. **测试覆盖**: 遵循现有测试驱动模式，确保质量稳定性
8. **多模型支持**: 支持主流AI服务商，用户选择灵活

## 📈 实施建议

### 分阶段实施
1. **迭代1**: 实现用户AI配置管理和基础对话功能
2. **迭代2**: 完成智能文档生成和进度可视化  
3. **迭代3**: 实现测试用例自动生成和完整集成

### 风险控制
1. **充分测试**: 每个功能模块都要有完整的测试覆盖
2. **性能监控**: 部署初期要密切监控AI调用性能
3. **用户反馈**: 定期收集用户使用反馈，持续优化体验
4. **安全审计**: 定期检查API密钥存储和访问控制机制

这个完整的技术架构设计充分考虑了用户自主配置AI服务的需求，确保AI需求分析模块能够无缝集成到Intent Test Framework中，同时提供灵活、安全、可扩展的AI服务配置体验。