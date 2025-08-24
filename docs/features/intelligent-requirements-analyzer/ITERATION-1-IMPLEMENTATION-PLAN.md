# 迭代1技术实施方案: AI对话体验

## 迭代目标
创建基础的AI需求分析对话体验，让用户能够通过自然语言与AI Mary进行需求澄清对话，实现核心的需求理解和澄清流程。

## 核心功能范围 (用户可见价值)
1. **智能对话界面**: 用户可以用自然语言描述需求
2. **实时AI回应**: Mary能够理解用户需求并提供专业回应  
3. **澄清引导**: Mary主动识别信息缺口并引导用户澄清
4. **基础进度可视化**: 用户可以看到需求理解的进展状态

## 技术实施范围

### 1. 核心组件开发优先级
```
优先级1 (必须实现):
├── AI对话引擎核心逻辑
├── WebSocket实时通信  
├── 基础UI对话界面
└── 会话状态管理

优先级2 (本迭代完成):
├── 澄清方法引擎 (3-4个核心方法)
├── 进度可视化组件
└── 基础错误处理

优先级3 (后续迭代):  
├── 文档生成功能
├── 知识库集成
└── 高级分析功能
```

### 2. 最小可行产品 (MVP) 架构

#### 2.1 数据模型设计 (最简化)
```python
# web_gui/models.py - 新增模型

class RequirementsSession(db.Model):
    """需求分析会话模型 - 迭代1简化版"""
    
    __tablename__ = "requirements_sessions"
    
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_name = db.Column(db.String(255))
    session_status = db.Column(db.String(50), default='active')  # active, paused, completed
    current_stage = db.Column(db.String(50), default='initial')  # initial, clarifying, analyzing
    progress_percentage = db.Column(db.Integer, default=0)
    user_context = db.Column(db.Text)  # JSON存储用户上下文
    ai_context = db.Column(db.Text)    # JSON存储AI分析上下文
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 简化版关系
    messages = db.relationship("RequirementsMessage", backref="session", lazy=True, cascade="all, delete-orphan")

class RequirementsMessage(db.Model):
    """需求分析对话消息 - 迭代1简化版"""
    
    __tablename__ = "requirements_messages"
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), db.ForeignKey("requirements_sessions.id"), nullable=False)
    message_type = db.Column(db.String(20), nullable=False)  # user, assistant, system
    content = db.Column(db.Text, nullable=False)
    ai_decision_data = db.Column(db.Text)  # JSON - AI分析结果
    clarification_method = db.Column(db.String(100))  # 使用的澄清方法
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "message_type": self.message_type,
            "content": self.content,
            "ai_decision_data": json.loads(self.ai_decision_data) if self.ai_decision_data else {},
            "clarification_method": self.clarification_method,
            "created_at": self.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if self.created_at else None
        }
```

#### 2.2 API端点设计 (MVP版本)
```python
# web_gui/api/requirements.py

from flask import Blueprint, request, jsonify
from ..services.requirements_service import RequirementsService
from ..utils.error_handler import api_error_handler, format_success_response

requirements_bp = Blueprint('requirements', __name__)
requirements_service = RequirementsService()

@requirements_bp.route('/sessions', methods=['POST'])
@api_error_handler
def create_session():
    """创建新的需求分析会话"""
    data = request.get_json()
    
    session_data = {
        'project_name': data.get('project_name', '新项目'),
        'user_context': data.get('user_context', {})
    }
    
    session = requirements_service.create_session(session_data)
    return format_success_response(session.to_dict())

@requirements_bp.route('/sessions/<session_id>', methods=['GET'])
@api_error_handler
def get_session(session_id):
    """获取会话详情"""
    session = requirements_service.get_session(session_id)
    if not session:
        return jsonify({'code': 404, 'message': '会话不存在'}), 404
    
    return format_success_response({
        'session': session.to_dict(),
        'messages': [msg.to_dict() for msg in session.messages]
    })

@requirements_bp.route('/sessions/<session_id>/messages', methods=['POST'])
@api_error_handler
def send_message(session_id):
    """发送用户消息并获取AI响应"""
    data = request.get_json()
    message_content = data.get('message', '').strip()
    
    if not message_content:
        return jsonify({'code': 400, 'message': '消息内容不能为空'}), 400
    
    result = requirements_service.process_user_message(session_id, message_content)
    return format_success_response(result)

@requirements_bp.route('/sessions/<session_id>/progress', methods=['GET'])
@api_error_handler
def get_progress(session_id):
    """获取需求分析进度"""
    progress = requirements_service.get_session_progress(session_id)
    return format_success_response(progress)
```

#### 2.3 核心业务逻辑服务
```python
# web_gui/services/requirements_service.py

import json
import uuid
import logging
from datetime import datetime
from ..models import db, RequirementsSession, RequirementsMessage
from .ai_requirements_engine import AIRequirementsEngine

logger = logging.getLogger(__name__)

class RequirementsService:
    """需求分析业务服务 - 迭代1简化版"""
    
    def __init__(self):
        self.ai_engine = AIRequirementsEngine()
    
    def create_session(self, session_data: dict) -> RequirementsSession:
        """创建需求分析会话"""
        try:
            session = RequirementsSession(
                project_name=session_data.get('project_name'),
                user_context=json.dumps(session_data.get('user_context', {})),
                ai_context=json.dumps(self._initialize_ai_context())
            )
            
            db.session.add(session)
            db.session.commit()
            
            # 添加欢迎消息
            welcome_message = self._create_welcome_message(session.id)
            db.session.add(welcome_message)
            db.session.commit()
            
            logger.info(f"创建需求分析会话成功: {session.id}")
            return session
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"创建会话失败: {str(e)}")
            raise
    
    def get_session(self, session_id: str) -> RequirementsSession:
        """获取会话详情"""
        return RequirementsSession.query.filter_by(id=session_id).first()
    
    def process_user_message(self, session_id: str, message_content: str) -> dict:
        """处理用户消息并生成AI响应"""
        try:
            # 获取会话
            session = self.get_session(session_id)
            if not session:
                raise ValueError("会话不存在")
            
            # 保存用户消息
            user_message = RequirementsMessage(
                session_id=session_id,
                message_type='user',
                content=message_content
            )
            db.session.add(user_message)
            
            # 获取AI响应
            ai_response = self.ai_engine.analyze_user_message(
                session_context=json.loads(session.ai_context),
                user_message=message_content,
                message_history=self._get_recent_messages(session_id)
            )
            
            # 保存AI响应
            ai_message = RequirementsMessage(
                session_id=session_id,
                message_type='assistant',
                content=ai_response['response'],
                ai_decision_data=json.dumps(ai_response.get('decision_data', {})),
                clarification_method=ai_response.get('clarification_method')
            )
            db.session.add(ai_message)
            
            # 更新会话状态
            self._update_session_progress(session, ai_response.get('progress_update', {}))
            
            db.session.commit()
            
            return {
                'ai_response': ai_response['response'],
                'clarification_method': ai_response.get('clarification_method'),
                'progress_update': ai_response.get('progress_update', {}),
                'next_steps': ai_response.get('next_steps', [])
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"处理用户消息失败: {str(e)}")
            raise
    
    def get_session_progress(self, session_id: str) -> dict:
        """获取会话进度"""
        session = self.get_session(session_id)
        if not session:
            raise ValueError("会话不存在")
        
        return {
            'session_id': session_id,
            'current_stage': session.current_stage,
            'progress_percentage': session.progress_percentage,
            'status': session.session_status,
            'last_updated': session.updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
    
    def _initialize_ai_context(self) -> dict:
        """初始化AI上下文"""
        return {
            'clarification_methods_used': [],
            'identified_requirements': [],
            'pending_clarifications': [],
            'analysis_stage': 'initial'
        }
    
    def _create_welcome_message(self, session_id: str) -> RequirementsMessage:
        """创建欢迎消息"""
        welcome_text = """👋 你好！我是Mary，你的AI需求分析师。

我会帮你：
✅ 理解和澄清你的项目需求
✅ 识别关键功能和优先级  
✅ 发现可能的技术挑战
✅ 确保需求描述清晰完整

请开始描述你的项目想法吧！比如：
• "我想做一个..."
• "用户需要能够..."
• "系统应该支持..." """

        return RequirementsMessage(
            session_id=session_id,
            message_type='assistant',
            content=welcome_text
        )
    
    def _get_recent_messages(self, session_id: str, limit: int = 10) -> list:
        """获取最近的对话历史"""
        messages = RequirementsMessage.query.filter_by(session_id=session_id)\
            .order_by(RequirementsMessage.created_at.desc())\
            .limit(limit)\
            .all()
        
        return [msg.to_dict() for msg in reversed(messages)]
    
    def _update_session_progress(self, session: RequirementsSession, progress_data: dict):
        """更新会话进度"""
        if 'stage' in progress_data:
            session.current_stage = progress_data['stage']
        
        if 'percentage' in progress_data:
            session.progress_percentage = min(100, max(0, progress_data['percentage']))
        
        if 'ai_context_update' in progress_data:
            current_context = json.loads(session.ai_context)
            current_context.update(progress_data['ai_context_update'])
            session.ai_context = json.dumps(current_context)
```

#### 2.4 AI需求分析引擎
```python
# web_gui/services/ai_requirements_engine.py

import json
import logging
import requests
import os
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class AIRequirementsEngine:
    """AI需求分析引擎 - 迭代1核心版本"""
    
    def __init__(self):
        self.midscene_url = os.getenv('MIDSCENE_SERVER_URL', 'http://localhost:3001')
        self.model_name = os.getenv('MIDSCENE_MODEL_NAME', 'qwen-vl-max-latest')
        self.clarification_methods = self._initialize_clarification_methods()
    
    def analyze_user_message(self, session_context: dict, user_message: str, message_history: list) -> dict:
        """分析用户消息并生成响应"""
        try:
            # 构建分析请求
            analysis_request = {
                'session_context': session_context,
                'user_message': user_message,
                'message_history': message_history,
                'clarification_methods': self.clarification_methods
            }
            
            # 调用AI服务
            response = requests.post(
                f'{self.midscene_url}/api/requirements/analyze',
                json=analysis_request,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"AI服务调用失败: {response.status_code}")
            
            ai_result = response.json()
            
            # 解析AI响应
            return self._process_ai_response(ai_result, session_context)
            
        except Exception as e:
            logger.error(f"AI分析失败: {str(e)}")
            return self._generate_fallback_response(user_message)
    
    def _initialize_clarification_methods(self) -> dict:
        """初始化澄清方法库"""
        return {
            'scope_clarification': {
                'name': '需求范围确认',
                'description': '明确功能边界和项目范围',
                'triggers': ['功能', '系统', '平台', '模块'],
                'questions': [
                    '这个功能主要服务于哪些用户群体？',
                    '核心功能的边界是什么？',
                    '哪些功能是必需的，哪些是可选的？'
                ]
            },
            'user_role_definition': {
                'name': '用户角色定义', 
                'description': '识别和定义系统的用户角色',
                'triggers': ['用户', '角色', '权限', '登录'],
                'questions': [
                    '系统会有哪些类型的用户？',
                    '不同用户的权限差异是什么？',
                    '用户的典型使用场景是什么？'
                ]
            },
            'priority_assessment': {
                'name': '功能优先级评估',
                'description': '评估功能的重要性和紧急度',
                'triggers': ['重要', '优先', '核心', '关键'],
                'questions': [
                    '哪些功能是MVP必须的？',
                    '功能的实现优先级如何排序？',
                    '哪些功能可以在后期迭代中实现？'
                ]
            },
            'constraint_identification': {
                'name': '技术约束识别',
                'description': '识别技术和业务约束',
                'triggers': ['技术', '性能', '安全', '集成'],
                'questions': [
                    '有哪些技术栈的限制？',
                    '性能要求是什么？',
                    '需要集成哪些外部系统？'
                ]
            }
        }
    
    def _process_ai_response(self, ai_result: dict, session_context: dict) -> dict:
        """处理AI响应结果"""
        decision_data = ai_result.get('decision', {})
        
        # 确定使用的澄清方法
        clarification_method = self._determine_clarification_method(decision_data, session_context)
        
        # 计算进度更新
        progress_update = self._calculate_progress_update(decision_data, session_context)
        
        return {
            'response': decision_data.get('response', '我理解了，请继续描述更多细节。'),
            'decision_data': decision_data,
            'clarification_method': clarification_method,
            'progress_update': progress_update,
            'next_steps': decision_data.get('next_steps', [])
        }
    
    def _determine_clarification_method(self, decision_data: dict, session_context: dict) -> str:
        """确定使用的澄清方法"""
        # 简化版逻辑，基于关键词匹配
        message_content = decision_data.get('original_message', '').lower()
        
        for method_key, method_info in self.clarification_methods.items():
            for trigger in method_info['triggers']:
                if trigger in message_content:
                    return method_key
        
        return 'scope_clarification'  # 默认方法
    
    def _calculate_progress_update(self, decision_data: dict, session_context: dict) -> dict:
        """计算进度更新"""
        # 简化版进度计算
        current_percentage = session_context.get('analysis_stage', 'initial')
        
        stage_mapping = {
            'initial': {'percentage': 10, 'stage': 'understanding'},
            'understanding': {'percentage': 30, 'stage': 'clarifying'},
            'clarifying': {'percentage': 60, 'stage': 'analyzing'},
            'analyzing': {'percentage': 85, 'stage': 'finalizing'}
        }
        
        if current_percentage in stage_mapping:
            return stage_mapping[current_percentage]
        
        return {'percentage': 25, 'stage': 'understanding'}
    
    def _generate_fallback_response(self, user_message: str) -> dict:
        """生成降级响应"""
        return {
            'response': f'我理解了你关于"{user_message[:50]}..."的需求。能否提供更多具体的细节？比如主要的用户群体和核心功能是什么？',
            'decision_data': {'fallback': True},
            'clarification_method': 'scope_clarification',
            'progress_update': {'percentage': 15, 'stage': 'understanding'},
            'next_steps': ['提供更多功能细节', '描述用户场景', '明确技术要求']
        }
```

#### 2.5 扩展midscene_server.js
```javascript
// midscene_server.js 新增需求分析端点

/**
 * 需求分析专用端点 - 迭代1简化版
 */
app.post('/api/requirements/analyze', async (req, res) => {
    try {
        const { session_context, user_message, message_history, clarification_methods } = req.body;
        
        // 构建专用Prompt
        const analysisPrompt = buildRequirementsAnalysisPrompt(
            session_context, 
            user_message, 
            message_history, 
            clarification_methods
        );
        
        console.log('🔍 需求分析请求:', {
            user_message: user_message.substring(0, 100) + '...',
            context_stage: session_context.analysis_stage
        });
        
        // 调用AI模型
        const response = await openaiClient.chat.completions.create({
            model: process.env.MIDSCENE_MODEL_NAME || 'qwen-vl-max-latest',
            messages: [
                { role: "system", content: getRequirementsSystemPrompt() },
                { role: "user", content: analysisPrompt }
            ],
            temperature: 0.3,
            max_tokens: 1500
        });
        
        const aiContent = response.choices[0].message.content;
        const decision = parseRequirementsDecision(aiContent, user_message);
        
        console.log('✅ AI分析完成:', {
            response_length: decision.response?.length || 0,
            clarification_needed: decision.clarification_needed
        });
        
        res.json({
            success: true,
            decision: decision,
            model_used: process.env.MIDSCENE_MODEL_NAME,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        console.error('❌ 需求分析失败:', error);
        res.status(500).json({
            success: false,
            error: error.message,
            fallback_response: "我遇到了一些技术问题，但让我们继续讨论你的需求。请描述更多细节。"
        });
    }
});

function getRequirementsSystemPrompt() {
    return `你是Mary，一位经验丰富的产品需求分析师。你的目标是通过对话帮助用户澄清和完善他们的产品需求。

核心职责：
1. 深入理解用户的需求和想法
2. 主动识别需要澄清的关键信息
3. 引导用户提供完整的需求描述
4. 保持专业、友好和耐心的沟通风格

澄清重点（按优先级）：
- 需求范围确认：功能边界、目标用户群体
- 用户角色定义：使用者类型、权限差异
- 功能优先级评估：MVP核心功能识别
- 技术约束识别：技术要求、性能约束

输出要求：
- 响应自然、专业且具有引导性
- 每次最多提出2-3个关键问题
- 基于用户输入给出具体的建议和观察
- 保持对话流畅，避免机械化问答

始终记住：你的目标是帮助用户完善需求，而不是主导对话。`;
}

function buildRequirementsAnalysisPrompt(sessionContext, userMessage, messageHistory, clarificationMethods) {
    const historyText = messageHistory.map(msg => 
        `${msg.message_type === 'user' ? '用户' : 'Mary'}: ${msg.content}`
    ).slice(-6).join('\n'); // 只取最近6条消息
    
    return `当前会话上下文:
分析阶段: ${sessionContext.analysis_stage}
已使用澄清方法: ${sessionContext.clarification_methods_used?.join(', ') || '无'}
已识别需求: ${sessionContext.identified_requirements?.length || 0}个

最近对话历史:
${historyText}

用户新消息: ${userMessage}

请分析这条用户消息，并提供专业的回应。重点关注：
1. 理解用户的真实意图
2. 识别需要澄清的关键信息
3. 选择最合适的澄清方法
4. 提供自然、有帮助的回应

请直接回复给用户的内容，保持自然对话风格。`;
}

function parseRequirementsDecision(aiContent, originalMessage) {
    // 简化版解析 - 迭代1重点是功能正常运行
    return {
        response: aiContent.trim(),
        original_message: originalMessage,
        clarification_needed: aiContent.includes('?') || aiContent.includes('？'),
        confidence: 0.8,
        next_steps: [
            '继续描述具体功能',
            '明确用户角色',
            '确定优先级'
        ]
    };
}
```

### 3. 前端界面实现 (MVP版本)

#### 3.1 对话界面模板
```html
<!-- templates/requirements/chat.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI需求分析 - {{ session.project_name }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/minimal-style.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/requirements-chat.css') }}">
</head>
<body>
    <div class="container">
        <!-- 顶部进度条 -->
        <div class="progress-header">
            <div class="progress-info">
                <h1>需求分析对话 - {{ session.project_name }}</h1>
                <div class="progress-stats">
                    <span>当前阶段: <span id="current-stage">{{ session.current_stage }}</span></span>
                    <span>进度: <span id="progress-percentage">{{ session.progress_percentage }}%</span></span>
                </div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {{ session.progress_percentage }}%"></div>
            </div>
        </div>
        
        <!-- 对话区域 -->
        <div class="chat-container">
            <div id="chat-messages" class="chat-messages">
                {% for message in messages %}
                <div class="message {{ message.message_type }}">
                    <div class="message-content">{{ message.content | safe }}</div>
                    {% if message.clarification_method %}
                    <div class="clarification-method">澄清方法: {{ message.clarification_method }}</div>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            
            <!-- 输入区域 -->
            <div class="chat-input-container">
                <div class="input-group">
                    <textarea id="user-input" placeholder="描述你的需求和想法..." rows="3"></textarea>
                    <button id="send-button" class="btn-primary">发送</button>
                </div>
                <div class="input-hints">
                    <span class="hint-item">💡 提示：详细描述功能需求</span>
                    <span class="hint-item">👥 明确目标用户群体</span>
                    <span class="hint-item">⭐ 说明优先级和重要性</span>
                </div>
            </div>
        </div>
    </div>
    
    <script src="{{ url_for('static', filename='js/requirements-chat.js') }}"></script>
</body>
</html>
```

#### 3.2 对话交互JavaScript
```javascript
// static/js/requirements-chat.js

class RequirementsChat {
    constructor() {
        this.sessionId = this.getSessionId();
        this.setupEventHandlers();
        this.scrollToBottom();
    }
    
    getSessionId() {
        // 从URL或页面数据获取session ID
        const pathParts = window.location.pathname.split('/');
        return pathParts[pathParts.length - 1];
    }
    
    setupEventHandlers() {
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');
        
        sendButton.addEventListener('click', () => this.sendMessage());
        
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // 自动调整文本框高度
        userInput.addEventListener('input', this.autoResize);
    }
    
    async sendMessage() {
        const userInput = document.getElementById('user-input');
        const message = userInput.value.trim();
        
        if (!message) return;
        
        // 显示用户消息
        this.addMessage('user', message);
        userInput.value = '';
        
        // 显示加载状态
        const loadingId = this.showLoadingMessage();
        
        try {
            const response = await fetch(`/api/requirements/sessions/${this.sessionId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });
            
            const result = await response.json();
            
            // 移除加载消息
            this.removeLoadingMessage(loadingId);
            
            if (result.code === 200) {
                // 显示AI响应
                this.addMessage('assistant', result.data.ai_response, {
                    clarification_method: result.data.clarification_method
                });
                
                // 更新进度
                if (result.data.progress_update) {
                    this.updateProgress(result.data.progress_update);
                }
            } else {
                this.addMessage('system', `错误: ${result.message}`);
            }
            
        } catch (error) {
            console.error('发送消息失败:', error);
            this.removeLoadingMessage(loadingId);
            this.addMessage('system', '网络错误，请稍后重试');
        }
    }
    
    addMessage(type, content, metadata = {}) {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        let messageHtml = `<div class="message-content">${this.formatMessageContent(content)}</div>`;
        
        if (metadata.clarification_method) {
            messageHtml += `<div class="clarification-method">澄清方法: ${metadata.clarification_method}</div>`;
        }
        
        messageDiv.innerHTML = messageHtml;
        chatMessages.appendChild(messageDiv);
        
        this.scrollToBottom();
        
        return messageDiv;
    }
    
    showLoadingMessage() {
        const loadingId = `loading-${Date.now()}`;
        const loadingDiv = this.addMessage('assistant', '正在分析中...');
        loadingDiv.id = loadingId;
        loadingDiv.classList.add('loading');
        
        return loadingId;
    }
    
    removeLoadingMessage(loadingId) {
        const loadingDiv = document.getElementById(loadingId);
        if (loadingDiv) {
            loadingDiv.remove();
        }
    }
    
    updateProgress(progressData) {
        if (progressData.stage) {
            document.getElementById('current-stage').textContent = progressData.stage;
        }
        
        if (progressData.percentage !== undefined) {
            const percentage = Math.max(0, Math.min(100, progressData.percentage));
            document.getElementById('progress-percentage').textContent = percentage + '%';
            
            const progressFill = document.querySelector('.progress-fill');
            progressFill.style.width = percentage + '%';
        }
    }
    
    formatMessageContent(content) {
        // 简单的文本格式化
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }
    
    autoResize(e) {
        e.target.style.height = 'auto';
        e.target.style.height = e.target.scrollHeight + 'px';
    }
    
    scrollToBottom() {
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    window.requirementsChat = new RequirementsChat();
});
```

#### 3.3 样式文件
```css
/* static/css/requirements-chat.css */

.progress-header {
    background: white;
    border-bottom: 1px solid #e0e0e0;
    padding: 1rem;
    margin-bottom: 1rem;
}

.progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.progress-info h1 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
}

.progress-stats {
    display: flex;
    gap: 2rem;
    font-size: 0.9rem;
    color: #666;
}

.progress-bar {
    width: 100%;
    height: 6px;
    background-color: #f0f0f0;
    border-radius: 3px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background-color: #4CAF50;
    transition: width 0.5s ease;
}

.chat-container {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 200px);
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    background: white;
    border-radius: 8px;
    margin-bottom: 1rem;
}

.message {
    margin-bottom: 1rem;
    max-width: 80%;
}

.message.user {
    margin-left: auto;
}

.message.assistant {
    margin-right: auto;
}

.message.system {
    margin: 0 auto;
    max-width: 60%;
    text-align: center;
    opacity: 0.8;
}

.message-content {
    padding: 0.75rem 1rem;
    border-radius: 1rem;
    background: #f5f5f5;
    line-height: 1.5;
}

.message.user .message-content {
    background: #007AFF;
    color: white;
}

.message.assistant .message-content {
    background: #E5E5EA;
    color: black;
}

.message.system .message-content {
    background: #FFE4B5;
    color: #8B4513;
    font-style: italic;
}

.clarification-method {
    font-size: 0.8rem;
    color: #666;
    margin-top: 0.25rem;
    padding-left: 1rem;
}

.message.loading .message-content {
    opacity: 0.7;
    animation: pulse 1.5s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 0.7; }
    50% { opacity: 1; }
}

.chat-input-container {
    background: white;
    border-radius: 8px;
    padding: 1rem;
}

.input-group {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}

.input-group textarea {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 0.5rem;
    resize: none;
    font-family: inherit;
    font-size: 1rem;
    min-height: 3rem;
    max-height: 8rem;
}

.input-group textarea:focus {
    outline: none;
    border-color: #007AFF;
    box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.1);
}

.input-hints {
    display: flex;
    gap: 1rem;
    font-size: 0.8rem;
    color: #888;
    flex-wrap: wrap;
}

.hint-item {
    padding: 0.25rem 0.5rem;
    background: #f8f8f8;
    border-radius: 1rem;
}

@media (max-width: 768px) {
    .progress-info {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
    }
    
    .progress-stats {
        gap: 1rem;
    }
    
    .message {
        max-width: 95%;
    }
    
    .input-hints {
        flex-direction: column;
        gap: 0.25rem;
    }
}
```

### 4. 路由配置
```python
# web_gui/routes/requirements_routes.py

from flask import Blueprint, render_template, redirect, url_for, request
from ..services.requirements_service import RequirementsService

requirements_ui_bp = Blueprint('requirements_ui', __name__)
requirements_service = RequirementsService()

@requirements_ui_bp.route('/requirements')
def index():
    """需求分析主页"""
    return render_template('requirements/index.html')

@requirements_ui_bp.route('/requirements/new', methods=['GET', 'POST'])
def new_session():
    """创建新的需求分析会话"""
    if request.method == 'POST':
        project_name = request.form.get('project_name', '新项目')
        
        session = requirements_service.create_session({
            'project_name': project_name,
            'user_context': {}
        })
        
        return redirect(url_for('requirements_ui.chat', session_id=session.id))
    
    return render_template('requirements/new_session.html')

@requirements_ui_bp.route('/requirements/<session_id>')
def chat(session_id):
    """需求分析对话界面"""
    session = requirements_service.get_session(session_id)
    if not session:
        return redirect(url_for('requirements_ui.index'))
    
    messages = [msg.to_dict() for msg in session.messages]
    
    return render_template('requirements/chat.html', 
                         session=session.to_dict(), 
                         messages=messages)
```

## 迭代1测试策略

### API测试覆盖
```python
# tests/api/test_requirements_api.py - 迭代1测试范围

class TestRequirementsAPIIteration1:
    """迭代1 API测试套件"""
    
    def test_create_session_basic(self, client):
        """测试基础会话创建"""
        pass
    
    def test_send_message_and_get_response(self, client, test_session):
        """测试消息发送和AI响应"""
        pass
    
    def test_progress_tracking(self, client, test_session):
        """测试进度跟踪"""
        pass
    
    def test_error_handling(self, client):
        """测试错误处理"""
        pass
```

## 部署配置

### 数据库迁移
```bash
# 创建迭代1需要的表
python scripts/create_requirements_tables.py
```

### 环境变量配置
```bash
# .env 新增配置
REQUIREMENTS_MODULE_ENABLED=true
MIDSCENE_SERVER_URL=http://localhost:3001
```

## 交付时间线

**第1-2天**: 后端API和服务层开发
**第3-4天**: AI引擎集成和midscene服务扩展  
**第5-6天**: 前端界面开发和集成
**第7天**: 测试和调试优化

## 成功标准

1. **功能完整性**: 用户可以创建会话并进行基础对话
2. **AI响应质量**: Mary能够理解用户需求并给出合理回应
3. **界面友好性**: 对话界面直观易用，进度可视化清晰
4. **系统稳定性**: 基础错误处理到位，系统运行稳定
5. **集成无缝**: 与现有Intent Test Framework完全兼容

通过迭代1的实施，用户将能够体验到AI需求分析的核心价值，为后续迭代的功能扩展奠定坚实基础。