# 开发指南

## 📋 快速开始

### 1. 环境设置
```bash
# 克隆项目
git clone <repository-url>
cd AI-WebUIAuto

# 自动设置开发环境
python scripts/setup_dev_env.py

# 手动设置（可选）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

pip install -r requirements.txt
npm install
```

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入正确的配置
# 特别是OPENAI_API_KEY和OPENAI_BASE_URL
```

### 3. 启动应用
```bash
# 启动MidScene服务
node midscene_server.js

# 启动Web应用
python web_gui/run_enhanced.py

# 访问应用
open http://localhost:5001
```

## 🛠️ 开发工作流

### 分支管理
```bash
# 创建功能分支
git checkout -b feature/your-feature-name

# 开发完成后
git add .
git commit -m "feat(scope): 功能描述"
git push origin feature/your-feature-name

# 创建Pull Request
```

### 代码质量检查
```bash
# 运行完整的质量检查
python scripts/quality_check.py

# 自动修复可修复的问题
python scripts/quality_check.py --fix

# 手动格式化代码
black .
flake8 .
```

### 提交规范
```bash
# 提交信息格式
<type>(<scope>): <subject>

# 示例
feat(webui): 添加截图历史功能
fix(api): 修复测试用例删除接口错误
docs(readme): 更新安装说明
style(format): 统一代码格式
refactor(models): 重构数据模型
test(unit): 添加单元测试
chore(deps): 更新依赖包
```

## 📁 项目结构

```
AI-WebUIAuto/
├── web_gui/                   # Web界面核心模块
│   ├── templates/             # HTML模板
│   │   ├── index_enhanced.html
│   │   ├── testcases.html
│   │   ├── execution.html
│   │   └── reports.html
│   ├── static/               # 静态资源
│   │   ├── css/              # 样式文件
│   │   ├── js/               # JavaScript文件
│   │   └── screenshots/      # 截图文件
│   ├── app_enhanced.py       # 主应用
│   ├── api_routes.py         # API路由
│   ├── models.py             # 数据模型
│   └── run_enhanced.py       # 启动脚本
├── scripts/                  # 工具脚本
│   ├── quality_check.py      # 代码质量检查
│   ├── setup_dev_env.py      # 开发环境设置
│   └── setup_git_hooks.sh    # Git钩子设置
├── PRD/                      # 产品需求文档
├── TASK/                     # 任务文档
├── tests/                    # 测试文件
├── logs/                     # 日志文件
├── PROJECT_RULES.md          # 项目规则
├── DEVELOPMENT_GUIDE.md      # 开发指南
├── requirements.txt          # Python依赖
├── package.json              # Node.js依赖
├── .env.example              # 环境变量模板
├── .gitignore               # Git忽略规则
└── README.md                # 项目说明
```

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试文件
python -m pytest tests/test_models.py

# 运行测试并生成覆盖率报告
python -m pytest tests/ --cov=web_gui --cov-report=html
```

### 编写测试
```python
# tests/test_example.py
import unittest
from web_gui.models import TestCase

class TestCaseModelTest(unittest.TestCase):
    def setUp(self):
        """测试前置设置"""
        pass
    
    def test_create_testcase(self):
        """测试创建测试用例"""
        # Given
        data = {"name": "测试用例", "steps": []}
        
        # When
        testcase = TestCase.create(data)
        
        # Then
        self.assertIsNotNone(testcase.id)
        self.assertEqual(testcase.name, "测试用例")
```

## 📝 代码规范

### Python代码
```python
"""
模块文档字符串
描述模块的功能和用途
"""

class ExampleClass:
    """
    类文档字符串
    
    Attributes:
        attr1 (str): 属性描述
        attr2 (int): 属性描述
    """
    
    def __init__(self, param1: str, param2: int = 0):
        """
        初始化方法
        
        Args:
            param1 (str): 参数描述
            param2 (int, optional): 可选参数描述. Defaults to 0.
        """
        self.attr1 = param1
        self.attr2 = param2
    
    def example_method(self, arg1: str) -> bool:
        """
        示例方法
        
        Args:
            arg1 (str): 参数描述
            
        Returns:
            bool: 返回值描述
            
        Raises:
            ValueError: 异常描述
        """
        if not arg1:
            raise ValueError("arg1 不能为空")
        
        # 业务逻辑
        return True
```

### JavaScript代码
```javascript
/**
 * 类文档注释
 * 描述类的功能和用途
 */
class ExampleClass {
    /**
     * 构造函数
     * @param {string} param1 - 参数描述
     * @param {number} param2 - 参数描述
     */
    constructor(param1, param2 = 0) {
        this.attr1 = param1;
        this.attr2 = param2;
    }
    
    /**
     * 示例方法
     * @param {string} arg1 - 参数描述
     * @returns {Promise<boolean>} 返回值描述
     */
    async exampleMethod(arg1) {
        if (!arg1) {
            throw new Error('arg1 不能为空');
        }
        
        // 业务逻辑
        return true;
    }
}
```

## 🔧 工具配置

### VSCode配置
项目已包含`.vscode/settings.json`配置文件，包含：
- Python格式化工具配置
- 代码检查工具配置
- 自动保存格式化
- 统一的编辑器设置

### Git Hooks
运行`./scripts/setup_git_hooks.sh`设置Git钩子：
- **pre-commit**: 提交前代码质量检查
- **commit-msg**: 提交信息格式检查
- **pre-push**: 推送前测试和安全检查

## 🚨 常见问题

### 1. 代码质量检查失败
```bash
# 查看具体问题
python scripts/quality_check.py

# 自动修复格式问题
black .

# 手动修复其他问题
```

### 2. 依赖安装失败
```bash
# 更新pip
python -m pip install --upgrade pip

# 清理缓存重新安装
pip cache purge
pip install -r requirements.txt
```

### 3. Node.js依赖问题
```bash
# 清理node_modules
rm -rf node_modules package-lock.json

# 重新安装
npm install
```

### 4. 环境变量配置
```bash
# 检查.env文件是否存在
ls -la .env

# 检查环境变量是否正确加载
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('OPENAI_API_KEY'))"
```

## 📚 参考资源

- [项目规则文档](PROJECT_RULES.md)
- [Flask官方文档](https://flask.palletsprojects.com/)
- [Socket.IO文档](https://socket.io/docs/)
- [MidScene文档](https://midscenejs.com/)
- [Python代码规范PEP8](https://pep8.org/)
- [JavaScript代码规范](https://standardjs.com/)

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 遵循代码规范
4. 编写测试
5. 提交Pull Request
6. 等待代码审查

## 📞 支持

如有问题，请：
1. 查看本文档和项目规则
2. 运行代码质量检查工具
3. 查看项目Issues
4. 联系项目维护者
