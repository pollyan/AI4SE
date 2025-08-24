# 故事 1.1: AI需求分析对话界面

## 基本信息
- **故事ID**: STORY-01-01
- **所属Epic**: Epic 1: 智能需求分析核心体验
- **优先级**: 高
- **故事点数**: 8
- **复杂度**: 中等
- **状态**: 待开发

## INVEST原则检查
- **Independent**: ✅ 此故事独立，不依赖其他未完成故事
- **Negotiable**: ✅ 实现细节（UI布局、消息格式）可以协商调整
- **Valuable**: ✅ 为用户提供核心价值 - AI辅助需求分析能力
- **Estimable**: ✅ 工作量可估算，涉及前后端开发和AI集成
- **Small**: ✅ 规模适中，一个sprint内可完成
- **Testable**: ✅ 可通过手动测试和API测试验证

## 用户故事

### 主要故事
**作为** 项目经理或产品经理
**我希望** 通过对话界面与AI助手Mary交流我的需求想法
**以便** 我能够以自然的方式描述模糊的需求，并获得AI的专业引导来澄清细节

### 使用场景
用户登录Intent Test Framework后，进入智能需求分析模块，开始新的需求分析会话。用户可以用自然语言描述项目需求，AI Mary会实时回应并提供专业的需求澄清问题。

### 触发条件
- 用户点击"智能需求分析"导航菜单
- 用户点击"新建分析会话"按钮
- 用户输入需求描述并发送消息

### 相关故事
- Story 1.2: 实时AI回应和澄清引导
- Story 1.3: 需求分析进度可视化
- Story 1.4: AI配置管理

## 详细描述

### 功能概述
创建一个基于WebSocket的实时对话界面，用户可以通过自然语言与AI助手Mary进行需求分析对话。界面采用左右分屏布局：左侧为对话区域（60%），右侧为共识达成内容显示（40%）。

### 主要操作流程
1. 用户进入智能需求分析页面
2. 系统自动创建新的需求分析会话
3. AI Mary发送欢迎消息，引导用户开始描述需求
4. 用户在输入框中输入需求描述
5. 点击发送或按Enter键发送消息
6. 系统通过WebSocket将消息发送至后端
7. AI处理消息并返回专业回应
8. 界面实时显示对话内容和AI理解的共识要点

### 用户界面要求
**页面布局**：
- 遵循现有minimal-style极简设计系统
- 左右分屏布局（3:2比例）
- 左侧对话区域高度450px，支持滚动
- 右侧共识区域可视化显示AI理解的要点

**对话界面**：
- 仿聊天应用的消息气泡样式
- 用户消息显示在右侧，AI消息显示在左侧
- 每条消息显示时间戳
- 支持多行文本输入和显示

**交互要求**：
- Enter键发送消息，Shift+Enter换行
- 发送过程中显示AI处理状态
- 支持清空对话历史功能

### 数据处理要求
**数据模型**：
```python
class RequirementsSession(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    project_name = db.Column(db.String(255))
    session_status = db.Column(db.String(50), default='active')
    current_stage = db.Column(db.String(50), default='initial')
    user_context = db.Column(db.Text)  # JSON
    ai_context = db.Column(db.Text)    # JSON
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

class RequirementsMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50))
    message_type = db.Column(db.String(20))  # user, assistant, system
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime)
```

**数据流**：
1. WebSocket接收用户消息 → 存储到RequirementsMessage表
2. 调用AI服务处理消息 → 更新session的ai_context
3. AI返回响应 → 存储AI消息到RequirementsMessage表
4. 通过WebSocket推送AI响应给前端

### 业务规则
- 每个用户可以同时只有一个活跃的需求分析会话
- 会话超时时间为2小时，超时后状态变为paused
- AI响应时间超过30秒显示超时提示
- 用户输入限制在2000字符以内
- 对话历史保存90天，之后归档

## 验收标准

### 主要验收场景

**场景1**: 用户开始新的需求分析对话
```gherkin
Given 用户已登录Intent Test Framework
When 用户点击"智能需求分析"菜单
Then 系统显示需求分析页面
And 自动创建新的分析会话
And AI Mary发送欢迎消息
```

**场景2**: 用户发送需求描述消息
```gherkin
Given 用户在需求分析页面
When 用户在输入框输入"我想开发一个用户登录系统"
And 用户点击发送按钮
Then 消息出现在对话区域
And 显示AI处理状态
And AI在3秒内返回专业回应
And 右侧显示更新的共识内容
```

**场景3**: 实时对话体验
```gherkin
Given 用户正在与AI对话
When 用户连续发送多条消息
Then 每条消息都能正确显示和处理
And 对话历史按时间顺序显示
And WebSocket连接保持稳定
```

### 边界场景

**边界场景1**: 长消息处理
```gherkin
Given 用户在输入框中输入1500字符的长消息
When 用户点击发送
Then 消息能够完整发送和显示
And AI能够正确处理长文本
```

**边界场景2**: 快速连续发送
```gherkin
Given 用户快速连续点击发送按钮3次
When 系统处理这些请求
Then 每个消息都被正确处理
And 不出现消息重复或丢失
```

### 异常处理场景

**异常场景1**: WebSocket连接断开
```gherkin
Given 用户正在对话过程中
When WebSocket连接意外断开
Then 系统显示连接断开提示
And 自动尝试重新连接
And 恢复连接后保持会话状态
```

**异常场景2**: AI服务响应超时
```gherkin
Given 用户发送了一条消息
When AI服务30秒内未响应
Then 显示"AI正在思考，请稍候"提示
And 60秒后显示超时错误信息
And 提供重试选项
```

**异常场景3**: 超长输入限制
```gherkin
Given 用户尝试输入超过2000字符的消息
When 用户点击发送
Then 显示字符数限制提示
And 拒绝发送消息
And 提供文本截断建议
```

## 非功能性要求

### 性能要求
- WebSocket消息传输延迟 < 100ms
- AI响应时间90%情况下 < 5秒
- 页面加载时间 < 2秒
- 支持并发用户数 > 50

### 安全要求
- WebSocket连接使用WSS加密传输
- 用户消息内容进行XSS防护
- 会话数据加密存储
- 实施输入内容长度和格式验证

### 可用性要求
- 界面遵循无障碍设计原则
- 支持键盘快捷键操作
- 提供清晰的加载和错误状态提示
- 移动端响应式适配

### 兼容性要求
- 支持Chrome 90+, Firefox 88+, Safari 14+
- 支持1920x1080和1366x768分辨率
- 移动端支持iOS Safari和Android Chrome

## 设计注意事项

### UI/UX设计要点
- **极简设计原则**: 遵循现有minimal-style，无图标纯文本界面
- **布局比例**: 左侧对话区占3列，右侧共识区占2列（使用CSS Grid）
- **状态指示**: 使用彩色圆点表示当前分析阶段和AI状态
- **消息设计**: 用户消息浅灰背景，AI消息白色背景，系统消息蓝色背景
- **输入体验**: 多行文本框，支持回车发送和清空功能

### 技术实现要点
- **WebSocket集成**: 使用Flask-SocketIO实现实时通信
- **AI服务调用**: 复用现有midscene_server.js，扩展需求分析端点
- **状态管理**: 前端维护会话状态，后端持久化会话数据
- **错误处理**: 实现重连机制和超时处理
- **性能优化**: 对话历史分页加载，避免长会话造成页面卡顿

### 数据设计要点
- **会话模型**: 使用UUID作为会话ID，支持会话恢复
- **消息存储**: JSON格式存储AI上下文，便于后续分析
- **索引设计**: 在session_id和created_at字段建立索引
- **数据清理**: 定期归档超过90天的历史对话

### 集成要求
- **API设计**: 
  - POST /api/requirements/sessions - 创建会话
  - WebSocket /ws/requirements/<session_id> - 实时通信
  - GET /api/requirements/sessions/<session_id> - 获取会话详情
- **AI服务集成**: 通过HTTP调用midscene_server.js的需求分析端点
- **现有系统集成**: 复用authentication、database_service等现有组件

## 测试指导

### 测试重点
1. **WebSocket通信稳定性** - 连接建立、消息传输、异常重连
2. **AI集成正确性** - 消息格式、响应处理、错误处理
3. **用户界面交互** - 消息显示、输入体验、状态反馈
4. **会话状态管理** - 创建、更新、恢复、超时处理

### 关键测试场景
1. 新用户首次使用流程测试
2. 长时间对话会话稳定性测试
3. 网络中断重连功能测试
4. 多用户并发对话测试
5. AI服务异常情况处理测试

### 测试数据要求
- 准备多种类型的需求描述文本（简单、复杂、模糊、技术性）
- 模拟不同长度的用户输入（短消息、长消息、超长消息）
- 准备AI服务的模拟响应数据
- 创建不同状态的测试会话数据

### 自动化测试建议
- API测试：会话CRUD操作、消息存储和检索
- WebSocket测试：连接建立、消息传输、异常处理
- 前端单元测试：消息组件、输入验证、状态管理
- 端到端测试：完整对话流程的自动化验证

### 测试工具建议
- API测试：pytest + requests
- WebSocket测试：pytest + websocket-client
- 前端测试：Jest + Testing Library
- 端到端测试：Playwright或Cypress

## 依赖关系

### 前置故事
无（这是Epic 1的第一个故事）

### 技术依赖
- Flask-SocketIO库安装和配置
- 现有数据库服务和模型系统
- midscene_server.js AI服务端点扩展
- minimal-style.css设计系统

### 数据依赖
- 数据库迁移脚本执行（新增RequirementsSession和RequirementsMessage表）
- AI配置的环境变量设置

### 外部依赖
- AI服务提供商（OpenAI、DashScope等）的API可用性
- WebSocket代理配置（如使用Nginx）

### 阻塞风险
- AI服务配额限制可能影响测试
- WebSocket在某些网络环境下的连通性问题
- 新数据模型可能与现有系统存在冲突

## 完成定义

### 开发完成标准
- [ ] 前端对话界面开发完成，支持实时消息传输
- [ ] 后端WebSocket服务实现，支持会话和消息管理
- [ ] AI服务集成完成，能够处理需求分析请求
- [ ] 数据模型创建和迁移完成
- [ ] 代码通过同行评审
- [ ] 单元测试编写完成，覆盖率 > 80%
- [ ] 集成测试通过
- [ ] 代码符合项目编码规范

### 测试完成标准
- [ ] 所有验收标准测试通过
- [ ] WebSocket连接稳定性测试通过
- [ ] AI集成功能测试通过
- [ ] 异常处理测试通过（网络断开、AI超时等）
- [ ] 性能测试满足要求（响应时间、并发数）
- [ ] 安全测试通过（XSS防护、数据加密）

### 文档完成标准
- [ ] API文档更新（WebSocket事件、REST端点）
- [ ] 数据模型文档更新
- [ ] 部署和配置文档更新

### 产品负责人验收
- [ ] 对话界面交互体验满足期望
- [ ] AI回应质量满足基本要求
- [ ] 功能演示通过
- [ ] 产品负责人最终验收

### 发布就绪标准
- [ ] 功能在测试环境稳定运行48小时
- [ ] 数据库迁移脚本测试完成
- [ ] WebSocket服务监控配置完成
- [ ] 回滚方案准备就绪

## 备注

这是智能需求分析模块的核心基础故事，为后续的澄清引导、文档生成等高级功能奠定基础。实现时需要特别关注WebSocket连接的稳定性和AI集成的可靠性。

## 变更历史

| 日期 | 版本 | 变更内容 | 变更原因 | 变更人 |
|------|------|----------|----------|--------|
| 2024-01-20 | 1.0 | 初始创建故事文档 | 基于迭代1实施计划和架构设计 | Scrum Master Bob |