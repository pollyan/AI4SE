# MidSceneJS Demo - 完全AI驱动的Web UI自动化测试

这是一个展示Python + MidSceneJS集成的演示项目，**完全依赖AI功能**，不使用任何传统的元素定位方法。

## 🚀 项目特色

### 🤖 纯AI驱动架构
- **完全依赖AI**: 所有测试操作通过自然语言指令完成
- **零传统方法**: 不使用CSS选择器、XPath或其他传统定位方式  
- **智能交互**: AI理解页面内容并自主执行操作
- **自然语言**: 测试脚本使用人类语言描述测试步骤

### 🔧 技术架构
- **Python + Node.js**: Python测试框架 + Node.js MidSceneJS服务器
- **HTTP API**: 通过RESTful API实现跨语言AI调用
- **通义千问VL**: 使用阿里云大模型进行视觉理解
- **实时报告**: 生成详细的AI操作报告和截图

## 📋 系统要求

- Python 3.8+
- Node.js 16+
- 有效的通义千问API密钥

## ⚡ 快速开始

### 1. 环境配置
```bash
# 克隆项目
git clone <项目地址>
cd midscenejs-demo

# 一键安装环境
python setup.py
```

### 2. 配置API密钥
```bash
# 复制环境变量模板
cp env.example .env

# 编辑.env文件，设置你的API密钥
OPENAI_API_KEY=your_qwen_api_key_here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest
MIDSCENE_USE_QWEN_VL=1
```

### 3. 运行纯AI测试
```bash
# 设置环境变量并运行测试
export OPENAI_API_KEY=your_api_key
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export MIDSCENE_MODEL_NAME=qwen-vl-max-latest
export MIDSCENE_USE_QWEN_VL=1

# 运行所有AI测试
pytest tests/test_ai_only.py -v -s
```

## 🤖 AI功能演示

### 完全AI驱动的测试示例
```python
def test_ai_baidu_search_workflow(self):
    """完整的AI驱动百度搜索工作流"""
    
    # AI导航
    self.ai.goto("https://www.baidu.com")
    
    # AI输入 - 自然语言描述输入框
    self.ai.ai_input("MidSceneJS AI自动化", "搜索框")
    
    # AI点击 - 自然语言描述按钮
    self.ai.ai_tap("百度一下按钮")
    
    # AI等待 - 智能判断页面状态
    self.ai.ai_wait_for("搜索结果页面已加载完成")
    
    # AI断言 - 智能验证页面内容
    self.ai.ai_assert("页面显示了关于MidSceneJS的搜索结果")
```

### AI数据提取
```python
# AI提取结构化数据
search_results = self.ai.ai_query(
    "提取前5个搜索结果的标题和摘要，返回JSON格式的数组"
)

# AI分析页面统计
page_stats = self.ai.ai_query(
    "分析当前搜索结果页面，提取搜索关键词、结果数量等统计信息"
)
```

## 📊 测试结果

最新测试结果（完全AI驱动）：
- ✅ **AI搜索工作流测试**: 通过
- ✅ **AI数据提取测试**: 通过  
- ✅ **AI页面交互测试**: 通过
- ✅ **AI滚动探索测试**: 通过
- ⚠️ **AI多步骤工作流**: 部分通过（超时限制）

**成功率: 80% (4/5)**

## 🏗️ 项目结构

```
midscenejs-demo/
├── midscene_python.py          # Python AI封装类
├── midscene_server.js          # Node.js AI服务器
├── tests/
│   ├── conftest.py            # pytest配置
│   └── test_ai_only.py        # 纯AI测试用例
├── screenshots/               # AI测试截图
├── midscene_run/             # MidSceneJS报告
├── requirements.txt          # Python依赖
├── package.json             # Node.js依赖
└── setup.py                # 环境安装脚本
```

## 🎯 AI功能列表

### 核心AI操作
- `ai_input(text, locate_prompt)` - AI智能输入
- `ai_tap(prompt)` - AI智能点击
- `ai_query(prompt)` - AI数据提取
- `ai_assert(prompt)` - AI智能断言
- `ai_action(prompt)` - AI通用操作
- `ai_wait_for(prompt)` - AI智能等待
- `ai_scroll(direction, type)` - AI智能滚动

### 特色功能
- 🧠 **自然语言理解**: 完全使用人类语言描述操作
- 👁️ **视觉理解**: AI通过截图理解页面内容
- 🎯 **智能定位**: 无需CSS选择器，AI自动识别元素
- 📊 **数据提取**: AI提取并结构化页面数据
- ✅ **智能断言**: AI理解页面状态并进行验证

## 🔧 技术细节

### AI服务器架构
- **Express.js服务器**: 提供RESTful API接口
- **PlaywrightAgent**: MidSceneJS核心AI代理
- **环境隔离**: 每个测试独立的浏览器环境
- **错误处理**: 详细的AI操作错误反馈

### Python客户端
- **HTTP通信**: 通过requests与AI服务器通信
- **同步接口**: 简化的同步API调用
- **结果处理**: 智能处理AI返回结果

## 📈 AI模型支持

- ✅ **通义千问VL** (推荐)
- ✅ **GPT-4o**
- ✅ **Gemini Vision**
- ✅ **其他兼容OpenAI API的视觉模型**

## 🎯 使用场景

### 适合的测试场景
- 🎨 **复杂UI交互**: AI理解视觉元素
- 📊 **数据验证**: AI提取和验证数据
- 🔄 **工作流测试**: AI执行复杂业务流程
- 🌐 **跨浏览器测试**: AI适应不同页面结构

### 优势
- 🚀 **快速开发**: 无需编写复杂选择器
- 🛡️ **稳定性强**: AI适应页面变化
- 📝 **易于维护**: 自然语言描述易读易改
- 🎯 **高准确性**: 视觉理解提供准确定位

## 🔍 报告和日志

### 测试输出
- 📸 **自动截图**: 每个测试步骤自动截图记录
- 📊 **AI报告**: MidSceneJS生成详细HTML报告
- 📝 **详细日志**: AI操作的完整日志记录

### 查看报告
```bash
# 查看截图
ls screenshots/

# 查看AI报告
open midscene_run/report/*.html
```

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [MidSceneJS](https://github.com/web-infra-dev/midscene) - 强大的AI自动化框架
- [Playwright](https://playwright.dev/) - 现代化的浏览器自动化工具
- [通义千问](https://dashscope.aliyuncs.com/) - 优秀的视觉理解大模型

---

⭐ 如果这个项目对你有帮助，请给它一个星标！

🤖 **纯AI驱动，零传统方法，开启智能化测试新时代！** 