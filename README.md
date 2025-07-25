# 意图测试平台

![Python Tests (Unit + API)](https://github.com/pollyan/intent-test-framework/actions/workflows/python-tests.yml/badge.svg)
[![codecov](https://codecov.io/gh/pollyan/intent-test-framework/branch/master/graph/badge.svg)](https://codecov.io/gh/pollyan/intent-test-framework)
![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)

一个基于AI的意图驱动Web自动化测试框架，提供完整的WebUI界面用于测试用例管理、执行监控和结果分析。

## 项目特色

### AI驱动的测试自动化
- **智能元素识别**: 使用AI视觉模型自动识别页面元素
- **自然语言测试**: 支持用自然语言描述测试步骤
- **智能断言**: AI自动验证页面状态和内容
- **自适应执行**: 根据页面变化自动调整测试策略

### 完整的WebUI管理界面
- **测试用例管理**: 可视化创建、编辑、组织测试用例
- **实时执行监控**: WebSocket实时显示执行状态和日志
- **截图历史**: 每个步骤自动截图，支持缩略图查看
- **测试报告**: 详细的执行报告和历史记录

### 强大的技术架构
- **分层架构**: 清晰的表现层、业务逻辑层、数据访问层分离
- **实时通信**: Flask + Socket.IO 实现实时状态更新
- **AI引擎集成**: 支持多种AI模型（Qwen VL、GPT-4V等）
- **浏览器支持**: 支持可视化和无头模式执行

## 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- 现代浏览器

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/pollyan/intent-test-framework.git
cd intent-test-framework
```

2. **自动设置开发环境**
```bash
python scripts/setup_dev_env.py
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑.env文件，填入您的AI API配置
```

4. **启动服务**
```bash
# 启动MidScene服务
node midscene_server.js

# 启动Web应用
python web_gui/run_enhanced.py
```

5. **访问应用**
```
http://localhost:5001
```

## 核心功能

### 意图驱动测试
```python
# 示例：自然语言测试用例
steps = [
    {
        "action": "navigate",
        "params": {"url": "https://example.com"}
    },
    {
        "action": "ai_input",
        "params": {
            "element": "搜索框",
            "text": "AI测试"
        }
    },
    {
        "action": "ai_tap", 
        "params": {"element": "搜索按钮"}
    },
    {
        "action": "ai_assert",
        "params": {"assertion": "页面显示搜索结果"}
    }
]
```

### 实时监控
- **执行状态**: 实时显示测试执行进度
- **步骤日志**: 详细的步骤执行日志
- **错误捕获**: 自动捕获和显示执行错误
- **性能监控**: 步骤执行时间统计

### 可视化调试
- **步骤截图**: 每个步骤自动截图保存
- **缩略图历史**: 网格显示所有步骤截图
- **全屏查看**: 点击缩略图查看完整截图
- **失败分析**: 快速定位失败步骤

## 项目架构

```
intent-test-framework/
├── web_gui/                   # Web界面核心模块
│   ├── templates/             # HTML模板
│   ├── static/               # 静态资源
│   ├── app_enhanced.py       # 主应用
│   ├── api_routes.py         # API路由
│   ├── models.py             # 数据模型
│   └── run_enhanced.py       # 启动脚本
├── scripts/                  # 工具脚本
│   ├── quality_check.py      # 代码质量检查
│   ├── setup_dev_env.py      # 开发环境设置
│   └── setup_git_hooks.sh    # Git钩子设置
├── tests/                    # 测试文件
├── PRD/                      # 产品需求文档
├── PROJECT_RULES.md          # 项目规则
├── DEVELOPMENT_GUIDE.md      # 开发指南
└── midscene_python.py        # AI引擎接口
```

## 开发指南

### 代码质量
```bash
# 运行质量检查
python scripts/quality_check.py

# 自动修复格式问题
python scripts/quality_check.py --fix
```

### 提交规范
```bash
# 提交信息格式
<type>(<scope>): <subject>

# 示例
feat(webui): 添加截图历史功能
fix(api): 修复测试用例删除接口错误
docs(readme): 更新安装说明
```

### 测试
```bash
# 运行测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_models.py
```

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 遵循代码规范
4. 编写测试
5. 提交更改 (`git commit -m 'feat: add amazing feature'`)
6. 推送分支 (`git push origin feature/amazing-feature`)
7. 创建Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [MidScene](https://midscenejs.com/) - AI视觉测试引擎
- [Flask](https://flask.palletsprojects.com/) - Web框架
- [Socket.IO](https://socket.io/) - 实时通信
- [Playwright](https://playwright.dev/) - 浏览器自动化

## 支持

如有问题或建议，请：
1. 查看[开发指南](DEVELOPMENT_GUIDE.md)
2. 查看[项目规则](PROJECT_RULES.md)
3. 创建[Issue](https://github.com/pollyan/intent-test-framework/issues)
4. 联系维护者

---

**意图测试平台** - 让AI驱动的Web测试变得简单而强大！
