# 测试说明

## 测试结构

```
tests/
├── unit/                    # 单元测试
│   ├── test_testcase_model.py       # TestCase模型测试
│   ├── test_execution_history_model.py  # ExecutionHistory模型测试
│   ├── test_step_execution_model.py    # StepExecution模型测试
│   ├── test_models.py              # 基础模型测试
│   └── factories.py               # 测试数据工厂
├── conftest.py             # pytest配置和fixtures
└── README.md              # 本文件
```

## 本地运行测试

### 1. 安装测试依赖

```bash
pip install -r requirements.txt
pip install pytest pytest-cov pytest-html pytest-mock factory-boy faker
```

### 2. 运行所有测试

```bash
# 运行所有测试
python -m pytest

# 运行单元测试
python -m pytest tests/unit/

# 详细输出
python -m pytest -v

# 指定测试文件
python -m pytest tests/unit/test_testcase_model.py

# 运行特定测试类
python -m pytest tests/unit/test_testcase_model.py::TestTestCaseBasicOperations

# 运行特定测试方法
python -m pytest tests/unit/test_testcase_model.py::TestTestCaseBasicOperations::test_should_create_testcase_with_valid_data
```

### 3. 生成测试覆盖率报告

```bash
# 生成终端报告
python -m pytest --cov=web_gui tests/unit/

# 生成HTML报告
python -m pytest --cov=web_gui --cov-report=html tests/unit/

# 查看HTML报告
open htmlcov/index.html  # macOS
# 或
start htmlcov/index.html  # Windows
```

### 4. 生成测试报告

```bash
# 生成HTML测试报告
python -m pytest --html=report.html --self-contained-html
```

## GitHub Actions 自动化测试

本项目配置了GitHub Actions自动运行测试：

- **触发条件**: 推送到master/main分支或创建Pull Request
- **Python版本**: 3.9, 3.10, 3.11
- **测试报告**: 自动生成并上传测试结果和覆盖率报告
- **查看结果**: 在GitHub仓库的Actions标签页查看测试结果

## 测试最佳实践

1. **测试隔离**: 每个测试使用独立的数据库会话，测试结束后自动回滚
2. **测试数据**: 使用factory_boy生成测试数据，避免硬编码
3. **测试命名**: 使用描述性的测试方法名，如 `test_should_create_testcase_with_valid_data`
4. **测试组织**: 按业务对象组织测试文件，按功能分组测试类
5. **断言清晰**: 使用明确的断言，包含失败时的错误信息

## 测试覆盖范围

### 单元测试覆盖内容

1. **基础操作测试**
   - 创建、读取、更新、删除操作
   - 数据序列化和反序列化

2. **约束测试**
   - 必填字段验证
   - 唯一性约束
   - 外键约束
   - 默认值

3. **边界值测试**
   - 最大/最小值
   - 空值处理
   - 特殊字符
   - Unicode支持

4. **关系测试**
   - 模型间关系
   - 级联操作
   - 关联查询

5. **业务逻辑测试**
   - 状态转换
   - 数据一致性
   - 计算逻辑

## 常见问题

### 1. 测试数据库连接错误

确保在测试环境中使用内存数据库：
```python
SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

### 2. 外键约束错误

SQLite默认关闭外键约束，测试配置已自动启用：
```python
PRAGMA foreign_keys=ON
```

### 3. 导入错误

确保项目根目录在Python路径中：
```python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```