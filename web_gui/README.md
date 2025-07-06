# AI Web测试用例管理系统

基于MidSceneJS AI框架的Web GUI测试用例管理系统，允许用户通过自然语言描述创建和执行Web自动化测试用例。

## 🌟 系统特色

### 🤖 AI驱动的测试用例生成
- **自然语言输入**: 用户用日常语言描述测试场景
- **智能步骤生成**: AI自动解析并生成结构化测试步骤
- **可视化编辑**: 直观的Web界面展示和编辑测试步骤

### 🎯 完整的测试管理
- **用例管理**: 创建、编辑、删除、分类管理测试用例
- **执行监控**: 实时查看测试执行过程和日志
- **结果分析**: 详细的执行报告和截图记录
- **历史追踪**: 完整的执行历史和状态跟踪

### 🔧 技术架构
- **前端**: Bootstrap + JavaScript (响应式Web界面)
- **后端**: Flask + SQLAlchemy (RESTful API)
- **AI引擎**: MidSceneJS + 通义千问VL
- **数据库**: SQLite (轻量级本地存储)

## 📋 系统要求

- Python 3.8+
- Node.js 16+
- 有效的通义千问API密钥

## ⚡ 快速开始

### 1. 环境准备

```bash
# 确保已安装Python和Node.js依赖
cd AI-WebUIAuto-slh

# 安装Python依赖
pip install -r web_gui/requirements.txt

# 安装Node.js依赖（如果还没有安装）
npm install
```

### 2. 配置API密钥

```bash
# 设置环境变量
export OPENAI_API_KEY=your_qwen_api_key_here
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export MIDSCENE_MODEL_NAME=qwen-vl-max-latest
export MIDSCENE_USE_QWEN_VL=1

# 或者创建.env文件
cp env.example .env
# 编辑.env文件设置你的API密钥
```

### 3. 启动系统

```bash
# 一键启动（推荐）
python web_gui/start_web_gui.py

# 或者手动启动
# 终端1: 启动MidSceneJS服务器
node midscene_server.js

# 终端2: 启动Web GUI
cd web_gui
python app.py
```

### 4. 访问系统

打开浏览器访问: http://localhost:5000

## 🎮 使用指南

### 创建测试用例

1. **点击"创建测试用例"按钮**
2. **填写基本信息**:
   - 测试用例名称
   - 用例描述（可选）
   - 目标网址（可选）

3. **输入自然语言测试描述**:
```
访问百度首页
在搜索框中输入"人工智能"
点击搜索按钮
等待搜索结果加载完成
验证页面显示了相关的搜索结果
提取前5个搜索结果的标题
```

4. **AI自动生成测试步骤**
5. **保存并执行测试用例**

### 自然语言描述示例

#### 基础搜索测试
```
1. 在搜索框输入"机器学习"
2. 点击搜索按钮
3. 等待页面加载完成
4. 验证搜索结果包含相关内容
5. 提取搜索结果数量
```

#### 登录流程测试
```
1. 点击登录按钮
2. 在用户名框输入"testuser"
3. 在密码框输入"password123"
4. 点击提交按钮
5. 等待页面跳转
6. 验证登录成功
```

#### 表单填写测试
```
1. 填写姓名字段为"张三"
2. 选择性别为"男"
3. 填写邮箱为"test@example.com"
4. 填写电话为"13800138000"
5. 点击提交按钮
6. 验证提交成功提示
```

### 支持的操作类型

| 操作类型 | 自然语言关键词 | 示例 |
|---------|---------------|------|
| 输入文本 | 输入、填写、搜索 | "在搜索框输入关键词" |
| 点击元素 | 点击、按、选择 | "点击登录按钮" |
| 等待条件 | 等待、加载 | "等待页面加载完成" |
| 验证断言 | 验证、检查、确认 | "验证页面显示成功信息" |
| 数据提取 | 提取、获取、查询 | "提取搜索结果标题" |
| 页面滚动 | 滚动、下拉、上拉 | "向下滚动页面" |

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web前端界面    │    │   Flask后端API   │    │  MidSceneJS AI  │
│                │    │                │    │                │
│ - 用例编辑器     │◄──►│ - 用例管理API    │◄──►│ - AI操作引擎     │
│ - 执行监控面板   │    │ - 测试执行API    │    │ - 浏览器控制     │
│ - 结果查看器     │    │ - 结果管理API    │    │ - 视觉理解       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   SQLite数据库   │
                       │                │
                       │ - 测试用例表     │
                       │ - 执行记录表     │
                       │ - 结果数据表     │
                       └─────────────────┘
```

## 📊 数据模型

### 测试用例表 (TestCase)
- id: 主键
- name: 用例名称
- description: 用例描述
- natural_language_input: 自然语言输入
- generated_steps: AI生成的步骤(JSON)
- target_url: 目标网址
- status: 状态(draft/ready/running/completed/failed)
- created_at/updated_at: 时间戳

### 执行记录表 (TestExecution)
- id: 主键
- test_case_id: 关联的测试用例ID
- execution_id: 执行UUID
- status: 执行状态
- start_time/end_time: 执行时间
- result: 执行结果(JSON)
- logs: 执行日志
- screenshots: 截图路径列表
- error_message: 错误信息

## 🔧 API接口

### 测试用例管理
- `GET /api/test-cases` - 获取所有测试用例
- `POST /api/test-cases` - 创建新测试用例
- `GET /api/test-cases/{id}` - 获取单个测试用例
- `PUT /api/test-cases/{id}` - 更新测试用例
- `DELETE /api/test-cases/{id}` - 删除测试用例

### 测试执行
- `POST /api/test-cases/{id}/execute` - 执行测试用例
- `GET /api/executions/{execution_id}` - 获取执行状态
- `GET /api/executions/{execution_id}/logs` - 获取执行日志

## 🎯 高级功能

### AI增强解析
- 智能识别测试意图
- 自动优化步骤顺序
- 上下文相关的元素定位
- 错误处理和重试机制

### 批量执行
- 选择多个测试用例批量执行
- 并发执行控制
- 执行队列管理
- 批量结果报告

### 测试报告
- 详细的HTML报告
- 步骤级别的截图
- 执行时间统计
- 成功率分析

## 🔍 故障排除

### 常见问题

1. **AI服务连接失败**
   - 检查API密钥是否正确
   - 确认网络连接正常
   - 验证MidSceneJS服务器是否运行

2. **测试执行失败**
   - 检查目标网站是否可访问
   - 确认测试步骤描述是否清晰
   - 查看执行日志获取详细错误信息

3. **页面加载问题**
   - 检查浏览器是否正确启动
   - 确认端口5000和3001未被占用
   - 清除浏览器缓存重试

### 日志查看
```bash
# Web GUI日志
tail -f web_gui/logs/app.log

# MidSceneJS服务器日志
tail -f midscene_run/log/*.log
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](../LICENSE) 文件了解详情

---

⭐ 如果这个项目对你有帮助，请给它一个星标！

🤖 **AI驱动，自然语言测试，开启智能化测试新时代！**
