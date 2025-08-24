# 故事 1.4: AI配置管理

## 基本信息
- **故事ID**: STORY-01-04
- **所属Epic**: Epic 1: 智能需求分析核心体验
- **优先级**: 中
- **故事点数**: 8
- **复杂度**: 中等
- **状态**: 待开发

## INVEST原则检查
- **Independent**: ✅ 可以独立实现，作为需求分析的配套功能
- **Negotiable**: ✅ 配置界面设计和支持的AI服务商可协商
- **Valuable**: ✅ 让用户能够使用自己的AI服务，提供灵活性价值
- **Estimable**: ✅ 涉及CRUD操作和安全存储，工作量可估算
- **Small**: ✅ 专注于配置管理，规模适中
- **Testable**: ✅ 可通过配置操作和AI连接测试验证

## 用户故事

### 主要故事
**作为** 智能需求分析的使用者
**我希望** 能够配置和管理自己的AI服务参数（API Key、Base URL、模型名称）
**以便** 我可以使用自己的AI服务账户进行需求分析，而不依赖系统默认配置

### 使用场景
用户在进行需求分析前，可以通过配置管理界面添加、编辑和测试自己的AI服务配置。支持OpenAI、DashScope、Claude等多种服务商，用户可以为不同的分析任务选择不同的AI配置。

### 触发条件
- 用户首次使用智能需求分析功能
- 用户点击需求分析界面的"配置"按钮
- 用户需要切换或更新AI服务配置
- AI服务连接异常需要重新配置

### 相关故事
- Story 1.1: AI需求分析对话界面
- Story 1.2: 实时AI回应和澄清引导（使用AI配置）

## 详细描述

### 功能概述
实现AI配置管理的完整功能，包括配置的增删改查、连接测试、使用统计，以及安全的API密钥存储。配置管理作为需求分析的子功能，通过模态框方式集成在主界面中。

### 主要操作流程
1. 用户点击需求分析页面的"配置"按钮
2. 打开AI配置管理模态框
3. 用户可以查看现有配置列表
4. 添加新配置：选择服务商、输入API密钥、Base URL、模型名称
5. 测试配置连接有效性
6. 保存配置并选择为当前使用的配置
7. 关闭模态框，继续需求分析对话

### 用户界面要求
**模态框设计**：
- 700px宽度，自适应高度
- 标题栏包含关闭按钮
- 主体区域分为配置列表和操作区

**配置列表**：
- 列表项显示配置名称、服务商、模型、状态
- 显示使用次数和成功率统计
- 每项包含编辑、测试、删除按钮
- 当前选中配置有明显标识

**配置表单**：
- 服务商选择下拉框（OpenAI、DashScope、Claude、自定义）
- 根据服务商自动填充推荐的Base URL
- 模型名称下拉框，根据服务商动态更新选项
- API密钥密码输入框
- 配置名称和描述文本框
- 测试连接按钮

### 数据处理要求
**数据模型**：
```python
class RequirementsAIConfig(db.Model):
    """需求分析AI配置模型"""
    
    __tablename__ = "requirements_ai_configs"
    
    id = db.Column(db.Integer, primary_key=True)
    config_name = db.Column(db.String(255), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # openai, dashscope, claude, custom
    api_key = db.Column(db.Text, nullable=False)  # 加密存储
    base_url = db.Column(db.String(500))
    model_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    
    # 使用统计
    total_requests = db.Column(db.Integer, default=0)
    successful_requests = db.Column(db.Integer, default=0)
    average_response_time = db.Column(db.Float)
    last_used_at = db.Column(db.DateTime)
    
    # 元数据
    created_by = db.Column(db.String(100), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RequirementsAIUsageLog(db.Model):
    """AI配置使用记录"""
    
    __tablename__ = "requirements_ai_usage_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey("requirements_ai_configs.id"))
    session_id = db.Column(db.String(50))
    request_type = db.Column(db.String(50))  # analysis, clarification
    total_tokens = db.Column(db.Integer)
    response_time = db.Column(db.Float)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**API密钥加密存储**：
```python
from cryptography.fernet import Fernet
import base64

class ConfigEncryption:
    def __init__(self):
        self.key = os.getenv('CONFIG_ENCRYPTION_KEY')
        self.cipher_suite = Fernet(self.key)
    
    def encrypt_api_key(self, api_key: str) -> str:
        """加密API密钥"""
        encrypted_key = self.cipher_suite.encrypt(api_key.encode())
        return base64.urlsafe_b64encode(encrypted_key).decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """解密API密钥"""
        encrypted_data = base64.urlsafe_b64decode(encrypted_key.encode())
        return self.cipher_suite.decrypt(encrypted_data).decode()
```

### 业务规则
**配置管理规则**：
- 每个用户最多可创建10个AI配置
- 必须有一个默认配置，删除默认配置时需指定新的默认配置
- API密钥必须加密存储，界面上只显示部分字符（如sk-****1234）
- 配置测试成功后才能保存

**使用统计规则**：
- 每次AI调用都记录使用情况到usage_log表
- 成功率和平均响应时间每小时更新一次
- 超过30天未使用的配置标记为inactive

## 验收标准

### 主要验收场景

**场景1**: 添加新的AI配置
```gherkin
Given 用户打开AI配置管理界面
When 用户点击"新建配置"按钮
And 选择"OpenAI"服务商
And 输入有效的API密钥和配置信息
And 点击"测试连接"按钮
Then 系统验证连接成功
And 用户点击"保存配置"
And 新配置出现在配置列表中
```

**场景2**: 配置连接测试
```gherkin
Given 用户输入了完整的AI配置信息
When 用户点击"测试连接"按钮
Then 系统使用该配置调用AI服务
And 显示测试进度指示器
And 3秒内返回测试结果（成功或失败）
And 显示响应时间和连接状态
```

**场景3**: 切换当前使用的配置
```gherkin
Given 用户有多个已保存的AI配置
When 用户在需求分析界面的下拉框中选择不同配置
Then 系统切换到新的AI配置
And 状态指示器显示切换成功
And 后续AI对话使用新配置
```

**场景4**: 查看使用统计
```gherkin
Given 配置已被使用多次
When 用户查看配置列表
Then 每个配置显示使用次数、成功率、平均响应时间
And 可以查看最近一周的使用趋势
```

### 边界场景

**边界场景1**: API密钥格式验证
```gherkin
Given 用户输入不符合格式的API密钥
When 用户尝试保存配置
Then 系统显示密钥格式错误提示
And 拒绝保存配置
And 提供正确格式的示例
```

**边界场景2**: 达到配置数量限制
```gherkin
Given 用户已创建了10个AI配置（达到上限）
When 用户尝试创建新配置
Then 系统显示配置数量限制提示
And 建议删除不使用的配置
And 阻止新配置的创建
```

### 异常处理场景

**异常场景1**: 配置测试失败
```gherkin
Given 用户输入了错误的API密钥或配置
When 用户点击测试连接
Then 系统显示具体的错误信息
And 提供问题排查建议
And 允许用户修改配置重新测试
```

**异常场景2**: 配置加密/解密异常
```gherkin
Given 系统在加密API密钥时出现异常
When 用户尝试保存配置
Then 系统显示安全存储异常提示
And 记录详细错误日志
And 引导用户联系技术支持
```

**异常场景3**: 删除正在使用的配置
```gherkin
Given 用户尝试删除当前正在使用的配置
When 用户点击删除按钮
Then 系统显示警告信息
And 要求用户先选择其他配置作为默认
And 确认后才允许删除操作
```

## 非功能性要求

### 性能要求
- 配置列表加载时间 < 1秒
- 配置测试响应时间 < 5秒
- 模态框打开/关闭动画流畅
- 支持配置数据缓存

### 安全要求
- API密钥必须加密存储，使用AES-256加密
- 配置传输过程使用HTTPS
- 实施访问日志记录
- 定期轮换加密密钥
- API密钥在界面上脱敏显示

### 可用性要求
- 配置表单验证即时反馈
- 提供各服务商的配置帮助文档
- 错误信息具体明确，便于排查
- 支持配置的导入/导出功能

### 兼容性要求
- 支持主流AI服务商API格式
- 模态框在不同屏幕尺寸下正常显示
- 兼容现有的认证和权限系统

## 设计注意事项

### UI/UX设计要点
- **极简模态框**：遵循minimal-style设计，简洁不杂乱
- **安全显示**：API密钥脱敏显示（sk-****1234）
- **状态指示**：连接状态用彩色圆点表示
- **操作反馈**：测试连接时显示进度和结果

### 技术实现要点
- **加密存储**：使用Fernet对称加密存储API密钥
- **配置验证**：多层验证确保配置有效性
- **缓存机制**：配置信息缓存减少数据库查询
- **错误处理**：详细的错误分类和处理逻辑

### 数据设计要点
- **外键约束**：与RequirementsSession建立关联
- **索引优化**：在user_id、provider、is_active字段建立索引
- **数据清理**：定期清理过期的使用记录

### 集成要求
- **API设计**：
  - GET /api/requirements/ai-configs - 获取配置列表
  - POST /api/requirements/ai-configs - 创建配置
  - PUT /api/requirements/ai-configs/{id} - 更新配置
  - DELETE /api/requirements/ai-configs/{id} - 删除配置
  - POST /api/requirements/ai-configs/{id}/test - 测试配置
- **AI服务集成**：支持多种服务商的统一调用接口
- **权限集成**：与现有用户权限系统集成

## 测试指导

### 测试重点
1. **配置CRUD操作** - 创建、查询、更新、删除配置
2. **加密安全性** - API密钥加密存储和解密
3. **连接测试功能** - 各种AI服务的连接验证
4. **使用统计准确性** - 统计数据的记录和计算

### 关键测试场景
1. 不同AI服务商的配置和连接测试
2. API密钥的安全存储和脱敏显示测试
3. 配置切换和会话关联测试
4. 异常配置的处理测试
5. 并发用户的配置隔离测试

### 测试数据要求
- 各种AI服务商的有效和无效API密钥
- 不同格式的配置数据
- 边界情况的测试用例
- 加密解密的正确性验证数据

### 自动化测试建议
- 配置CRUD的API测试
- 加密解密功能的单元测试
- AI连接测试的集成测试
- 前端配置界面的E2E测试

### 测试工具建议
- API测试：pytest + requests
- 安全测试：自定义加密测试工具
- 前端测试：Playwright
- 性能测试：locust

## 依赖关系

### 前置故事
- Story 1.1: AI需求分析对话界面（UI集成依赖）

### 技术依赖
- cryptography库用于加密存储
- 各AI服务商的Python SDK或HTTP客户端
- Flask-WTF用于表单验证
- 数据库迁移工具

### 数据依赖
- 数据库迁移脚本（新增配置表）
- 加密密钥的环境变量配置
- AI服务商的配置模板数据

### 外部依赖
- AI服务商API的可用性
- 网络连接质量
- HTTPS证书配置

### 阻塞风险
- AI服务商API变更可能影响兼容性
- 加密密钥管理的复杂性
- 不同AI服务的认证方式差异

## 完成定义

### 开发完成标准
- [ ] 配置CRUD功能完全实现
- [ ] API密钥加密存储功能完成
- [ ] 多AI服务商支持完成
- [ ] 配置测试功能实现
- [ ] 使用统计功能完成
- [ ] 前端模态框界面完成
- [ ] 代码通过同行评审
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过

### 测试完成标准
- [ ] 所有配置操作测试通过
- [ ] 加密安全性测试通过
- [ ] 各AI服务商连接测试通过
- [ ] 异常处理测试通过
- [ ] 性能测试满足要求
- [ ] 安全扫描无高危漏洞

### 文档完成标准
- [ ] AI配置API文档完成
- [ ] 用户配置指南完成
- [ ] 安全配置文档完成
- [ ] 故障排除指南

### 产品负责人验收
- [ ] 配置管理界面易用性满足期望
- [ ] 多AI服务商支持验证完成
- [ ] 安全性和隐私保护符合要求
- [ ] 产品负责人最终验收通过

### 发布就绪标准
- [ ] 功能在测试环境稳定运行48小时
- [ ] 加密密钥管理流程就绪
- [ ] 配置数据备份和恢复方案完成
- [ ] 安全监控告警配置完成

## 备注

这个故事实现了用户自主配置AI服务的核心需求，是整个智能需求分析模块用户友好性的重要保障。需要特别关注安全性，确保用户的API密钥得到妥善保护。

## 变更历史

| 日期 | 版本 | 变更内容 | 变更原因 | 变更人 |
|------|------|----------|----------|--------|
| 2024-01-20 | 1.0 | 初始创建故事文档 | 基于用户自主配置需求 | Scrum Master Bob |