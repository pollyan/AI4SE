# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🔴 CRITICAL 安全规则（绝对禁止）

### 数据库操作安全规则

**⚠️ 绝对禁止执行以下操作，违者后果严重：**

1. **禁止删除数据库内容**：
   - ❌ 绝对禁止执行 `db.drop_all()`
   - ❌ 绝对禁止执行 `DROP TABLE` 任何表
   - ❌ 绝对禁止执行 `DELETE FROM` 无条件删除
   - ❌ 绝对禁止执行 `TRUNCATE TABLE` 任何表
   - ❌ 绝对禁止清空数据库或重置数据库

2. **禁止破坏性操作**：
   - ❌ 在没有明确用户确认的情况下，执行任何可能丢失数据的操作
   - ❌ 在生产环境或包含真实数据的环境中执行数据清理
   - ❌ 执行任何形式的"清空并重建"操作

3. **数据库操作原则**：
   - ✅ 只读操作可以安全执行（SELECT, 查询表结构等）
   - ✅ 如果需要创建表，使用 `IF NOT EXISTS` 条件
   - ✅ 任何写入操作前必须先征得用户明确同意
   - ✅ 遇到数据问题时，优先查询和诊断，而非删除重建

**后果警示**：违反此规则会导致用户重要配置、测试数据、会话历史等丢失，造成不可挽回的损失。

## 沟通指导原则

**语言**：在此项目中工作时始终使用中文回应。除非特别要求，否则所有沟通、解释和文档都应使用中文。

## 项目概述

这是Intent Test Framework（意图测试框架）- 一个由AI驱动的Web自动化测试平台，为测试用例管理、执行监控和结果分析提供完整的WebUI界面。系统使用MidSceneJS进行AI驱动的视觉测试，支持自然语言测试描述。

## 特别强调（重要）
- 问题再困难也不要做违反架构原则与最佳实践的代码和设计
- 在实际的业务功能中不要有任何的模拟数据，模拟功能
- 完成任务之后，要详细验证结果，之后再给出确定的反馈，不能猜测，要有确实的根据
- 修改完业务功能后，本地运行API测试来保证功能正确
- 每当开始一个新的涉及到用户交互的功能开发，先在minimal-preview这里产出html的设计，与我确认之后再开始开发

## 核心开发命令

### 测试执行（重要）
```bash
# 快速本地测试套件运行（推荐用法）
./scripts/test-local.sh --fast --parallel

# 完整测试套件（提交前必须运行）
./scripts/test-local.sh --clean --open-coverage

# 仅运行API测试
pytest tests/api/ -v

# 运行特定测试文件
pytest tests/api/test_testcase_api.py -v

# 并行测试（需要pytest-xdist）
pytest tests/api/ -n auto -v

# 生成覆盖率报告
pytest tests/api/ --cov=web_gui --cov-report=html --cov-report=term
```

### 环境设置
```bash
# 自动设置开发环境
python scripts/setup_dev_env.py

# 手动安装测试依赖
./scripts/install-test-deps.sh

# 配置环境变量
cp .env.example .env  # 然后编辑.env填入API密钥
```

### 应用启动
```bash
# 启动AI引擎服务
node midscene_server.js

# 启动Web应用
python web_gui/run_enhanced.py
```

### 代码质量
```bash
# 运行质量检查
python scripts/quality_check.py --fix

# 性能基准测试
python scripts/benchmark.py --parallel --save
```

## 架构概览

### 核心架构模式
- **微服务分离**: Flask Web应用 + Node.js AI服务器
- **API优先**: 完全模块化的REST API架构（`web_gui/api/`）
- **服务层抽象**: 业务逻辑封装在服务层（`web_gui/services/`）
- **测试驱动**: API集成测试覆盖所有端点，已移除单元测试

### 关键组件理解

#### 1. Web GUI层 (`web_gui/`)
- **`app_enhanced.py`**: Flask应用工厂，统一的应用程序入口
- **`api/`**: 模块化API端点，每个资源独立文件
  - `testcases.py`: 测试用例CRUD操作，支持活跃/非活跃状态管理
  - `executions.py`: 执行历史和监控
  - `statistics.py`: 仪表板统计数据
- **`services/`**: 业务逻辑服务层
  - `execution_service.py`: 测试执行引擎
  - `variable_resolver_service.py`: 变量解析和上下文管理
  - `database_service.py`: 统一数据库访问层

#### 2. AI引擎层
- **`midscene_server.js`**: Node.js AI操作服务器
- **`midscene_python.py`**: Python-JavaScript桥接层
- **MidSceneJS集成**: 支持AI视觉识别和自然语言测试

#### 3. 数据库架构
- **核心模型**: `TestCase`, `ExecutionHistory`, `StepExecution` 
- **关系**: TestCase (1:N) ExecutionHistory (1:N) StepExecution
- **变量系统**: 支持 `${variable}` 语法和上下文传递

### 测试架构（已重构）

**重要变更**: 已完全移除单元测试，采用API集成测试架构

#### 测试结构
- **`tests/api/`**: 完整API集成测试套件（163个测试）
- **`tests/proxy/`**: Node.js微服务测试
- **`tests/conftest.py`**: 全局测试配置和固件

#### 测试数据管理
- **代理对象模式**: `tests/api/test_data_manager.py` 提供TestCaseProxy等代理类
- **向后兼容**: 支持字典访问（`data['name']`）和属性访问（`data.name`）
- **灵活创建**: `create_test_testcase` fixture支持参数覆盖

#### 关键测试固件
```python
# tests/api/conftest.py 核心固件
@pytest.fixture
def assert_api_response():
    """智能API响应验证，支持成功和错误场景"""
    
@pytest.fixture  
def create_test_testcase():
    """创建测试用例，支持is_active等参数"""
```

## 业务逻辑规则

### 测试用例状态管理
- **Inactive测试用例**: 可以访问和查看，用户可以重新激活
- **删除操作**: 防重复删除，已删除的测试用例再次删除返回404
- **状态字段**: `is_active` 字段控制测试用例的活跃状态

### API响应格式
```json
{
  "code": 200,
  "message": "success", 
  "data": {...}
}
```

### 变量系统
- **语法**: `${variable_name}` 或 `${object.property}`
- **上下文传递**: 步骤间变量自动传递
- **输出变量**: 支持 `output_variable` 参数

## CI/CD配置

### GitHub Actions
- **自动触发**: 推送到master/main/develop分支或PR
- **多阶段检查**: 测试、代码质量、安全扫描、性能测试
- **覆盖率报告**: 自动生成并评论到PR

### 本地验证工作流
```bash
# 1. 开发时快速验证
./scripts/test-local.sh --fast

# 2. 提交前完整检查  
./scripts/test-local.sh --clean --open-coverage
python scripts/quality_check.py --fix

# 3. 性能基准测试
python scripts/benchmark.py --save
```

## 设计系统

### 极简设计原则
参考 `minimal-preview/` 目录中的设计系统：
- **无图标**: 纯文本界面，不使用emoji或符号
- **一致组件**: 标准化的按钮、表单、列表项样式
- **状态指示**: 使用彩色圆点表示状态
- **网格布局**: 一致的内容组织结构

### UI组件标准
```html
<!-- 列表项标准结构 -->
<div class="list-item" onclick="editItem(id)">
    <div class="list-item-content">
        <div class="list-item-title">标题</div>
        <div class="list-item-subtitle">副标题</div>
    </div>
    <div class="flex items-center gap-1">
        <button onclick="event.stopPropagation(); action()">操作</button>
        <div class="status status-success"></div>
    </div>
</div>
```

## 开发指导原则

### 架构优先原则
- **服务层抽象**: 业务逻辑必须封装在services层
- **DRY原则**: 避免重复代码，统一的错误处理和数据访问
- **数据库访问**: 使用DatabaseService，不直接写SQL

### 测试驱动开发
- **API测试优先**: 所有新API必须有对应测试
- **测试数据管理**: 使用test_data_manager的代理对象
- **覆盖率要求**: API测试覆盖率100%，整体覆盖率≥80%

### 代码质量标准
```bash
# 提交前必须运行
python scripts/quality_check.py --fix
./scripts/test-local.sh --clean
```

### 提交规范
```
<type>(<scope>): <subject>

# 示例
feat(api): 添加测试用例模板功能
fix(tests): 修复API测试数据结构问题
refactor(services): 重构执行服务架构
```

## 环境配置

### 必需环境变量
```env
# AI服务配置
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # 推荐DashScope
MIDSCENE_MODEL_NAME=qwen-vl-max-latest

# 数据库
DATABASE_URL=postgresql://... # 生产环境
DATABASE_URL=sqlite:///./intent_test_framework.db # 开发环境

# 应用配置
SECRET_KEY=your_secret_key
DEBUG=true  # 开发环境
```

### AI模型支持
- **主要**: Qwen VL (DashScope) - `qwen-vl-max-latest`
- **备选**: GPT-4V (OpenAI) - `gpt-4o`

## 重要禁止事项

### 测试架构
- **禁止创建单元测试**: 已移除`tests/unit/`，专注API集成测试
- **禁止返回假数据**: API必须返回真实数据库数据或明确错误

### 代码架构
- **禁止绕过服务层**: API控制器中不直接写数据库操作
- **禁止重复代码**: 特别是数据库连接、错误处理逻辑
- **严格禁止Mock功能**: Mock只能在测试代码中使用，业务逻辑中绝对不允许出现任何模拟、虚假功能。系统所有功能都必须是真实可用的功能

### UI设计
- **禁止使用图标**: 保持纯文本极简风格
- **禁止偏离设计系统**: 必须参考minimal-preview设计

## 常见任务模式

### 添加新API端点
1. 在 `web_gui/api/` 创建端点文件
2. 在 `tests/api/` 创建对应测试文件
3. 使用 `test_data_manager` 创建测试数据
4. 遵循标准API响应格式

### 修改现有功能
1. 先运行相关测试确保当前状态正确
2. 修改代码实现
3. 更新对应测试
4. 运行完整测试套件验证

### 调试测试失败
```bash
# 查看详细失败信息
pytest tests/api/test_specific.py -v -s

# 使用本地测试脚本
./scripts/test-local.sh --verbose
```

通过遵循这些指导原则，可以高效地在Intent Test Framework中进行开发，维持高质量的代码和稳定的架构。